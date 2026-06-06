function compile_toolbox(target_dir)

% Add sg_toolbox
sg_toolbox_dir = '/home/ejl62/summerResearch/STA/STOPGAP/sg_toolbox/';
matlab_root = '/apps/matlab/r2023b/';

% Compile (drop the graph2d -a arg if that toolbox path no longer exists in r2023b)
target_dir = sg_check_dir_slash(target_dir);
graph2d = [matlab_root,'toolbox/matlab/graph2d/'];
if exist(graph2d,'dir')
    mcc('-R', '-nosplash', '-d', target_dir, '-mv', 'sg_toolbox.m', '-a', sg_toolbox_dir, '-a', graph2d);
else
    mcc('-R', '-nosplash', '-d', target_dir, '-mv', 'sg_toolbox.m', '-a', sg_toolbox_dir);
end
system(['chmod +x ',target_dir,'sg_toolbox']);
