% PCA classification walkthrough (headless adaptation)
% https://www.dynamo-em.org/w/index.php?title=Walkthrough_on_PCA_through_the_command_line
set(0,'DefaultFigureVisible','off');
run('/home/jblaser2/Research/dynamo/dynamo_activate.m');

outdir = '/home/jblaser2/Research/STA/dynamo/dynamo_outputs/ttest128_tutorial';
cd(outdir);

% --- Define input elements (walkthrough) ---
dataFolder = 'ttest128/data';
tableFile  = 'ttest128/real.tbl';     % ground-truth alignment, per walkthrough
mask = dcylinder([20,20],40);
name = 'classtest128';

% remove any prior workflow folder so .new() does not clash
if exist(fullfile(outdir,name),'dir'); rmdir(fullfile(outdir,name),'s'); end

% --- Initialize PCA workflow ---
wb = dpkpca.new(name,'t',tableFile,'d',dataFolder,'m',mask);

% --- Mathematical configuration (walkthrough) ---
wb.setBand([0,0.5,2]);
wb.setSym('c8');
wb.settings.general.bin.value = 0;

% --- Computational params (adapted: CPU, no compiled GPU exe on this node) ---
wb.settings.computing.cores.value  = '*';
wb.settings.computing.useGpus.value = false;
wb.setBatch(100);
disp('--- getBlockSize ---'); wb.getBlockSize();

% --- Prepare ---
wb.unfold();

% --- Sequential computation ---
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

% --- Extract numerical results to disk ---
try
    m = wb.getCCMatrix();
    save(fullfile(outdir,'ccmatrix.mat'),'m');
    writematrix(m, fullfile(outdir,'ccmatrix.txt'));
    figure; dshow(m); h=gca(); h.YDir='reverse'; title('CC matrix');
    print(gcf, fullfile(outdir,'ccmatrix.png'),'-dpng','-r150');
    fprintf('CCMATRIX_OK size %dx%d\n', size(m,1), size(m,2));
catch ME
    fprintf('CCMATRIX_FAIL: %s\n', ME.message);
end

E = [];
try
    E = wb.getEigencomponents();
    save(fullfile(outdir,'eigencomponents.mat'),'E');
    writematrix(E, fullfile(outdir,'eigencomponents.txt'));
    fprintf('EIGEN_OK size %dx%d\n', size(E,1), size(E,2));
catch ME
    fprintf('EIGEN_FAIL: %s\n', ME.message);
end

% --- Ground truth from real.tbl column 22 ---
T = dread(tableFile);
gt = T(:,22);
writematrix(gt, fullfile(outdir,'ground_truth_labels.txt'));
fprintf('GT class counts: c1=%d c2=%d\n', sum(gt==1), sum(gt==2));

% --- k-means k=2 on leading eigencomponents, compare to GT ---
if ~isempty(E)
    nc = min(5, size(E,2));
    X = E(:,1:nc);
    rng(0);
    km = kmeans(X, 2, 'Replicates', 20);
    writematrix(km, fullfile(outdir,'kmeans_labels.txt'));
    % accuracy under best label permutation
    acc1 = mean(km==gt);
    acc2 = mean((3-km)==gt);
    acc = max(acc1,acc2);
    fprintf('KMEANS k=2 accuracy vs GT = %.3f (using %d comps)\n', acc, nc);
    % scatter of first two comps colored by GT
    figure; gscatter(E(:,1),E(:,2),gt); xlabel('PC1'); ylabel('PC2');
    title(sprintf('Eigencomponents colored by GT (kmeans acc=%.2f)',acc));
    print(gcf, fullfile(outdir,'pca_scatter_gt.png'),'-dpng','-r150');
end

% --- Eigenvolume montage ---
try
    eigSet = wb.getEigenvolume(1:min(30, 64));
    figure; mbvol.groups.montage(dynamo_normalize_roi(eigSet));
    print(gcf, fullfile(outdir,'eigenvolumes_montage.png'),'-dpng','-r150');
    fprintf('EIGENVOL_OK\n');
catch ME
    fprintf('EIGENVOL_FAIL: %s\n', ME.message);
end

% --- save workflow handle name for later interactive reload ---
fprintf('WORKFLOW_FOLDER: %s\n', fullfile(outdir,name));
disp('RUN_PCA_DONE');
