function build_masks_ref(rootdir)
%% build_masks_ref
% Build cylindrical alignment/CC masks and an initial reference (global
% average of all subtomograms) for the T4P pili classification pipeline.
%
% Pilus axis runs along Z. Cylinder geometry values below are reasonable
% starting points for 80^3 boxes; TUNE ali_radius/ali_height after viewing
% the global average central slices (see research.md Part II, §14).
%
% rootdir : STOPGAP project root

box = 80;

% Alignment mask: tightened to the compact central density measured from the
% global average (radial profile falls off past r~12px). The previous r=20/h=64
% mask let in a large noise shell + missing-wedge streak artifacts, which
% dominated the CC-matrix/PCA and produced noise-dominated class averages.
% "Very tight" setting (2026-06-04): focus purely on the dense core.
ali_radius = 8;    ali_height = 26;   ali_sigma = [3 3];
% CC mask (FLCF scoring): tighter still to focus the score on the pilus core
cc_radius  = 6;    cc_height  = 20;   cc_sigma  = [2 2];

mask_dir = fullfile(rootdir, 'masks');
if ~exist(mask_dir,'dir'), mkdir(mask_dir); end

ali = sg_cylinder([box box box], ali_radius, ali_height, ali_sigma);
cc  = sg_cylinder([box box box], cc_radius,  cc_height,  cc_sigma);

sg_mrcwrite(fullfile(mask_dir, 'mask_align.mrc'), single(ali));
sg_mrcwrite(fullfile(mask_dir, 'mask_cc.mrc'),    single(cc));
fprintf('[build_masks] wrote mask_align.mrc (r=%d h=%d) and mask_cc.mrc (r=%d h=%d)\n', ...
        ali_radius, ali_height, cc_radius, cc_height);

% Initial reference: normalize-then-average all subtomograms
d = dir(fullfile(rootdir, 'subtomograms', 'subtomo_*.mrc'));
n = numel(d);
if n == 0
    error('ACHTUNG!!! No subtomo_*.mrc files found in %s/subtomograms', rootdir);
end
fprintf('[build_masks] averaging %d subtomograms -> ref_1.mrc ...\n', n);

acc = zeros(box, box, box, 'single');
for i = 1:n
    v  = single(sg_mrcread(fullfile(d(i).folder, d(i).name)));
    mu = mean(v(:));
    sd = std(v(:));
    if sd > 0
        acc = acc + (v - mu) ./ sd;
    else
        acc = acc + (v - mu);
    end
end
ref = acc ./ n;

ref_dir = fullfile(rootdir, 'ref');
if ~exist(ref_dir,'dir'), mkdir(ref_dir); end

% STOPGAP's singleref loader (load_subtomo_references.m) always reads BOTH
% halfset references ref_A_1.mrc and ref_B_1.mrc (the h=1:2 loop), so the
% initial reference must be written per halfset. Gold-standard practice: both
% halves start from the same common initial model (the global average) and
% diverge through independent refinement. ref_1.mrc is the combined ref that
% later steps (e.g. PCA's initialize_ref_for_pca) read at their iteration.
ref = single(ref);
sg_mrcwrite(fullfile(ref_dir, 'ref_1.mrc'),   ref);
sg_mrcwrite(fullfile(ref_dir, 'ref_A_1.mrc'), ref);
sg_mrcwrite(fullfile(ref_dir, 'ref_B_1.mrc'), ref);
fprintf('[build_masks] wrote ref_1.mrc, ref_A_1.mrc, ref_B_1.mrc (global average of %d particles)\n', n);
end
