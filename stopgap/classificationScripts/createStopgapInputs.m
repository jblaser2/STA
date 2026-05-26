%% createStopgapInputs.m
% Creates all required input files for a STOPGAP classification run.
% Run this script from subtomo_project/ in MATLAB with sg_toolbox/ on the path.
%
% Expects subtomograms already present in subtomograms/ named as:
%   aligned_tom{N}_P{K}.mrc
% This script creates symlinks subtomo_1.mrc ... subtomo_N.mrc pointing to
% the original files (same directory, relative symlinks), then builds the
% motivelist, wedgelist, initial reference, and masks.
%
% Particles are assumed centered in the box and aligned with the z-axis
% (phi=0, psi=0, the=0 as starting orientations).

%% ---- USER PARAMETERS — edit these ----------------------------------------

box_size   = 80;      % voxels; edge length of the cubic subvolume

% Imaging parameters — applied uniformly to all tomograms
pixel_size = 13.33;    % Angstroms
tilt_min   = -60;     % degrees
tilt_max   =  60;     % degrees

% Original tomogram dimensions (for wedge mask generation)
tomo_x = 500;
tomo_y = 500;
tomo_z = 300;

%% --------------------------------------------------------------------------

%% 0. Discover files and create symlinks

raw = dir('subtomograms/aligned_tom*_P*.mrc');
if isempty(raw)
    error('No aligned_tom*_P*.mrc files found in subtomograms/. Run from subtomo_project/.');
end

% Sort deterministically so subtomo_num assignment is stable across runs
fnames = sort({raw.name});
n_particles = numel(fnames);
fprintf('Found %d subvolumes in subtomograms/\n', n_particles);

% Parse tomo_num from each filename and create numbered symlinks
tomo_num_all = zeros(n_particles, 1, 'int32');

for i = 1:n_particles
    tok = regexp(fnames{i}, 'aligned_tom(\d+)_P(\d+)\.mrc', 'tokens', 'once');
    if isempty(tok)
        error('Filename does not match expected pattern: %s', fnames{i});
    end
    tomo_num_all(i) = str2double(tok{1});

    link = sprintf('subtomograms/subtomo_%d.mrc', i);
    if ~exist(link, 'file')
        % Relative symlink: target is just the filename (same directory)
        system(sprintf('ln -s "%s" "%s"', fnames{i}, link));
    end
end

% Write the mapping for reference and post-processing traceability
fid = fopen('lists/subtomo_mapping.txt', 'w');
fprintf(fid, '# subtomo_num  tomo_num  original_filename\n');
for i = 1:n_particles
    fprintf(fid, '%d  %d  %s\n', i, tomo_num_all(i), fnames{i});
end
fclose(fid);
fprintf('Symlinks created. Mapping written to lists/subtomo_mapping.txt\n');

%% 1. Motivelist

centre = box_size / 2;

% Random halfset assignment (required for FSC during averaging)
% STOPGAP requires single-char 'A'/'B' values — NOT 'h1'/'h2'.
% sg_motl_write uses %-1c format; a 2-char string would produce two printf
% values and corrupt the STAR file with a second line per particle.
rng(42);
h = ceil(rand(n_particles, 1) * 2);
halfset_options = {'A', 'B'};
halfset_cell = arrayfun(@(x) halfset_options{x}, h, 'UniformOutput', false);

% Build struct array (one element per particle) — sg_motl_write requires this
motl = struct( ...
    'motl_idx',    num2cell((1:n_particles)'), ...
    'tomo_num',    num2cell(double(tomo_num_all)), ...
    'object',      num2cell(ones(n_particles, 1)), ...
    'subtomo_num', num2cell((1:n_particles)'), ...
    'halfset',     halfset_cell, ...
    'orig_x',      num2cell(repmat(centre, n_particles, 1)), ...
    'orig_y',      num2cell(repmat(centre, n_particles, 1)), ...
    'orig_z',      num2cell(repmat(centre, n_particles, 1)), ...
    'score',       num2cell(ones(n_particles, 1)), ...
    'x_shift',     num2cell(zeros(n_particles, 1)), ...
    'y_shift',     num2cell(zeros(n_particles, 1)), ...
    'z_shift',     num2cell(zeros(n_particles, 1)), ...
    'phi',         num2cell(zeros(n_particles, 1)), ...
    'psi',         num2cell(zeros(n_particles, 1)), ...
    'the',         num2cell(zeros(n_particles, 1)), ...
    'class',       num2cell(ones(n_particles, 1)) ...
);

sg_motl_write('lists/motl_1.star', motl);
disp('Motivelist written to lists/motl_1.star');

%% 2. Wedgelist — one entry per unique tomogram

unique_tomos = unique(double(tomo_num_all));
n_tomos = numel(unique_tomos);
fprintf('Building wedgelist for %d unique tomograms\n', n_tomos);

tilt_angles = linspace(tilt_min, tilt_max, abs(tilt_max - tilt_min) + 1);
% defocus and exposure are 'array' type fields in sg_get_wedgelist_fields —
% sg_wedgelist_write distributes them element-by-element across tilt angles,
% so they must be vectors the same length as tilt_angles, not scalars.
zero_angles = zeros(size(tilt_angles));

% Pre-allocate struct array
wedge = repmat(struct('tomo_num', 0, 'pixelsize', pixel_size, ...
                      'tomo_x', tomo_x, 'tomo_y', tomo_y, 'tomo_z', tomo_z, ...
                      'z_shift', 0, 'tilt_angle', tilt_angles, ...
                      'defocus', zero_angles, 'exposure', zero_angles), n_tomos, 1);
for j = 1:n_tomos
    wedge(j).tomo_num = unique_tomos(j);
end

sg_wedgelist_write('lists/wedgelist.star', wedge);
fprintf('Wedgelist written to lists/wedgelist.star (%d tomograms)\n', n_tomos);

%% 3. Initial reference — unaligned average over all particles

ref = zeros(box_size, box_size, box_size, 'single');
fprintf('Reading %d volumes to compute initial reference...\n', n_particles);
for i = 1:n_particles
    v = single(sg_mrcread(sprintf('subtomograms/subtomo_%d.mrc', i)));
    ref = ref + v;
end
ref = ref / n_particles;

% Normalize to zero mean, unit std within a soft sphere
sph = sg_sphere(box_size, floor(box_size/2) - 2, 3);
ref = sg_normalize_under_mask(ref, sph);

% STOPGAP loads per-halfset references named {ref_name}_A_{iter}.mrc and
% {ref_name}_B_{iter}.mrc — a single merged file is never read.
sg_mrcwrite('ref/ref_class1_A_1.mrc', ref);
sg_mrcwrite('ref/ref_class1_B_1.mrc', ref);
disp('Initial references written to ref/ref_class1_A_1.mrc and ref/ref_class1_B_1.mrc');

%% 4. Masks

% Alignment mask: soft sphere filling most of the box
ali_mask = sg_sphere(box_size, floor(box_size/2) - 3, 3);
sg_mrcwrite('masks/ali_mask.mrc', single(ali_mask));

% Cross-correlation mask: small sphere constraining shift search to ±cc_radius voxels
cc_mask = sg_sphere(box_size, floor(box_size/8), 2);
sg_mrcwrite('masks/ccmask.mrc', single(cc_mask));

disp('Masks written to masks/');
fprintf('Done. %d particles from %d tomograms. Ready for subtomoParams.sh.\n', ...
        n_particles, n_tomos);
