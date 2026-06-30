% dynamo_fm_hard_pca.m
% dpkpca classification on FM_hard (813 particles, 96^3, GT-aligned, 3 classes).
%
% Data:   dynamo_outputs/motor_hard_pca/data/ (symlinks to merged_ABC_full/)
% Table:  motor_hard_pca.tbl (identity poses, tags 1..813)
% Mask:   diff_mask_hard.mrc (3-class diff mask, 5.5% of box)
% Band:   [0.05, 0.45, 2] — same as FM_easy

run('/home/jblaser2/Research/dynamo/dynamo_activate.m');

OUTDIR   = '/home/jblaser2/Research/STA/packages/dynamo/dynamo_outputs/motor_hard_pca';
DATA_DIR = fullfile(OUTDIR, 'data');
TBL_FILE = fullfile(OUTDIR, 'motor_hard_pca.tbl');
MASK_MRC = '/home/jblaser2/Research/synthetic_sta/motor_hard/maps/diff_mask_hard.mrc';
WFNAME   = 'motor_hard_pca';

cd(OUTDIR);

fprintf('\n=== Dynamo dpkpca — FM_hard (%s) ===\n', datestr(now, 'HH:MM:SS'));

mask = dynamo_read(MASK_MRC);
fprintf('Mask loaded: %d active voxels (threshold > 0.5)\n', sum(mask(:) > 0.5));

if exist(fullfile(OUTDIR, WFNAME), 'dir')
    fprintf('Reloading existing workflow %s...\n', WFNAME);
    wb = dpkmath.pca.ProjectWorkflow.read(WFNAME);
else
    fprintf('Creating new workflow %s...\n', WFNAME);
    wb = dpkpca.new(WFNAME, 't', TBL_FILE, 'd', DATA_DIR, 'm', mask);
    wb.setBand([0.05, 0.45, 2]);
    wb.setSym('c1');
    wb.settings.general.bin.value = 0;
    wb.settings.computing.cores.value  = '*';
    wb.settings.computing.useGpus.value = false;
    wb.setBatch(100);
    wb.unfold();
    fprintf('Workflow created and unfolded.\n');
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

fprintf('\n=== K-means k=3 (%s) ===\n', datestr(now, 'HH:MM:SS'));
try
    E = wb.getEigencomponents();
    N = size(E, 1);
    fprintf('Eigencomponents: %dx%d\n', size(E,1), size(E,2));
    save(fullfile(OUTDIR, 'eigencomponents.mat'), 'E');
catch ME
    fprintf('getEigencomponents failed: %s\n', ME.message);
    try
        cc = wb.getCCMatrix();
        save(fullfile(OUTDIR, 'ccmatrix_pca.mat'), 'cc');
        [V, D] = eig(cc);
        [~, idx] = sort(diag(D), 'descend');
        E = V(:, idx)';
        N = size(E, 2);
        fprintf('Built eigenvectors from cc: %dx%d\n', size(E,1), size(E,2));
        save(fullfile(OUTDIR, 'eigencomponents.mat'), 'E');
    catch ME2
        fprintf('Fallback also failed: %s\n', ME2.message);
        exit(1);
    end
end

for k = [3]
    nc = min(17, size(E,2));
    X = E(:, 1:nc);    % N x nc  (E is particles x eigenvectors)
    [km, ~] = kmeans(X, k, 'Replicates', 10, 'MaxIter', 500);
    km = km';

    % Counts
    for c = 1:k
        fprintf('  class %d: %d\n', c, sum(km == c));
    end

    pred_file = fullfile(OUTDIR, sprintf('predictions_k%d.csv', k));
    fid = fopen(pred_file, 'w');
    fprintf(fid, 'file,pred_label\n');
    for i = 1:N
        fprintf(fid, 'subtomo_%04d.mrc,%d\n', i-1, km(i));
    end
    fclose(fid);
    fprintf('Predictions -> %s\n', pred_file);
end

fprintf('\n=== Done (%s) ===\n', datestr(now, 'HH:MM:SS'));
