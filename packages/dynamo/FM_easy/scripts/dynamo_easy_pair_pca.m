% dynamo_easy_pair_pca.m
% 2-class dpkpca on a PAIR of motor_easy GT classes. Raw GT-aligned subtomos only.
% Reads from environment: PAIR_OUTDIR, PAIR_MASK  (set by the launching shell).
%   PAIR_OUTDIR/data/        symlinked raw aligned subtomos (the 2 classes)
%   PAIR_OUTDIR/pair.tbl     identity poses
%   PAIR_MASK                generic soft spherical mask
% Writes PAIR_OUTDIR/predictions_k2.csv  (tag,pred_label)

run('/home/jblaser2/Research/dynamo/dynamo_activate.m');

% --- parpool hardening (avoids the ServiceHost/parfor teardown crash) ---
setenv('MW_SERVICE_HOST_DISABLE', '1');
NWORKERS = 16;
if isempty(gcp('nocreate')); pool = parpool('Processes', NWORKERS); else; pool = gcp; end
pool.IdleTimeout = Inf;

OUTDIR = getenv('PAIR_OUTDIR');
MASK   = getenv('PAIR_MASK');
TBL    = fullfile(OUTDIR, 'pair.tbl');
DATA   = fullfile(OUTDIR, 'data');
WF     = 'pair_pca';
cd(OUTDIR);
fprintf('\n=== dpkpca pair run: %s (%s) ===\n', OUTDIR, datestr(now,'HH:MM:SS'));

mask = dynamo_read(MASK);
fprintf('Mask: %d active voxels\n', sum(mask(:) > 0.05));

if exist(fullfile(OUTDIR, WF), 'dir')
    wb = dpkmath.pca.ProjectWorkflow.read(WF);
else
    wb = dpkpca.new(WF, 't', TBL, 'd', DATA, 'm', mask);
    wb.setBand([0.05, 0.45, 2]);          % same band as the canonical FM_easy run
    wb.setSym('c1');
    wb.settings.general.bin.value = 0;
    wb.settings.computing.cores.value = NWORKERS;
    wb.settings.computing.useGpus.value = false;
    wb.setBatch(100);
    wb.unfold();
end

steps = {'prealign','ccmatrix','eigentable','eigenvolumes'};
for k = 1:numel(steps)
    s = steps{k};
    fprintf('\n=== STEP: %s (%s) ===\n', s, datestr(now,'HH:MM:SS'));
    try
        wb.steps.items.(s).compute();
        fprintf('=== STEP_OK: %s ===\n', s);
    catch ME
        fprintf('=== STEP_FAIL: %s : %s ===\n', s, ME.message);
        if strcmp(s,'ccmatrix') || strcmp(s,'prealign'); exit(1); end
    end
end

E = wb.getEigencomponents();
save(fullfile(OUTDIR,'eigencomponents.mat'),'E');
fprintf('\nEigencomponents: %dx%d\n', size(E,1), size(E,2));

N = size(E,1); nc = min(10, size(E,2)); X = E(:,1:nc); rng(42);
km = kmeans(X, 2, 'Replicates', 20, 'MaxIter', 500);
fid = fopen(fullfile(OUTDIR,'predictions_k2.csv'),'w');
fprintf(fid,'tag,pred_label\n');
for i = 1:N; fprintf(fid,'%d,%d\n', i, km(i)); end
fclose(fid);
fprintf('k=2: class1=%d class2=%d\n', sum(km==1), sum(km==2));
fprintf('=== Done (%s) ===\n', datestr(now,'HH:MM:SS'));
