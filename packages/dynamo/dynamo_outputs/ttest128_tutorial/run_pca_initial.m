% PCA classification with coarse initial.tbl (imperfect prealignment)
% Stress-test variant of the dynamo-em PCA walkthrough.
set(0,'DefaultFigureVisible','off');
run('/home/jblaser2/Research/dynamo/dynamo_activate.m');

outdir = '/home/jblaser2/Research/STA/dynamo/dynamo_outputs/ttest128_tutorial';
cd(outdir);

fprintf('IPT check: imgaussfilt3 -> %s\n', which('imgaussfilt3'));

dataFolder = 'ttest128/data';
tableFile  = 'ttest128/initial.tbl';   % coarse starting alignment
mask = dcylinder([20,20],40);
name = 'classtest128_initial';

if exist(fullfile(outdir,name),'dir'); rmdir(fullfile(outdir,name),'s'); end
if exist(fullfile(outdir,[name '.PCA']),'dir'); rmdir(fullfile(outdir,[name '.PCA']),'s'); end

wb = dpkpca.new(name,'t',tableFile,'d',dataFolder,'m',mask);
wb.setBand([0,0.5,2]);
wb.setSym('c8');
wb.settings.general.bin.value = 0;
wb.settings.computing.cores.value  = '*';
wb.settings.computing.useGpus.value = false;
wb.setBatch(100);
wb.unfold();

steps = {'prealign','ccmatrix','eigentable','eigenvolumes','tsne'};
for k = 1:numel(steps)
    s = steps{k};
    fprintf('=== STEP: %s ===\n', s);
    try
        wb.steps.items.(s).compute();
        fprintf('=== STEP_OK: %s ===\n', s);
    catch ME
        fprintf('=== STEP_FAIL: %s : %s ===\n', s, ME.message);
    end
end

% --- ground truth (always from real.tbl col 22) ---
Treal = dread('ttest128/real.tbl');
gt = Treal(:,22);

% --- results ---
m = wb.getCCMatrix();
save(fullfile(outdir,'ccmatrix_initial.mat'),'m');
figure; dshow(m); h=gca(); h.YDir='reverse'; title('CC matrix (initial.tbl)');
print(gcf, fullfile(outdir,'ccmatrix_initial.png'),'-dpng','-r150');

E = wb.getEigencomponents();
save(fullfile(outdir,'eigencomponents_initial.mat'),'E');
fprintf('EIGEN_INITIAL size %dx%d\n', size(E,1), size(E,2));

% --- helper: best-permutation accuracy + adjusted Rand index (k=2) ---
function [acc,ari] = score2(lab, gt)
    acc = max(mean(lab==gt), mean((3-lab)==gt));
    n = numel(gt);
    % contingency table
    a = lab(:); b = gt(:);
    ua = unique(a); ub = unique(b);
    C = zeros(numel(ua), numel(ub));
    for i=1:numel(ua); for j=1:numel(ub); C(i,j)=sum(a==ua(i) & b==ub(j)); end; end
    sumi = sum(C,2); sumj = sum(C,1);
    nij = sum(arrayfun(@(x) nchoosek2(x), C(:)));
    ai  = sum(arrayfun(@(x) nchoosek2(x), sumi));
    bj  = sum(arrayfun(@(x) nchoosek2(x), sumj));
    expected = ai*bj / nchoosek2(n);
    maxIdx   = 0.5*(ai+bj);
    ari = (nij - expected) / (maxIdx - expected);
end
function v = nchoosek2(x); v = x*(x-1)/2; end

% --- score initial.tbl run ---
nc = min(5, size(E,2)); rng(0);
km = kmeans(E(:,1:nc),2,'Replicates',20);
[acc_i, ari_i] = score2(km, gt);
fprintf('INITIAL: kmeans k=2 acc=%.3f ARI=%.3f (%d comps)\n', acc_i, ari_i, nc);
figure; gscatter(E(:,1),E(:,2),gt); xlabel('PC1'); ylabel('PC2');
title(sprintf('initial.tbl: acc=%.2f ARI=%.2f',acc_i,ari_i));
print(gcf, fullfile(outdir,'pca_scatter_initial.png'),'-dpng','-r150');

% --- re-score real.tbl baseline from saved eigencomponents ---
S = load(fullfile(outdir,'eigencomponents.mat'));  % var E
Er = S.E; rng(0);
kmr = kmeans(Er(:,1:nc),2,'Replicates',20);
[acc_r, ari_r] = score2(kmr, gt);
fprintf('REAL   : kmeans k=2 acc=%.3f ARI=%.3f (%d comps)\n', acc_r, ari_r, nc);

fprintf('COMPARE  real.tbl  acc=%.3f ARI=%.3f  |  initial.tbl acc=%.3f ARI=%.3f\n', ...
        acc_r, ari_r, acc_i, ari_i);
disp('RUN_PCA_INITIAL_DONE');
