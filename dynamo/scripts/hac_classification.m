% HAC classification of pre-aligned subtomograms using Dynamo
%
% Requires: Dynamo activated in MATLAB (run <DYNAMO_ROOT>/dynamo_activate.m)
%           MATLAB Statistics and Machine Learning Toolbox (for linkage/cluster)
%
% Usage: run this script from any directory after activating Dynamo.
%
% Outputs (in OUTPUT_DIR):
%   class_averages/class_<N>.mrc   - average volume for each class
%   class_assignments.txt          - particle filename -> class index
%   ccmatrix.mat                   - saved N×N CC matrix (reuse without recomputing)
%   dendrogram.png                 - dendrogram visualization

% -------------------------------------------------------------------------
% SETTINGS -- edit these
% -------------------------------------------------------------------------

DATA_DIR    = '/home/jblaser2/Research/STA/subtomos_mrc';
OUTPUT_DIR  = '/home/jblaser2/Research/STA/dynamo/outputs/hac_classification';

N_CLASSES   = 3;     % 2 pili conformations + 1 noisy/junk class

% Spherical mask radius in voxels. Box is 80^3.
MASK_RADIUS = 20;

% -------------------------------------------------------------------------

fprintf('=== Dynamo HAC Classification ===\n');
fprintf('Data:      %s\n', DATA_DIR);
fprintf('Output:    %s\n', OUTPUT_DIR);
fprintf('Classes:   %d\n', N_CLASSES);

%% 1. Load all particles
fprintf('\n[1/4] Loading particles...\n');

files = dir(fullfile(DATA_DIR, '*.mrc'));
if isempty(files)
    error('No .mrc files found in %s', DATA_DIR);
end
N = length(files);
fprintf('  Found %d particles\n', N);

% Read first to get box size
tmp = dynamo_read(fullfile(DATA_DIR, files(1).name));
box = size(tmp, 1);
fprintf('  Box size: %d^3\n', box);

data = cell(N, 1);
for i = 1:N
    data{i} = dynamo_read(fullfile(DATA_DIR, files(i).name));
    if mod(i, 50) == 0
        fprintf('  Loaded %d / %d\n', i, N);
    end
end
fprintf('  Done loading.\n');

%% 2. Build spherical mask
fprintf('\n[2/4] Building spherical mask (radius=%d voxels)...\n', MASK_RADIUS);
center  = (box / 2 + 1) * ones(1, 3);
radii   = MASK_RADIUS * ones(1, 3);
mask    = dynamo_ellipsoid(radii, box * ones(1, 3), center, 2);
mask    = mask > 0.5;
fprintf('  Active voxels: %d / %d (%.1f%%)\n', ...
    sum(mask(:)), box^3, 100 * sum(mask(:)) / box^3);

%% 3. Compute CC matrix (Pearson inside mask, no wedge correction)
fprintf('\n[3/4] Computing %dx%d CC matrix (~%d pairs)...\n', N, N, N*(N-1)/2);

ccmatrix_file = fullfile(OUTPUT_DIR, 'ccmatrix.mat');
if ~exist(OUTPUT_DIR, 'dir')
    mkdir(OUTPUT_DIR);
end

if exist(ccmatrix_file, 'file')
    fprintf('  Found existing ccmatrix, loading it.\n');
    S = load(ccmatrix_file);
    ccmatrix = S.ccmatrix;
else
    t_start = tic;
    ccmatrix = zeros(N, N);
    report_every = max(1, floor(N / 20));
    for i = 1:N
        for j = (i+1):N
            ccmatrix(i,j) = dynamo_pearson3d(data{i}, data{j}, mask);
        end
        if mod(i, report_every) == 0
            elapsed = toc(t_start);
            frac    = (i * (2*N - i - 1) / 2) / (N*(N-1)/2);
            eta     = elapsed / max(frac, 1e-6) * (1 - frac);
            fprintf('  Row %d/%d  (%.0f%% done, ETA ~%.0f s)\n', i, N, 100*frac, eta);
        end
    end
    ccmatrix = ccmatrix + ccmatrix';
    for i = 1:N
        ccmatrix(i,i) = 1;
    end
    save(ccmatrix_file, 'ccmatrix');
    fprintf('  CC matrix saved to %s\n', ccmatrix_file);
end

%% 4. HAC clustering and output
fprintf('\n[4/4] Running HAC (N=%d classes)...\n', N_CLASSES);

distMatrix = 1 - ccmatrix;
Y = squareform(distMatrix);
Z = linkage(Y, 'ward');
c = cophenet(Z, Y);
fprintf('  Cophenetic correlation: %.4f  (closer to 1 = better hierarchy)\n', c);

T = cluster(Z, 'maxclust', N_CLASSES);

% Save dendrogram
fig = figure('visible', 'off');
dendrogram(Z, 0);
title(sprintf('HAC Dendrogram  (%d particles, Ward linkage)', N));
saveas(fig, fullfile(OUTPUT_DIR, 'dendrogram.png'));
close(fig);
fprintf('  Dendrogram saved.\n');

% Class averages
avg_dir = fullfile(OUTPUT_DIR, 'class_averages');
if ~exist(avg_dir, 'dir'), mkdir(avg_dir); end

fprintf('\n  Class sizes:\n');
for c = 1:N_CLASSES
    idx = find(T == c);
    fprintf('    Class %d: %d particles\n', c, length(idx));
    avg = zeros(box, box, box);
    for k = 1:length(idx)
        avg = avg + data{idx(k)};
    end
    avg = avg / length(idx);
    out_file = fullfile(avg_dir, sprintf('class_%02d.mrc', c));
    dynamo_write(avg, out_file);
end

% Assignment table — saved with class count in filename so multiple runs don't overwrite each other
assign_file = fullfile(OUTPUT_DIR, sprintf('class_assignments_%dclass.txt', N_CLASSES));
fid = fopen(assign_file, 'w');
fprintf(fid, 'particle\tclass\n');
for i = 1:N
    fprintf(fid, '%s\t%d\n', files(i).name, T(i));
end
fclose(fid);

fprintf('\n=== Done ===\n');
fprintf('Class averages: %s/class_averages/\n', OUTPUT_DIR);
fprintf('Assignments:    %s\n', assign_file);  % class_assignments_<N>class.txt
fprintf('Dendrogram:     %s/dendrogram.png\n', OUTPUT_DIR);
fprintf('\nTo re-run with a different number of classes without recomputing\n');
fprintf('the CC matrix, set N_CLASSES and run the script again\n');
fprintf('(the saved ccmatrix.mat will be reloaded automatically).\n');

% Auto-generate comparison PNG
PYTHON  = '/home/jblaser2/conda-envs/napari-0.4-env/bin/python3';
PNG_SCR = '/home/jblaser2/Research/STA/dynamo/scripts/save_comparison_png.py';
cmd = sprintf('DISPLAY=:0 QT_QPA_PLATFORM=xcb %s %s "%s"', PYTHON, PNG_SCR, OUTPUT_DIR);
fprintf('\nGenerating comparison PNG...\n');
[status, out] = system(cmd);
if status == 0
    fprintf('%s\n', strtrim(out));
else
    fprintf('[warning] PNG generation failed:\n%s\n', out);
end

fprintf('\nTo open class averages in napari:\n');
fprintf('  DISPLAY=:0 QT_QPA_PLATFORM=xcb %s \\\n', PYTHON);
fprintf('    /home/jblaser2/Research/STA/dynamo/scripts/view_classes.py "%s"\n', OUTPUT_DIR);
