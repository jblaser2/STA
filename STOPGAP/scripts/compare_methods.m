function compare_methods(rootdir, pca_pat, mra_pat, klist)
%% compare_methods
% Compute ARI and NMI between PCA-k-means and MRA class labels for each k.
% Outputs: rootdir/meta/pca_vs_mra_agreement.csv and cooccur_k<k>.png.
%
% rootdir : STOPGAP project root
% pca_pat : glob pattern with one %d (k), e.g. 'lists/allmotl_pca_k%d_*.star'
% mra_pat : glob pattern with one %d (k), e.g. 'lists/allmotl_mra_k%d_*.star'
% klist   : e.g. [2 3 4]

meta = fullfile(rootdir, 'meta');
if ~exist(meta,'dir'), mkdir(meta); end

rows = {};
for k = klist
    a = newest(rootdir, sprintf(pca_pat, k));
    b = newest(rootdir, sprintf(mra_pat, k));
    if isempty(a) || isempty(b)
        warning('[compare] motl missing for k=%d', k);
        continue;
    end
    ma = sg_motl_read2(a);
    mb = sg_motl_read2(b);

    % Align particle lists by subtomo_num
    [~,ia,ib] = intersect(ma.subtomo_num, mb.subtomo_num);
    la = double(ma.class(ia));
    lb = double(mb.class(ib));

    ar = ari(la,lb);
    nm = nmi(la,lb);

    % Co-occurrence matrix
    C = accumarray([la lb], 1);
    f = figure('Visible','off');
    imagesc(C); axis image; colorbar;
    xlabel('MRA class'); ylabel('PCA class');
    title(sprintf('Co-occurrence k=%d  (ARI=%.3f, NMI=%.3f)', k, ar, nm));
    exportgraphics(f, fullfile(meta,sprintf('cooccur_k%d.png',k)),'Resolution',200);
    close(f);

    rows(end+1,:) = {k, ar, nm}; %#ok<AGROW>
    fprintf('[compare] k=%d  ARI=%.4f  NMI=%.4f\n', k, ar, nm);
end

T = cell2table(rows, 'VariableNames', {'k','ARI','NMI'});
writetable(T, fullfile(meta,'pca_vs_mra_agreement.csv'));
disp(T);
fprintf('[compare] wrote pca_vs_mra_agreement.csv\n');
end

function p = newest(rootdir, pat)
d = dir(fullfile(rootdir, pat));
if isempty(d)
    p = '';
else
    [~,o] = sort([d.datenum]);
    p = fullfile(d(o(end)).folder, d(o(end)).name);
end
end

function r = ari(a, b)
%% Adjusted Rand Index
n   = numel(a);
C   = accumarray([a(:) b(:)], 1);
ai  = sum(C,2);
bi  = sum(C,1);
nc2 = @(x) sum(x .* (x-1) / 2);
sij = nc2(C(:));
sa  = nc2(ai);
sb  = nc2(bi);
t   = n*(n-1)/2;
expected = sa*sb/t;
denom    = (sa+sb)/2 - expected;
if abs(denom) < 1e-12
    r = 1;
else
    r = (sij - expected) / denom;
end
end

function v = nmi(a, b)
%% Normalized Mutual Information
n   = numel(a);
C   = accumarray([a(:) b(:)], 1);
Pij = C / n;
Pi  = sum(Pij, 2);         % column vector
Pj  = sum(Pij, 1);         % row vector
PP  = Pi * Pj;             % outer product (same shape as Pij)
nz  = Pij > 0;
MI  = sum(Pij(nz) .* log(Pij(nz) ./ PP(nz)));
Hi  = -sum(Pi(Pi>0) .* log(Pi(Pi>0)));
Hj  = -sum(Pj(Pj>0) .* log(Pj(Pj>0)));
denom = sqrt(Hi * Hj);
if abs(denom) < 1e-12
    v = 1;
else
    v = MI / denom;
end
end
