function sg_pca_kmeans_cluster_fn(rootdir, paramfile, vectors, klist)
%% sg_pca_kmeans_cluster_fn
% Parameterized k-means clustering on STOPGAP PCA eigenvalues.
% Reads eigenvalue CSVs from the calc_pca_ccmat step, clusters into k
% classes for each k in klist, and writes labeled motls.
%
% rootdir   : project root (trailing slash optional)
% paramfile : relative path to PCA param file, e.g. 'params/pca_param.star'
% vectors   : Nx2 array [filter_idx, eigenvec_idx] per row
%             e.g. [1 1; 1 2; 1 3] -> PCs 1-3 from filter 1
% klist     : vector of k values, e.g. [2 3 4]
%
% Requires: Statistics & Machine Learning Toolbox (kmeans).

rootdir = sg_check_dir_slash(rootdir);
p = sg_read_pca_param(rootdir, paramfile);

% Find the calc_pca_ccmat row (the one that wrote eigenvalues)
param_idx = find(strcmp({p.pca_task}, 'calc_pca_ccmat'), 1, 'last');
if isempty(param_idx)
    error('ACHTUNG!!! No calc_pca_ccmat row found in %s', paramfile);
end

iter    = p(param_idx).iteration;
n_eigs  = p(param_idx).n_eigs;

% List and pca directories are STOPGAP *settings* (sg_get_pca_settings),
% not param-file columns, so they are not present on the param struct p.
% pca_settings.txt does not override them, so use the standard defaults.
listdir = 'lists/';
pcadir  = 'pca/';

% Read filter list directly (avoids load_filter_list which needs s.cn)
filtlist_path = [rootdir, listdir, p(param_idx).filtlist_name];
if ~exist(filtlist_path, 'file')
    error('ACHTUNG!!! Filter list not found: %s', filtlist_path);
end
filtlist = stopgap_star_read(filtlist_path, true, [], 'stopgap_pca_filt_list');
n_filt   = numel(filtlist);

% Read motl for the iteration that was classified
motl_path = [rootdir, listdir, p(param_idx).motl_name, '_', num2str(iter), '.star'];
if ~exist(motl_path, 'file')
    error('ACHTUNG!!! Motl not found: %s', motl_path);
end
motl  = sg_motl_read2(motl_path);
n_sub = numel(unique(motl.subtomo_num));
fprintf('[kmeans] %d subtomograms, %d filter(s), iteration %d\n', n_sub, n_filt, iter);

% Load eigenvalues: n_sub x n_eigs x n_filt
ev = zeros(n_sub, n_eigs, n_filt, 'single');
for i = 1:n_filt
    ev_path = [rootdir, pcadir, p(param_idx).eigenval_name, '_', ...
               num2str(filtlist(i).filt_idx), '.csv'];
    if ~exist(ev_path, 'file')
        error('ACHTUNG!!! Eigenvalue CSV not found: %s', ev_path);
    end
    ev(:,:,i) = single(readmatrix(ev_path));
end

% Build feature matrix X: n_sub x n_vec (each column = one PC axis)
n_vec = size(vectors, 1);
X = zeros(n_sub, n_vec, 'single');
for i = 1:n_vec
    fi = vectors(i,1);
    ei = vectors(i,2);
    if fi > n_filt
        error('ACHTUNG!!! Filter index %d > n_filt=%d', fi, n_filt);
    end
    if ei > n_eigs
        error('ACHTUNG!!! Eigenvec index %d > n_eigs=%d', ei, n_eigs);
    end
    X(:,i) = ev(:,ei,fi);
end

% k-means for each k
for k = klist
    rng(0);   % reproducible
    idx = kmeans(X, k, 'Replicates', 20, 'MaxIter', 500);
    motl.class = int32(idx);
    out = [rootdir, listdir, sprintf('allmotl_pca_k%d_%d.star', k, iter)];
    sg_motl_write2(out, motl);
    occ = accumarray(idx, 1)';
    fprintf('[kmeans] k=%d occupancies: %s\n         -> %s\n', k, mat2str(occ), out);
end
end
