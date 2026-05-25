function coph = hac_run_single(DATA_DIR, OUTPUT_DIR, MASK_RADIUS, N_CLASSES, data_in, files_in)
% HAC classification for one mask radius.
%
% data_in, files_in  - pre-loaded particles and file list (optional).
%                      If omitted, particles are loaded from DATA_DIR.
% Returns: coph      - cophenetic correlation coefficient

if ~exist(OUTPUT_DIR, 'dir'), mkdir(OUTPUT_DIR); end

fprintf('\n--- radius=%d, N_CLASSES=%d ---\n', MASK_RADIUS, N_CLASSES);
t_total = tic;

%% 1. Particles
if nargin >= 5 && ~isempty(data_in)
    data  = data_in;
    files = files_in;
    N     = length(data);
    box   = size(data{1}, 1);
    fprintf('[1/4] Using pre-loaded %d particles (box %d^3)\n', N, box);
else
    fprintf('[1/4] Loading particles...\n');
    files = dir(fullfile(DATA_DIR, '*.mrc'));
    if isempty(files), error('No .mrc files found in %s', DATA_DIR); end
    N     = length(files);
    tmp   = dynamo_read(fullfile(DATA_DIR, files(1).name));
    box   = size(tmp, 1);
    data  = cell(N, 1);
    for i = 1:N
        data{i} = dynamo_read(fullfile(DATA_DIR, files(i).name));
    end
    fprintf('  Loaded %d particles\n', N);
end

%% 2. Mask
fprintf('[2/4] Building spherical mask (radius=%d)...\n', MASK_RADIUS);
center = (box / 2 + 1) * ones(1, 3);
radii  = MASK_RADIUS * ones(1, 3);
mask   = dynamo_ellipsoid(radii, box * ones(1, 3), center, 2) > 0.5;
fprintf('  Active voxels: %d / %d (%.1f%%)\n', ...
    sum(mask(:)), box^3, 100 * sum(mask(:)) / box^3);

%% 3. CC matrix
fprintf('[3/4] CC matrix...\n');
ccmatrix_file = fullfile(OUTPUT_DIR, 'ccmatrix.mat');
if exist(ccmatrix_file, 'file')
    S = load(ccmatrix_file);
    ccmatrix = S.ccmatrix;
    fprintf('  Loaded from cache.\n');
else
    t_cc = tic;
    ccmatrix = zeros(N, N);
    report_every = max(1, floor(N / 20));
    for i = 1:N
        for j = (i+1):N
            ccmatrix(i,j) = dynamo_pearson3d(data{i}, data{j}, mask);
        end
        if mod(i, report_every) == 0
            elapsed = toc(t_cc);
            frac    = (i * (2*N - i - 1) / 2) / (N*(N-1)/2);
            eta     = elapsed / max(frac, 1e-6) * (1 - frac);
            fprintf('  Row %d/%d  (%.0f%%, ETA ~%.0f s)\n', i, N, 100*frac, eta);
        end
    end
    ccmatrix = ccmatrix + ccmatrix';
    for i = 1:N, ccmatrix(i,i) = 1; end
    save(ccmatrix_file, 'ccmatrix');
    fprintf('  CC matrix computed in %.0f s\n', toc(t_cc));
end

%% 4. HAC
fprintf('[4/4] HAC (N=%d classes)...\n', N_CLASSES);
distMatrix = 1 - ccmatrix;
Y = squareform(distMatrix);
Z = linkage(Y, 'ward');
coph = cophenet(Z, Y);
fprintf('  Cophenetic: %.4f\n', coph);

T = cluster(Z, 'maxclust', N_CLASSES);

% Dendrogram
fig = figure('visible', 'off');
dendrogram(Z, 0);
title(sprintf('r=%d  N=%d  coph=%.3f', MASK_RADIUS, N_CLASSES, coph));
saveas(fig, fullfile(OUTPUT_DIR, 'dendrogram.png'));
close(fig);

% Class averages
avg_dir = fullfile(OUTPUT_DIR, 'class_averages');
if ~exist(avg_dir, 'dir'), mkdir(avg_dir); end
fprintf('  Class sizes: ');
for c = 1:N_CLASSES
    idx = find(T == c);
    fprintf('%d(%d) ', c, length(idx));
    avg = zeros(box, box, box);
    for k = 1:length(idx), avg = avg + data{idx(k)}; end
    dynamo_write(avg / length(idx), fullfile(avg_dir, sprintf('class_%02d.mrc', c)));
end
fprintf('\n');

% Assignments
assign_file = fullfile(OUTPUT_DIR, sprintf('class_assignments_%dclass.txt', N_CLASSES));
fid = fopen(assign_file, 'w');
fprintf(fid, 'particle\tclass\n');
for i = 1:N
    fprintf(fid, '%s\t%d\n', files(i).name, T(i));
end
fclose(fid);

% Save linkage tree and results for downstream analysis
save(fullfile(OUTPUT_DIR, 'hac_result.mat'), 'Z', 'T', 'coph', 'MASK_RADIUS', 'N_CLASSES');

% PNG comparison
PYTHON  = '/home/jblaser2/conda-envs/napari-0.4-env/bin/python3';
PNG_SCR = '/home/jblaser2/Research/STA/dynamo/dynamo_scripts/save_comparison_png.py';
cmd = sprintf('DISPLAY=:0 QT_QPA_PLATFORM=xcb %s %s "%s" 2>&1', PYTHON, PNG_SCR, OUTPUT_DIR);
[~, png_out] = system(cmd);
% extract the "Saved:" line only
lines = strsplit(strtrim(png_out), newline);
for k = 1:length(lines)
    if contains(lines{k}, 'Saved:'), fprintf('  %s\n', strtrim(lines{k})); end
end

fprintf('  Total: %.0f s\n', toc(t_total));
end
