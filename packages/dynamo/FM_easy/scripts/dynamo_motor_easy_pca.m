% dynamo_motor_easy_pca.m
% dpkpca classification on motor_easy synthetic data (694 particles, 96^3, GT-aligned).
%
% Data:   packages/dynamo/dynamo_outputs/motor_easy_pca/data/particle_00001.mrc..00694.mrc
%         (symlinks to merged_all_aln/ — pre-aligned GT particles)
% Table:  motor_easy_pca.tbl (identity poses, tags 1..694)
% Mask:   RELION solvent mask (r=32 px, center Y-10, binarized at 0.5)
% Band:   [0.05, 0.45, 2] (Nyquist fraction; keeps ~30-267 A signal range)
%
% Run from: ~/Research/STA/packages/dynamo/dynamo_scripts/
% Full run (~15-30 min): prealign → ccmatrix → eigentable → eigenvolumes → kmeans

run('/home/jblaser2/Research/dynamo/dynamo_activate.m');

OUTDIR    = '/home/jblaser2/Research/STA/packages/dynamo/dynamo_outputs/motor_easy_pca';
DATA_DIR  = fullfile(OUTDIR, 'data');
TBL_FILE  = fullfile(OUTDIR, 'motor_easy_pca.tbl');
MASK_MRC  = '/home/jblaser2/Research/STA/outputs/relion_motor_easy/solvent_mask.mrc';
WFNAME    = 'motor_easy_pca';

cd(OUTDIR);

fprintf('\n=== Dynamo dpkpca — motor_easy (%s) ===\n', datestr(now, 'HH:MM:SS'));

%% Load mask
mask = dynamo_read(MASK_MRC);
fprintf('Mask loaded: %d active voxels (threshold > 0.5)\n', sum(mask(:) > 0.5));

%% Init workflow (or reload if already exists)
if exist(fullfile(OUTDIR, WFNAME), 'dir')
    fprintf('Reloading existing workflow %s...\n', WFNAME);
    wb = dpkmath.pca.ProjectWorkflow.read(WFNAME);
else
    fprintf('Creating new workflow %s...\n', WFNAME);
    wb = dpkpca.new(WFNAME, 't', TBL_FILE, 'd', DATA_DIR, 'm', mask);
    % Band: [low, high, smoothing] in Nyquist fractions
    % 0.05-0.45 keeps 29-267 A signal at 13.33 A/px; excludes DC and near-Nyquist noise
    wb.setBand([0.05, 0.45, 2]);
    wb.setSym('c1');
    wb.settings.general.bin.value = 0;
    wb.settings.computing.cores.value  = '*';
    wb.settings.computing.useGpus.value = false;
    wb.setBatch(100);
    wb.unfold();
    fprintf('Workflow created and unfolded.\n');
end

%% Run steps sequentially
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

%% Extract eigencomponents
E = [];
try
    E = wb.getEigencomponents();
    save(fullfile(OUTDIR, 'eigencomponents.mat'), 'E');
    fprintf('\nEigencomponents: %dx%d\n', size(E,1), size(E,2));
catch ME
    fprintf('getEigencomponents failed: %s\n', ME.message);
end

%% Save CC matrix
try
    cc = wb.getCCMatrix();
    save(fullfile(OUTDIR, 'ccmatrix_pca.mat'), 'cc');
    fprintf('CC matrix: %dx%d  mean=%.4f\n', size(cc,1), size(cc,2), mean(cc(:)));
catch ME
    fprintf('getCCMatrix failed: %s\n', ME.message);
end

%% k-means at k=2 and k=3, write predictions CSVs
if ~isempty(E)
    % Load particle filenames in tag order (1..N)
    N  = size(E, 1);
    nc = min(10, size(E, 2));
    X  = E(:, 1:nc);
    rng(42);

    for k = [2, 3]
        km = kmeans(X, k, 'Replicates', 20, 'MaxIter', 500);
        % Write predictions CSV (file,pred_label) matching subtomo_XXXX.mrc naming
        pred_file = fullfile(OUTDIR, sprintf('predictions_k%d.csv', k));
        fid = fopen(pred_file, 'w');
        fprintf(fid, 'file,pred_label\n');
        for i = 1:N
            % tag i = subtomo_{i-1:04d}.mrc
            fprintf(fid, 'subtomo_%04d.mrc,%d\n', i-1, km(i));
        end
        fclose(fid);
        % Print class sizes
        fprintf('k=%d: ', k);
        for c = 1:k
            fprintf('class%d=%d ', c, sum(km==c));
        end
        fprintf('\n  -> %s\n', pred_file);
    end
else
    fprintf('No eigencomponents available — k-means skipped.\n');
end

fprintf('\n=== Done (%s) ===\n', datestr(now, 'HH:MM:SS'));
fprintf('Next: python3 score_dynamo_motor_easy.py\n');
