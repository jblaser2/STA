% hac_run_sweep.m — sweep over mask radii, run HAC at each, generate summary
%
% Run after activating Dynamo:
%   run /home/jblaser2/Research/dynamo/dynamo_activate.m
%   run /home/jblaser2/Research/STA/dynamo/dynamo_scripts/hac_run_sweep.m

% -------------------------------------------------------------------------
% SETTINGS
% -------------------------------------------------------------------------
DATA_DIR  = '/home/jblaser2/Research/STA/subtomos_mrc';
SWEEP_DIR = '/home/jblaser2/Research/STA/dynamo/dynamo_outputs/hac_sweep_final_pick';
N_CLASSES = 2;
RADII     = [8.7, 8.8, 8.9];
% -------------------------------------------------------------------------

if ~exist(SWEEP_DIR, 'dir'), mkdir(SWEEP_DIR); end

fprintf('=== HAC Mask Radius Sweep ===\n');
fprintf('Radii:    %s\n', num2str(RADII));
fprintf('Classes:  %d\n', N_CLASSES);

%% Load particles once — reused across all radii (~10-15 s, saves ~90 s total)
fprintf('\n[Setup] Loading %d particles...\n', 0);
files = dir(fullfile(DATA_DIR, '*.mrc'));
N     = length(files);
tmp   = dynamo_read(fullfile(DATA_DIR, files(1).name));
box   = size(tmp, 1);
data  = cell(N, 1);
for i = 1:N
    data{i} = dynamo_read(fullfile(DATA_DIR, files(i).name));
    if mod(i, 100) == 0, fprintf('  Loaded %d / %d\n', i, N); end
end
fprintf('  Done: %d particles, box %d^3\n', N, box);

%% Sweep
coph_scores = zeros(1, length(RADII));
t_sweep = tic;

for ri = 1:length(RADII)
    r          = RADII(ri);
    output_dir = fullfile(SWEEP_DIR, sprintf('radius_%s', strrep(sprintf('%.1f', r), '.', 'p')));
    coph_scores(ri) = hac_run_single(DATA_DIR, output_dir, r, N_CLASSES, data, files);
end

fprintf('\n=== Sweep complete in %.0f s ===\n', toc(t_sweep));

%% Write cophenetic summary table
summary_dir = fullfile(SWEEP_DIR, 'summary');
if ~exist(summary_dir, 'dir'), mkdir(summary_dir); end

fid = fopen(fullfile(summary_dir, 'cophenetic_scores.txt'), 'w');
fprintf(fid, 'radius\tcophenetic\n');
for ri = 1:length(RADII)
    fprintf(fid, '%d\t%.4f\n', RADII(ri), coph_scores(ri));
end
fclose(fid);

fprintf('Cophenetic scores:\n');
for ri = 1:length(RADII)
    fprintf('  r=%-3d  coph=%.4f\n', RADII(ri), coph_scores(ri));
end

%% Call Python for the comparison grid
PYTHON  = '/home/jblaser2/conda-envs/napari-0.4-env/bin/python3';
CMP_SCR = '/home/jblaser2/Research/STA/dynamo/dynamo_scripts/hac_sweep_compare.py';
cmd = sprintf('DISPLAY=:0 QT_QPA_PLATFORM=xcb %s %s "%s" 2>&1', PYTHON, CMP_SCR, SWEEP_DIR);
fprintf('\nGenerating sweep comparison grid...\n');
[~, out] = system(cmd);
lines = strsplit(strtrim(out), newline);
for k = 1:length(lines)
    if contains(lines{k}, 'Saved:') || contains(lines{k}, 'Error') || contains(lines{k}, 'error')
        fprintf('  %s\n', strtrim(lines{k}));
    end
end

fprintf('\nDone. Results in: %s\n', SWEEP_DIR);
