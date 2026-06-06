% dynamo_motor_easy_hac.m
% HAC classification on motor_easy synthetic data (694 particles, 96^3, GT-aligned).
% Uses RELION solvent mask (soft-edge sphere r=32 px, center Y-10) as CC mask.
% CC matrix is cached to disk; safe to interrupt and resume.
% Outputs: assignments_k2.csv, assignments_k3.csv (file,pred_label format)
%
% Run: ~/Applications/matlab/bin/matlab -nodisplay -nosplash -r "run('dynamo_motor_easy_hac.m'); exit;"
% from ~/Research/STA/dynamo/dynamo_scripts/ after activating Dynamo.

run('/home/jblaser2/Research/dynamo/dynamo_activate.m');

DATA_DIR = '/home/jblaser2/Research/synthetic_sta/motor_easy/production/subtomos/merged_all_aln';
OUT_DIR  = '/home/jblaser2/Research/STA/dynamo/dynamo_outputs/motor_easy_hac';
MASK_MRC = '/home/jblaser2/Research/STA/outputs/relion_motor_easy/solvent_mask.mrc';
KS       = [2, 3];

if ~exist(OUT_DIR, 'dir'), mkdir(OUT_DIR); end

fprintf('\n=== Dynamo HAC — motor_easy (%s) ===\n', datestr(now, 'HH:MM:SS'));

%% 1. Load mask
fprintf('[1/4] Loading mask...\n');
mask_vol = dynamo_read(MASK_MRC);
mask = mask_vol > 0.5;
fprintf('  Active voxels: %d / %d (%.1f%%)\n', sum(mask(:)), numel(mask), ...
    100 * sum(mask(:)) / numel(mask));

%% 2. Load particles (sorted alphabetically = subtomo_0000..0693)
fprintf('[2/4] Loading particles...\n');
d = dir(fullfile(DATA_DIR, 'subtomo_*.mrc'));
names = sort({d.name});
N   = length(names);
BOX = 96;
fprintf('  Found %d particles\n', N);
data = cell(N, 1);
for i = 1:N
    data{i} = dynamo_read(fullfile(DATA_DIR, names{i}));
    if mod(i, 100) == 0
        fprintf('  Loaded %d/%d\n', i, N);
    end
end
fprintf('  Done loading.\n');

%% 3. CC matrix (cached)
fprintf('[3/4] CC matrix...\n');
ccmatrix_file = fullfile(OUT_DIR, 'ccmatrix.mat');
if exist(ccmatrix_file, 'file')
    fprintf('  Loading cached CC matrix from %s\n', ccmatrix_file);
    S = load(ccmatrix_file);
    ccmatrix = S.ccmatrix;
    fprintf('  Loaded: %dx%d\n', size(ccmatrix, 1), size(ccmatrix, 2));
else
    n_pairs = N * (N - 1) / 2;
    fprintf('  Computing %d pairs...\n', n_pairs);
    t_cc = tic;
    ccmatrix = zeros(N, N);
    report_every = max(1, floor(N / 20));
    for i = 1:N
        for j = (i+1):N
            ccmatrix(i, j) = dynamo_pearson3d(data{i}, data{j}, mask);
        end
        if mod(i, report_every) == 0
            elapsed = toc(t_cc);
            frac = (i * (2*N - i - 1) / 2) / n_pairs;
            eta  = elapsed / max(frac, 1e-6) * (1 - frac);
            fprintf('  Row %d/%d  (%.0f%%, ETA ~%.0f s)\n', i, N, 100*frac, eta);
        end
    end
    ccmatrix = ccmatrix + ccmatrix';
    for i = 1:N, ccmatrix(i, i) = 1; end
    save(ccmatrix_file, 'ccmatrix');
    fprintf('  CC matrix computed in %.0f s\n', toc(t_cc));
end

%% 4. HAC + output
fprintf('[4/4] HAC...\n');
distMatrix = 1 - ccmatrix;
Y = squareform(distMatrix);
Z = linkage(Y, 'ward');
coph = cophenet(Z, Y);
fprintf('  Cophenetic correlation: %.4f\n', coph);

% Dendrogram
fig = figure('visible', 'off');
dendrogram(Z, 0);
title(sprintf('motor\\_easy HAC  N=%d  coph=%.3f', N, coph));
saveas(fig, fullfile(OUT_DIR, 'dendrogram.png'));
close(fig);

for k = KS
    T = cluster(Z, 'maxclust', k);

    % Print class sizes
    fprintf('  k=%d: ', k);
    for c = 1:k
        fprintf('class%d=%d ', c, sum(T == c));
    end
    fprintf('\n');

    % Predictions CSV (file,pred_label)
    assign_file = fullfile(OUT_DIR, sprintf('predictions_k%d.csv', k));
    fid = fopen(assign_file, 'w');
    fprintf(fid, 'file,pred_label\n');
    for i = 1:N
        fprintf(fid, '%s,%d\n', names{i}, T(i));
    end
    fclose(fid);
    fprintf('  -> %s\n', assign_file);

    % Class averages
    avg_dir = fullfile(OUT_DIR, sprintf('class_avgs_k%d', k));
    if ~exist(avg_dir, 'dir'), mkdir(avg_dir); end
    for c = 1:k
        idx = find(T == c);
        avg = zeros(BOX, BOX, BOX);
        for ki = 1:length(idx)
            avg = avg + data{idx(ki)};
        end
        dynamo_write(avg / length(idx), fullfile(avg_dir, sprintf('class_%02d.mrc', c)));
    end
end

fprintf('\n=== Done (%s) ===\n', datestr(now, 'HH:MM:SS'));
fprintf('Next: python3 score_dynamo_motor_easy.py\n');
