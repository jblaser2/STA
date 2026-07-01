% dalign_fm_easy.m
% Production subtomogram alignment of FM_easy particles using Dynamo MRA.
% Class-blind: single global reference, no class information used.
%
% Input:  easy_AC_dalign/data/  (542 particles, 96^3, 13.33 A/px)
%         easy_AC_dalign/pair.tbl  (identity poses)
%         easy_AC_dalign/initial_ref.mrc  (global average)
%         easy_AC_dalign/diff_sphere_r23_y55.mrc  (classification mask)
%
% Output: easy_AC_dalign/dalign_fm_easy/  (Dynamo project)
%         easy_AC_dalign/final_aligned.tbl  (refined poses, 40 cols)
%
% Run:  MATLAB -batch "run('dalign_fm_easy.m')"
% Log:  nohup ... > run_dalign.log 2>&1 &

run('/home/jblaser2/Research/dynamo/dynamo_activate.m');

% PCT parpool fix: suppress ServiceHost + explicit pool to survive long run
setenv('MW_SERVICE_HOST_DISABLE', '1');
if isempty(gcp('nocreate'))
    pool = parpool('Processes', 16);
    pool.IdleTimeout = Inf;
    fprintf('Started parpool: %d workers\n', pool.NumWorkers);
end

OUTDIR  = '/home/jblaser2/Research/STA/packages/dynamo/dynamo_outputs/easy_AC_dalign';
DATA    = fullfile(OUTDIR, 'data');
TBL     = fullfile(OUTDIR, 'pair.tbl');
MASK    = fullfile(OUTDIR, 'diff_sphere_r23_y55.mrc');
TMPL    = fullfile(OUTDIR, 'initial_ref.mrc');
PRJNAME = 'dalign_fm_easy';

cd(OUTDIR);

fprintf('\n=== Dynamo dalign — FM_easy (%s) ===\n', datestr(now, 'HH:MM:SS'));
fprintf('Data: %s\n', DATA);
fprintf('Mask: %s\n', MASK);

%% Create or reload alignment project
prj_dir = fullfile(OUTDIR, PRJNAME);
if exist(prj_dir, 'dir')
    fprintf('Reloading existing project %s...\n', PRJNAME);
else
    fprintf('Creating alignment project %s...\n', PRJNAME);
    dcp.new(PRJNAME, 'd', DATA, 't', TBL, 'template', TMPL, ...
            'masks', 'default', 'show', 0, 'fo', true);

    % 3-round strategy: coarse (dim=48) → medium (dim=64) → fine (dim=96)
    %
    % Round 1: broad angular search on 2× downsampled box
    %   dim=48 = 96/2 — fast but covers full angular space
    dvput(PRJNAME, 'd', ...
        'nref_r1', 1, 'ite_r1', 3, 'dim_r1', 48, ...
        'cr_r1',  90, 'cs_r1', 30, ...
        'ir_r1', 180, 'is_r1', 30, ...
        'lim_r1', 8,  'limm_r1', 2, ...
        'sym_r1', 'c1');

    % Round 2: medium angular refinement on 1.5× box
    dvput(PRJNAME, 'd', ...
        'nref_r2', 1, 'ite_r2', 3, 'dim_r2', 64, ...
        'cr_r2',  25, 'cs_r2',  8, ...
        'ir_r2',  25, 'is_r2',  8, ...
        'lim_r2', 4,  'limm_r2', 2, ...
        'sym_r2', 'c1');

    % Round 3: fine local refinement at full resolution
    dvput(PRJNAME, 'd', ...
        'nref_r3', 1, 'ite_r3', 3, 'dim_r3', 96, ...
        'cr_r3',  10, 'cs_r3',  3, ...
        'ir_r3',  10, 'is_r3',  3, ...
        'lim_r3', 2,  'limm_r3', 2, ...
        'sym_r3', 'c1');

    dvput(PRJNAME, 'd', 'dst', 'matlab_parfor');
    dvput(PRJNAME, 'd', 'cores', 16);

    dvcheck(PRJNAME);
    dvunfold(PRJNAME);
    fprintf('Project created and unfolded.\n');
end

% Ensure cores are set correctly (also applies when reloading)
dvput(PRJNAME, 'd', 'cores', 16);

%% Run alignment
fprintf('\n=== Starting dvrun (%s) ===\n', datestr(now, 'HH:MM:SS'));
dvrun(PRJNAME);
fprintf('=== dvrun complete (%s) ===\n', datestr(now, 'HH:MM:SS'));

%% Locate and save final table
% Iteration numbering: next_iteration.txt holds the NEXT iteration to run.
% Last completed = next_iteration - 1.
nxt_file = fullfile(OUTDIR, PRJNAME, 'next_iteration.txt');
if exist(nxt_file, 'file')
    fid = fopen(nxt_file, 'r');
    nxt = fscanf(fid, '%d', 1);
    fclose(fid);
    last_ite = nxt - 1;
else
    % Fallback: find highest-numbered ite_XXXX directory
    dirs = dir(fullfile(OUTDIR, PRJNAME, 'results', 'ite_*'));
    nums = arrayfun(@(d) str2double(d.name(5:end)), dirs);
    last_ite = max(nums);
end
fprintf('Last completed iteration: %d\n', last_ite);

tbl_path = fullfile(OUTDIR, PRJNAME, 'results', ...
    sprintf('ite_%04d', last_ite), 'averages', ...
    sprintf('refined_table_ref_001_ite_%04d.tbl', last_ite));

if exist(tbl_path, 'file')
    copyfile(tbl_path, fullfile(OUTDIR, 'final_aligned.tbl'));
    fprintf('Final table saved: %s\n', fullfile(OUTDIR, 'final_aligned.tbl'));
    t = dread(fullfile(OUTDIR, 'final_aligned.tbl'));
    fprintf('Table size: %d x %d\n', size(t,1), size(t,2));
    fprintf('Shift RMS: dx=%.3f dy=%.3f dz=%.3f px\n', ...
        sqrt(mean(t(:,4).^2)), sqrt(mean(t(:,5).^2)), sqrt(mean(t(:,6).^2)));
else
    % Exhaustive search fallback
    fprintf('WARNING: expected table not found at:\n  %s\n', tbl_path);
    fprintf('Searching for refined_table_ref_001...\n');
    found = dir(fullfile(OUTDIR, PRJNAME, '**', 'refined_table_ref_001_*.tbl'));
    if ~isempty(found)
        % Take the last one (highest iteration)
        [~, idx] = max([found.datenum]);
        src = fullfile(found(idx).folder, found(idx).name);
        copyfile(src, fullfile(OUTDIR, 'final_aligned.tbl'));
        fprintf('Final table found and saved: %s\n', src);
    else
        fprintf('ERROR: no refined table found — extraction will fail.\n');
    end
end

fprintf('\n=== Done (%s) ===\n', datestr(now, 'HH:MM:SS'));
fprintf('Next: python3 extract_dalign_fm_easy.py\n');
