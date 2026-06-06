% Launch the two-stage MRA project (serial matlab backend; no PCT dependency).
set(0,'DefaultFigureVisible','off');
run('/home/jblaser2/Research/dynamo/dynamo_activate.m');
cd('/home/jblaser2/Research/STA/dynamo/dynamo_outputs/ttest128_tutorial');

pname = 'mra_ttest128';
% NOTE: Dynamo's in-MATLAB execution (dpkmulticore.run) always calls parpool/parfor,
% so it REQUIRES the Parallel Computing Toolbox. PCT is licensed on this node but must be
% installed (same as the IPT install). Once PCT is present, this runs as-is.
dvput(pname,'u','destination','matlab_parfor','cores',8,'mwa',4);

fprintf('RUN_START %s\n', datestr(now));
dvrun(pname);
fprintf('DVRUN_DONE %s\n', datestr(now));
