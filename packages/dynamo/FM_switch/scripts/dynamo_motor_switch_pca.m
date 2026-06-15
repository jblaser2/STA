% dynamo_motor_switch_pca.m
% dpkpca classification on motor_switch synthetic data (451 particles, 160^3, GT-aligned).
%
% Data:   packages/dynamo/dynamo_outputs/motor_switch_pca/data/particle_00001..00451.mrc
%         (symlinks to all_particles_aligned/ — pre-aligned GT particles at 5 A/px)
% Table:  motor_switch_pca.tbl (identity poses, tags 1..451)
% Mask:   RELION ellipsoidal solvent mask (r_xz=38, r_y=65 + soft edge; 160^3)
% Band:   [0.05, 0.45, 2] (Nyquist fraction; at 5 A/px: ~22-200 A signal range)
%
% Run from: ~/Research/STA
% ~/matlab/bin/matlab -batch "run('packages/dynamo/FM_switch/scripts/dynamo_motor_switch_pca.m')"

run('/home/jblaser2/Research/dynamo/dynamo_activate.m');

% --- Parallel-pool hardening (160^3 boxes; 2026-06-15) ---
% The 2026-06-11 run died at ccmatrix when the implicit 24-worker pool tore
% down mid-parfor (libgtk-x11-2.0 ServiceHost crash-loop noise + contention at
% 160^3). Quiet the non-essential MathWorks ServiceHost helper, then start one
% explicit, fixed pool that survives across prealign -> ccmatrix.
setenv('MW_SERVICE_HOST_DISABLE', '1');
NWORKERS = 16;                       % was '*' (24); fewer workers = less 160^3 pressure
if isempty(gcp('nocreate'))
    pool = parpool('Processes', NWORKERS);
else
    pool = gcp;
end
pool.IdleTimeout = Inf;              % do not reclaim the pool between steps
fprintf('Parpool ready: %d workers, IdleTimeout=Inf\n', pool.NumWorkers);

OUTDIR    = '/home/jblaser2/Research/STA/packages/dynamo/dynamo_outputs/motor_switch_pca';
DATA_DIR  = fullfile(OUTDIR, 'data');
TBL_FILE  = fullfile(OUTDIR, 'motor_switch_pca.tbl');
MASK_MRC  = '/home/jblaser2/Research/STA/outputs/FM_switch/relion/run_r02/solvent_mask.mrc';
WFNAME    = 'motor_switch_pca';

cd(OUTDIR);

fprintf('\n=== Dynamo dpkpca — motor_switch (%s) ===\n', datestr(now, 'HH:MM:SS'));

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
    wb.setBand([0.05, 0.45, 2]);
    wb.setSym('c1');
    wb.settings.general.bin.value = 0;
    wb.settings.computing.cores.value  = NWORKERS;
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

%% k-means at k=2, write predictions CSV
if ~isempty(E)
    N  = size(E, 1);
    nc = min(10, size(E, 2));
    X  = E(:, 1:nc);
    rng(42);

    for k = [2]
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
    fprintf('No eigencomponents available — k-means skipped.\n');
end

fprintf('\n=== Done (%s) ===\n', datestr(now, 'HH:MM:SS'));
fprintf('Next: python3 packages/dynamo/FM_switch/scripts/score_dynamo_motor_switch.py\n');
