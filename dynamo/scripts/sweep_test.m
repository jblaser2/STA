% Quick smoke test: run HAC at r=10 and r=20 to verify hac_run_single works
DATA_DIR  = '/home/jblaser2/Research/STA/subtomos_mrc';
SWEEP_DIR = '/home/jblaser2/Research/STA/dynamo/outputs/hac_sweep';
N_CLASSES = 3;

if ~exist(SWEEP_DIR, 'dir'), mkdir(SWEEP_DIR); end

files = dir(fullfile(DATA_DIR, '*.mrc'));
N = length(files);
data = cell(N, 1);
for i = 1:N
    data{i} = dynamo_read(fullfile(DATA_DIR, files(i).name));
end
fprintf('Loaded %d particles\n', N);

c10 = hac_run_single(DATA_DIR, fullfile(SWEEP_DIR, 'radius_10'), 10, N_CLASSES, data, files);
fprintf('r=10  coph=%.4f\n', c10);

c20 = hac_run_single(DATA_DIR, fullfile(SWEEP_DIR, 'radius_20'), 20, N_CLASSES, data, files);
fprintf('r=20  coph=%.4f\n', c20);
