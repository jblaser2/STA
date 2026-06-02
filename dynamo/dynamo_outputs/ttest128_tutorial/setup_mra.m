% Two-stage Dynamo alignment+classification project for the dtutorial set.
% Cold start from initial.tbl (identity poses / random orientations).
%   Rounds 1-3: single reference (nref=1) full-sphere alignment -> consensus
%   Rounds 4-6: two references (nref=2) local refine + class swapping
% Seed reference = ttest128/template.em (reasonable ab-initio initial model).
set(0,'DefaultFigureVisible','off');
run('/home/jblaser2/Research/dynamo/dynamo_activate.m');

outdir = '/home/jblaser2/Research/STA/dynamo/dynamo_outputs/ttest128_tutorial';
cd(outdir);

pname    = 'mra_ttest128';
dataF    = fullfile(outdir,'ttest128','data');
tblInit  = fullfile(outdir,'ttest128','initial.tbl');
template = fullfile(outdir,'ttest128','template.em');

% fresh project
if exist(fullfile(outdir,pname),'dir');     rmdir(fullfile(outdir,pname),'s');     end
if exist(fullfile(outdir,[pname '.empty']),'dir'); rmdir(fullfile(outdir,[pname '.empty']),'s'); end

% --- create project (no GUI) ---
dcp.new(pname,'d',dataF,'t',tblInit,'template',template,'masks','default','show',0,'fo',true);

% --- round-by-round parameters (save to disk). Box is 40^3 -> dim=40 ---
% Stage 1: single-reference alignment, narrowing angular search
dvput(pname,'d', ...
  ... % round 1: full sphere, coarse
  'dim_r1',40,'sym_r1','c8','ite_r1',3, 'nref_r1',1, 'cr_r1',360,'cs_r1',30, 'ir_r1',360,'is_r1',30, 'lim_r1',8,'limm_r1',1, ...
  ... % round 2: medium cone
  'dim_r2',40,'sym_r2','c8','ite_r2',3, 'nref_r2',1, 'cr_r2',60, 'cs_r2',15, 'ir_r2',45, 'is_r2',10, 'lim_r2',6,'limm_r2',1, ...
  ... % round 3: tight refine
  'dim_r3',40,'sym_r3','c8','ite_r3',3, 'nref_r3',1, 'cr_r3',30, 'cs_r3',8,  'ir_r3',20, 'is_r3',5,  'lim_r3',4,'limm_r3',1);

% Stage 2: switch to 2 references (classification) + embedded MRA class swapping
dvput(pname,'d', ...
  'dim_r4',40,'sym_r4','c8','ite_r4',3, 'nref_r4',2, 'cr_r4',20, 'cs_r4',6,  'ir_r4',15, 'is_r4',5,  'lim_r4',4,'limm_r4',1, 'mra_r4',1, ...
  'dim_r5',40,'sym_r5','c8','ite_r5',3, 'nref_r5',2, 'cr_r5',15, 'cs_r5',5,  'ir_r5',12, 'is_r5',4,  'lim_r5',3,'limm_r5',1, 'mra_r5',1, ...
  'dim_r6',40,'sym_r6','c8','ite_r6',3, 'nref_r6',2, 'cr_r6',10, 'cs_r6',4,  'ir_r6',10, 'is_r6',3,  'lim_r6',3,'limm_r6',1, 'mra_r6',1);

% --- compute backend: CPU parfor (no compiled GPU exe on this node) ---
dvput(pname,'d', 'destination','matlab_parfor', 'cores',20, 'mwa',8);

% --- validate + unfold (makes it runnable) ---
disp('================ dvcheck ================');
dvcheck(pname);
disp('================ dvunfold ===============');
dvunfold(pname);

% --- print a compact summary of the configured rounds ---
disp('================ SUMMARY ================');
vpr = dynamo_vpr_load(pname);
for r=1:6
  fprintf('round %d: dim=%d nref=%d ite=%d cone_range=%g cone_sampling=%g inplane_range=%g inplane_sampling=%g area_search=%g sym=%s mra=%g\n', ...
    r, vpr.(sprintf('dim_r%d',r)), vpr.(sprintf('nref_r%d',r)), vpr.(sprintf('ite_r%d',r)), ...
    vpr.(sprintf('cone_range_r%d',r)), vpr.(sprintf('cone_sampling_r%d',r)), ...
    vpr.(sprintf('inplane_range_r%d',r)), vpr.(sprintf('inplane_sampling_r%d',r)), ...
    vpr.(sprintf('area_search_r%d',r)), vpr.(sprintf('sym_r%d',r)), vpr.(sprintf('mra_r%d',r)));
end
fprintf('destination=%s\n', vpr.destination);
disp('SETUP_MRA_DONE');
