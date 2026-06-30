% dynamo_t3ss_pca.m
% dpkpca classification on T3SS injectisome dataset (415 particles, 48^3).
%
% Data:   dynamo_outputs/t3ss_pca/data/particle_00001..00415.mrc
% Table:  t3ss_pca.tbl (identity poses, tags 1..415)
% Mask:   mask_t3ss.mrc (cylinder R=20, Y=[2,27], ZC=24, XC=24)
% Band:   [0.05, 0.45, 2]  (~29-267 A at 13.33 A/px)

run('/home/jblaser2/Research/dynamo/dynamo_activate.m');

OUTDIR   = '/home/jblaser2/Research/STA/packages/dynamo/dynamo_outputs/t3ss_pca';
DATA_DIR = fullfile(OUTDIR, 'data');
TBL_FILE = fullfile(OUTDIR, 't3ss_pca.tbl');
MASK_MRC = '/home/jblaser2/Research/synthetic_sta/injectisome/maps/mask_t3ss.mrc';
WFNAME   = 't3ss_pca';

cd(OUTDIR);
fprintf('\n=== Dynamo dpkpca — T3SS (%s) ===\n', datestr(now, 'HH:MM:SS'));

mask = dynamo_read(MASK_MRC);
fprintf('Mask: %d active voxels (>0.5)\n', sum(mask(:) > 0.5));

if exist(fullfile(OUTDIR, WFNAME), 'dir')
    fprintf('Reloading existing workflow...\n');
    wb = dpkmath.pca.ProjectWorkflow.read(WFNAME);
else
    fprintf('Creating workflow...\n');
    wb = dpkpca.new(WFNAME, 't', TBL_FILE, 'd', DATA_DIR, 'm', mask);
    wb.setBand([0.05, 0.45, 2]);
    wb.setSym('c1');
    wb.settings.general.bin.value = 0;
    wb.settings.computing.cores.value  = '*';
    wb.settings.computing.useGpus.value = false;
    wb.setBatch(100);
    wb.unfold();
    fprintf('Workflow created.\n');
end

steps = {'prealign', 'ccmatrix', 'eigentable', 'eigenvolumes'};
for k = 1:numel(steps)
    s = steps{k};
    fprintf('\n=== STEP: %s (%s) ===\n', s, datestr(now, 'HH:MM:SS'));
    try
        wb.steps.items.(s).compute();
        fprintf('=== STEP_OK: %s ===\n', s);
    catch ME
        fprintf('=== STEP_FAIL: %s : %s ===\n', s, ME.message);
        if strcmp(s, 'ccmatrix') || strcmp(s, 'prealign')
            fprintf('Critical step failed — aborting.\n');
            exit(1);
        end
    end
end

E = [];
try
    E = wb.getEigencomponents();
    save(fullfile(OUTDIR, 'eigencomponents.mat'), 'E');
    fprintf('\nEigencomponents: %dx%d\n', size(E,1), size(E,2));
catch ME
    fprintf('getEigencomponents failed: %s\n', ME.message);
end

try
    cc = wb.getCCMatrix();
    save(fullfile(OUTDIR, 'ccmatrix_pca.mat'), 'cc');
    fprintf('CC matrix: %dx%d  mean=%.4f\n', size(cc,1), size(cc,2), mean(cc(:)));
catch ME
    fprintf('getCCMatrix failed: %s\n', ME.message);
end

if ~isempty(E)
    N  = size(E, 1);
    nc = min(10, size(E, 2));
    X  = E(:, 1:nc);
    rng(42);
    for k = [2, 3]
        km = kmeans(X, k, 'Replicates', 20, 'MaxIter', 500);
        pred_file = fullfile(OUTDIR, sprintf('predictions_k%d.csv', k));
        fid = fopen(pred_file, 'w');
        fprintf(fid, 'file,pred_label\n');
        for i = 1:N
            fprintf(fid, 'subtomo_%04d.mrc,%d\n', i-1, km(i));
        end
        fclose(fid);
        fprintf('k=%d: ', k);
        for c = 1:k
            fprintf('class%d=%d ', c, sum(km==c));
        end
        fprintf('\n  -> %s\n', pred_file);
    end
else
    fprintf('No eigencomponents — k-means skipped.\n');
end

fprintf('\n=== Done (%s) ===\n', datestr(now, 'HH:MM:SS'));
fprintf('Next: python3 score_dynamo_t3ss.py\n');
