% compute_fsc.m — split-half FSC for each class at r=7.2 optimal mask
%
% Reads:  dynamo_outputs/hac_sweep_fine/radius_7p2/hac_result.mat
% Writes: dynamo_final_results/fsc/fsc_class<N>.txt  (shell_freq  fsc_value)
%         dynamo_final_results/fsc/resolution.txt     (summary)

DATA_DIR   = '/home/jblaser2/Research/STA/subtomos_mrc';
R72_DIR    = '/home/jblaser2/Research/STA/dynamo/dynamo_outputs/hac_sweep_final_pick/radius_8p9';
OUTPUT_DIR = '/home/jblaser2/Research/STA/dynamo/dynamo_final_results';
PIXEL_ANG  = 13.328;   % Angstroms per voxel

fsc_dir = fullfile(OUTPUT_DIR, 'fsc');
if ~exist(fsc_dir, 'dir'), mkdir(fsc_dir); end

% Load assignments and parameters
mat = load(fullfile(R72_DIR, 'hac_result.mat'));
T         = mat.T;
N_CLASSES = mat.N_CLASSES;
fprintf('Loaded assignments: %d particles, %d classes\n', length(T), N_CLASSES);

% Load particles
fprintf('Loading particles...\n');
files = dir(fullfile(DATA_DIR, '*.mrc'));
N   = length(files);
tmp = dynamo_read(fullfile(DATA_DIR, files(1).name));
box = size(tmp, 1);
data = cell(N, 1);
for i = 1:N
    data{i} = dynamo_read(fullfile(DATA_DIR, files(i).name));
end
fprintf('Loaded %d particles (box %d^3)\n', N, box);

% FSC threshold at 0.5 (half-bit criterion for small N is more appropriate,
% but 0.5 is conventional for class averages)
FSC_THRESHOLD = 0.5;

res_summary = fopen(fullfile(fsc_dir, 'resolution.txt'), 'w');
fprintf(res_summary, 'class\tn_particles\tres_voxels\tres_ang_fsc05\tres_ang_fsc0143\tn_half1\tn_half2\n');

for c = 1:N_CLASSES
    idx = find(T == c);
    fprintf('\nClass %d: %d particles\n', c, length(idx));

    % Random split into two halves (fixed seed for reproducibility)
    rng(42);
    perm  = idx(randperm(length(idx)));
    half1 = perm(1 : floor(end/2));
    half2 = perm(floor(end/2)+1 : end);
    fprintf('  Half1: %d   Half2: %d\n', length(half1), length(half2));

    avg1 = zeros(box, box, box);
    for k = 1:length(half1), avg1 = avg1 + data{half1(k)}; end
    avg1 = avg1 / length(half1);

    avg2 = zeros(box, box, box);
    for k = 1:length(half2), avg2 = avg2 + data{half2(k)}; end
    avg2 = avg2 / length(half2);

    % FSC — pass apix so res_05/res_013 are in Angstroms
    fsc_result = dynamo_fsc(avg1, avg2, 'apix', PIXEL_ANG);
    fsc_vals   = fsc_result.fsc;
    n_shells   = length(fsc_vals);
    shells     = linspace(1/(2*n_shells), 0.5, n_shells);  % spatial freq 1/vox
    res_ang    = fsc_result.res_05;      % resolution at FSC=0.5 in Angstroms
    res_vox    = res_ang / PIXEL_ANG;
    fprintf('  Resolution (FSC=0.5): %.1f vox = %.1f Ang\n', res_vox, res_ang);
    fprintf('  Resolution (FSC=0.143): %.1f Ang\n', fsc_result.res_013);

    % Save FSC curve
    out = fullfile(fsc_dir, sprintf('fsc_class%02d.txt', c));
    fid = fopen(out, 'w');
    fprintf(fid, 'shell_freq\tfsc_value\n');
    for s = 1:length(shells)
        fprintf(fid, '%.6f\t%.6f\n', shells(s), fsc_vals(s));
    end
    fclose(fid);

    fprintf(res_summary, '%d\t%d\t%.2f\t%.2f\t%.2f\t%d\t%d\n', ...
        c, length(idx), res_vox, res_ang, fsc_result.res_013, length(half1), length(half2));
end

fclose(res_summary);
fprintf('\nFSC files written to %s\n', fsc_dir);
