function build_inputs(particle_dir, rootdir)
%% build_inputs
% Map aligned_tom<T>_P<NNNN>.mrc files to STOPGAP's subtomo_<n>.mrc naming
% via symlinks. Writes lists/allmotl_1.star (type-2 motl) and
% meta/tomo_nums.csv for the wedgelist builder.
%
% particle_dir : folder containing aligned_tom*_P*.mrc files
% rootdir      : STOPGAP project root (e.g. '/home/ejl62/Pili_class')

files = dir(fullfile(particle_dir, 'aligned_tom*_P*.mrc'));
n = numel(files);
if n == 0
    error('ACHTUNG!!! No aligned_tom*_P*.mrc files found in %s', particle_dir);
end
fprintf('[build_inputs] found %d particles in %s\n', n, particle_dir);

% Initialize type-2 motl struct (one row per particle)
fn = sg_get_motl_fields();          % 16x3 cell {name, type, format}
motl = struct();
for i = 1:size(fn,1)
    if strcmp(fn{i,2},'str')
        motl.(fn{i,1}) = repmat({''},n,1);
    else
        motl.(fn{i,1}) = zeros(n,1);
    end
end

% Ensure required directories exist
sub_dir   = fullfile(rootdir, 'subtomograms');
lists_dir = fullfile(rootdir, 'lists');
meta_dir  = fullfile(rootdir, 'meta');
for d = {sub_dir, lists_dir, meta_dir}
    if ~exist(d{1},'dir'), mkdir(d{1}); end
end

% Fill motl and create symlinks
for i = 1:n
    tok = regexp(files(i).name, 'aligned_tom(\d+)_P(\d+)\.mrc', 'tokens', 'once');
    if isempty(tok)
        error('ACHTUNG!!! Unexpected filename: %s', files(i).name);
    end
    motl.tomo_num(i)    = str2double(tok{1});
    motl.object(i)      = str2double(tok{2});   % particle-within-tomo id
    motl.subtomo_num(i) = i;                    % sequential id used in filenames
    motl.motl_idx(i)    = i;
    motl.score(i)       = 1;                    % placeholder; no score yet
    motl.class(i)       = 1;

    src = fullfile(files(i).folder, files(i).name);
    dst = fullfile(sub_dir, sprintf('subtomo_%d.mrc', i));
    if ~exist(dst, 'file')
        ret = system(sprintf('ln -s "%s" "%s"', src, dst));
        if ret ~= 0
            error('ACHTUNG!!! Failed to symlink: %s -> %s', src, dst);
        end
    end
end

% Gold-standard halfsets: odd index -> A, even index -> B
hs = repmat({'A'}, n, 1);
hs(mod((1:n)', 2) == 0) = {'B'};
motl.halfset = hs;
motl.class   = int32(motl.class);

sg_motl_write2(fullfile(lists_dir, 'allmotl_1.star'), motl);
fprintf('[build_inputs] wrote %d particles to lists/allmotl_1.star\n', n);

% Tomo list for build_wedgelist
tomo_nums = unique(motl.tomo_num);
writematrix(tomo_nums, fullfile(meta_dir, 'tomo_nums.csv'));
fprintf('[build_inputs] %d unique tomograms written to meta/tomo_nums.csv\n', numel(tomo_nums));
end
