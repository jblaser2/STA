function build_inputs_t3ss(particle_dir, rootdir)
%% build_inputs_t3ss
% Build STOPGAP inputs from T3SS subtomo_XXXX.mrc files (415 particles, 48^3).
% Creates subtomograms/ symlinks, lists/allmotl_1.star, meta/tomo_nums.csv.
%
% particle_dir : ~/Research/synthetic_sta/injectisome/subtomos/merged_BC_t3ss
% rootdir      : ~/Research/stopgap_t3ss

files = dir(fullfile(particle_dir, 'subtomo_*.mrc'));
files = sort({files.name});
n = numel(files);
if n == 0
    error('No subtomo_*.mrc in %s', particle_dir);
end
fprintf('[t3ss] %d particles\n', n);

fn   = sg_get_motl_fields();
motl = struct();
for i = 1:size(fn,1)
    if strcmp(fn{i,2},'str')
        motl.(fn{i,1}) = repmat({''},n,1);
    else
        motl.(fn{i,1}) = zeros(n,1);
    end
end

sub_dir   = fullfile(rootdir, 'subtomograms');
lists_dir = fullfile(rootdir, 'lists');
meta_dir  = fullfile(rootdir, 'meta');
for d = {sub_dir, lists_dir, meta_dir}
    if ~exist(d{1},'dir'), mkdir(d{1}); end
end

% All particles treated as tomo 1 (single simulated tomogram pool)
for i = 1:n
    motl.tomo_num(i)    = 1;
    motl.object(i)      = i;
    motl.subtomo_num(i) = i;
    motl.motl_idx(i)    = i;
    motl.score(i)       = 1;
    motl.class(i)       = 1;

    src = fullfile(particle_dir, files{i});
    dst = fullfile(sub_dir, sprintf('subtomo_%d.mrc', i));
    if ~exist(dst, 'file')
        system(sprintf('ln -s "%s" "%s"', src, dst));
    end
end

% Gold-standard halfsets
hs = repmat({'A'}, n, 1);
hs(mod((1:n)', 2) == 0) = {'B'};
motl.halfset = hs;
motl.class   = int32(motl.class);

sg_motl_write2(fullfile(lists_dir, 'allmotl_1.star'), motl);
fprintf('[t3ss] wrote %d particles to lists/allmotl_1.star\n', n);

writematrix(1, fullfile(meta_dir, 'tomo_nums.csv'));
fprintf('[t3ss] wrote meta/tomo_nums.csv\n');
end
