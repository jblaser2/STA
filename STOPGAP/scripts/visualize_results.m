function visualize_results(rootdir, eigenval_csv, motl_pat, refroot, klist, px)
%% visualize_results
% Generate headless PNGs (saved to rootdir/meta/):
%   (a) PCA scatter: PC1-2 and PC1-3 colored by k-means class, per k
%   (b) Central-slice montage (XY/XZ/YZ) of class averages per k
%
% rootdir      : STOPGAP project root
% eigenval_csv : full path to eigenval CSV (n_particles x n_eigs)
% motl_pat     : pattern with two %d placeholders (k, then iteration),
%                e.g. 'lists/allmotl_pca_k%d_%d.star'
% refroot      : class-average ref name root, e.g. 'class_pca'
% klist        : e.g. [2 3 4]
% px           : pixel size in Å/vox; <=0 -> read from subtomo header

meta = fullfile(rootdir, 'meta');
if ~exist(meta,'dir'), mkdir(meta); end

if px <= 0
    h  = sg_read_mrc_header(fullfile(rootdir,'subtomograms','subtomo_1.mrc'));
    px = double(h.xlen) / double(h.mx);
end
fprintf('[viz] pixel size = %.4f Å/vox\n', px);

% Load eigenvalue matrix (n_sub x n_eigs)
ev = readmatrix(eigenval_csv);
fprintf('[viz] eigenvalue matrix: %dx%d\n', size(ev,1), size(ev,2));

%%  (a) PCA scatter per k
n_k = numel(klist);
f1 = figure('Visible','off','Position',[0 0 700 350*n_k]);
for ki = 1:n_k
    k = klist(ki);
    % Newest motl for this k (wildcard on iteration number)
    pat1 = strrep(motl_pat, '%d_%d', sprintf('%d_*', k));
    ml   = dir(fullfile(rootdir, pat1));
    if isempty(ml)
        warning('[viz] no motl found: %s', fullfile(rootdir,pat1));
        continue;
    end
    [~,o] = sort([ml.datenum]);
    motl   = sg_motl_read2(fullfile(ml(o(end)).folder, ml(o(end)).name));
    c      = double(motl.class);

    subplot(n_k, 2, 2*ki-1);
    gscatter(ev(:,1), ev(:,2), c); xlabel('PC1'); ylabel('PC2');
    title(sprintf('k=%d', k)); axis tight; legend off;

    subplot(n_k, 2, 2*ki);
    if size(ev,2) >= 3
        gscatter(ev(:,1), ev(:,3), c); xlabel('PC1'); ylabel('PC3');
    else
        gscatter(ev(:,1), ev(:,2), c); xlabel('PC1'); ylabel('PC2');
    end
    axis tight; legend off;
end
out1 = fullfile(meta, [refroot,'_pca_scatter.png']);
exportgraphics(f1, out1, 'Resolution', 200);
close(f1);
fprintf('[viz] wrote %s\n', out1);

%% (b) Central-slice montage per k
for k = klist
    vols = cell(1, k);
    for cl = 1:k
        % Search for class average; exclude halfset (A_/B_) and wfilt maps
        d = dir(fullfile(rootdir,'ref', sprintf('%s_k%d_*_%d.mrc',refroot,k,cl)));
        if ~isempty(d)
            keep = ~cellfun(@(nm) contains(nm,'A_') || contains(nm,'B_') || ...
                                  contains(nm,'wfilt'), {d.name});
            d = d(keep);
        end
        if isempty(d)
            warning('[viz] class average not found: k=%d class=%d', k, cl);
            continue;
        end
        [~,o]    = sort([d.datenum]);
        vols{cl} = single(sg_mrcread(fullfile(d(o(end)).folder, d(o(end)).name)));
    end

    fk = figure('Visible','off','Position',[0 0 220*k 660]);
    tl = tiledlayout(3, k, 'TileSpacing','compact','Padding','compact');
    for cl = 1:k
        if numel(vols) < cl || isempty(vols{cl}), continue; end
        v  = vols{cl};
        cz = round(size(v,3)/2);
        cy = round(size(v,2)/2);
        cx = round(size(v,1)/2);

        nexttile(cl);
        imagesc(v(:,:,cz)); axis image off; colormap(gca,'gray');
        title(sprintf('c%d XY',cl));

        nexttile(k+cl);
        imagesc(squeeze(v(:,cy,:))); axis image off; colormap(gca,'gray');
        title('XZ');

        nexttile(2*k+cl);
        imagesc(squeeze(v(cx,:,:))); axis image off; colormap(gca,'gray');
        title('YZ');
    end
    title(tl, sprintf('%s class avgs k=%d (%.2f Å/px)', refroot, k, px));
    outk = fullfile(meta, sprintf('%s_class_avg_k%d.png', refroot, k));
    exportgraphics(fk, outk, 'Resolution', 200);
    close(fk);
    fprintf('[viz] wrote %s\n', outk);
end
fprintf('[viz] done. PNGs in %s\n', meta);
end
