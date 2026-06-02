% Evaluate the cold-start MRA run (mra_ttest128, 6 rounds / 18 iterations).
% Two questions:
%   (1) ALIGNMENT: how close did cold-start poses (from initial.tbl) get to real.tbl?
%       -> shift error + c8-folded angular error vs initial.tbl baseline (4.93 vox / 118.7 deg).
%   (2) CLASSIFICATION: (a) Dynamo's own embedded-MRA class labels (col 22) vs GT;
%       (b) PCA re-classification on the MRA-aligned table -> ARI vs GT.
%   Spectrum: initial.tbl PCA ARI 0.017  <-- cold-start -->  real.tbl PCA ARI 1.000.
set(0,'DefaultFigureVisible','off');
run('/home/jblaser2/Research/dynamo/dynamo_activate.m');
outdir = '/home/jblaser2/Research/STA/dynamo/dynamo_outputs/ttest128_tutorial';
cd(outdir);

Treal = dread('ttest128/real.tbl');
Tinit = dread('ttest128/initial.tbl');
Tmra  = dread('mra_ttest128/results/ite_0018/averages/refined_table_ref_001_ite_0018.tbl');

% match by tag (col 1)
[~,ir] = ismember(Tmra(:,1), Treal(:,1));
Treal = Treal(ir,:);
gt = Treal(:,22);

% ---- pose error helpers (c8 about z = the symmetry/narot axis) ----
function e = ang_err_c8(angR, angT)
    Rr = dynamo_euler2matrix(angR);
    best = inf;
    for k = 0:7
        Rt = dynamo_euler2matrix([angT(1), angT(2), angT(3)+45*k]);
        Rrel = Rr * Rt';
        c = (trace(Rrel)-1)/2; c = max(min(c,1),-1);
        best = min(best, acosd(c));
    end
    e = best;
end

n = size(Tmra,1);
ang_mra = zeros(n,1); ang_init = zeros(n,1);
for i = 1:n
    ang_mra(i)  = ang_err_c8(Tmra(i,7:9),  Treal(i,7:9));
    ang_init(i) = ang_err_c8(Tinit(i,7:9), Treal(i,7:9));
end
sh_mra  = sqrt(sum((Tmra(:,4:6)  - Treal(:,4:6)).^2, 2));
sh_init = sqrt(sum((Tinit(:,4:6) - Treal(:,4:6)).^2, 2));

fprintf('\n==== ALIGNMENT (vs real.tbl, c8-folded angles) ====\n');
fprintf('ANGLE  initial: mean %.1f  med %.1f deg | MRA cold-start: mean %.1f  med %.1f deg\n', ...
        mean(ang_init), median(ang_init), mean(ang_mra), median(ang_mra));
fprintf('SHIFT  initial: mean %.2f  med %.2f vox | MRA cold-start: mean %.2f  med %.2f vox\n', ...
        mean(sh_init), median(sh_init), mean(sh_mra), median(sh_mra));
fprintf('ANGLE within 20 deg: init %d/%d  MRA %d/%d\n', sum(ang_init<20),n, sum(ang_mra<20),n);

% ---- Dynamo's own embedded-MRA class labels ----
mracls = Tmra(:,22);
fprintf('\n==== MRA OWN CLASSIFICATION (col 22) ====\n');
u = unique(mracls);
fprintf('distinct class labels in final table: %s  (n classes = %d)\n', mat2str(u(:)'), numel(u));
for j=1:numel(u); fprintf('  class %d: %d particles\n', u(j), sum(mracls==u(j))); end

% ---- PCA re-classification on the MRA-aligned table ----
% write the matched MRA table to disk so dpkpca can index data by tag
dwrite(Tmra, fullfile(outdir,'mra_aligned.tbl'));
name = 'classtest128_mra';
if exist(fullfile(outdir,name),'dir'); rmdir(fullfile(outdir,name),'s'); end
if exist(fullfile(outdir,[name '.PCA']),'dir'); rmdir(fullfile(outdir,[name '.PCA']),'s'); end
wb = dpkpca.new(name,'t','mra_aligned.tbl','d','ttest128/data','m',dcylinder([20,20],40));
wb.setBand([0,0.5,2]); wb.setSym('c8');
wb.settings.general.bin.value = 0;
wb.settings.computing.cores.value = '*';
wb.settings.computing.useGpus.value = false;
wb.setBatch(100); wb.unfold();
for s = {'prealign','ccmatrix','eigentable','eigenvolumes','tsne'}
    try; wb.steps.items.(s{1}).compute(); catch ME; fprintf('STEP_FAIL %s: %s\n',s{1},ME.message); end
end
E = wb.getEigencomponents();
nc = min(5,size(E,2)); rng(0);
km = kmeans(E(:,1:nc),2,'Replicates',20);
[acc,ari] = score2(km, gt);
fprintf('\n==== PCA on MRA-aligned table ====\n');
fprintf('PCA(MRA-aligned): kmeans k=2 acc=%.3f ARI=%.3f (%d comps)\n', acc, ari, nc);
figure; gscatter(E(:,1),E(:,2),gt); xlabel('PC1'); ylabel('PC2');
title(sprintf('MRA-aligned PCA: acc=%.2f ARI=%.2f',acc,ari));
print(gcf, fullfile(outdir,'pca_scatter_mra.png'),'-dpng','-r150');

fprintf('\n==== SPECTRUM (PCA k=2 ARI vs GT) ====\n');
fprintf('initial.tbl 0.017  |  MRA cold-start %.3f  |  real.tbl 1.000\n', ari);
disp('EVAL_MRA_DONE');

% ---- scoring helpers ----
function [acc,ari] = score2(lab, gt)
    acc = max(mean(lab==gt), mean((3-lab)==gt));
    a=lab(:); b=gt(:); ua=unique(a); ub=unique(b);
    C=zeros(numel(ua),numel(ub));
    for i=1:numel(ua); for j=1:numel(ub); C(i,j)=sum(a==ua(i)&b==ub(j)); end; end
    sumi=sum(C,2); sumj=sum(C,1);
    nij=sum(arrayfun(@nchoosek2,C(:))); ai=sum(arrayfun(@nchoosek2,sumi)); bj=sum(arrayfun(@nchoosek2,sumj));
    expc=ai*bj/nchoosek2(numel(gt)); mx=0.5*(ai+bj);
    ari=(nij-expc)/(mx-expc);
end
function v=nchoosek2(x); v=x*(x-1)/2; end
