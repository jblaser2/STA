function crash_log = check_crashes(p,idx,crash_log)
%% check_crashes
% A functionf or checking if any STOPGAP crash files have been written. As
% each new file is written, it is displayed on the watcher terminal.
%
% Any single core crash is fatal: that core's particles can never finish, so
% the per-core completion flags will never all appear and the watcher would
% otherwise poll forever until the SLURM wall-time silently kills the job.
% We therefore abort on the FIRST crash so the error reaches the job log
% (stdout/stderr -> logs/classify_*.{log,err}). This adds no per-poll cost.
%
% WW 06-2023

%% Check for crashes!!1!

% Cycle through crash long
for i = 1:numel(crash_log)
    
    % Check for new crash
    if ~crash_log(i)
        
        % Check for crash file
        crash_file_name = [p(idx).rootdir,'/crash_',num2str(i)];
        if exist(crash_file_name,'file')
        
            % Report crash file
            fprintf('%s\n',[]);
            system(['cat ',crash_file_name]);

            % Log crash
            crash_log(i) = true;
            
        end
    end
end

% Abort on ANY crash (see header). A single dead core means the current task
% can never complete, so continuing would hang the watcher silently.
if any(crash_log)
    crashed = find(crash_log);
    error('ACHTUNG!!!1! STOPGAP core(s) [%s] crashed; aborting run to avoid a silent hang. See crash_* file(s) in %s', ...
        num2str(crashed(:)'), p(idx).rootdir);
end


        



