function [o,v,ali] = flcf_subtomo_scoring_function(p,o,s,idx,v,f,score_mode,ali)
%% flcf_subtomo_scoring_function
% A functon for initializing, preparing, and performing the Roseman
% fast local correlation function (FLCF).
%
% WW 06-2019

%% Calculate FLCF
mode = strsplit(p(idx).subtomo_mode,'_');

switch score_mode
    
    % Detect spherically symmetric masks once; precompute their FFTs so the
    % per-angle inner loop can skip sg_rotate_vol and fftn(mask) calls.
    % A sphere is rotation-invariant: rotating 90° gives the same volume
    % (within linear-interpolation error). This runs once per alignment
    % batch, not per particle, so the two test rotations are negligible.
    case 'init'
        test_rot = sg_rotate_vol(o.mask{1}, [90, 0, 0], [], 'linear');
        rel_err = norm(test_rot(:) - o.mask{1}(:)) / (norm(o.mask{1}(:)) + eps);
        o.mask_is_sphere = rel_err < 1e-2;
        if o.mask_is_sphere
            o.fmask_cache = cell(numel(o.mask), 1);
            for ci = 1:numel(o.mask)
                o.fmask_cache{ci} = fftn(o.mask{ci});
            end
        end
        test_rot = sg_rotate_vol(o.ccmask, [90, 0, 0], [], 'linear');
        rel_err = norm(test_rot(:) - o.ccmask(:)) / (norm(o.ccmask(:)) + eps);
        o.ccmask_is_sphere = rel_err < 1e-2;
        return
        
    % Prepare subtomogram for calculation
    case 'prep'
        
        % Fourier transform particle        
        fsubtomo = fftn(v.subtomo);
                
        % Check Fourier cropping
        if o.fcrop
            fsubtomo = fcrop_fftshifted_vol(fsubtomo,o.f_idx);
        end
        
        % Apply filter
        fsubtomo = fsubtomo.*f.pfilt.*o.bpf;
        % Force 0-frequency peak to zero
        fsubtomo(1,1,1) = 0;     


        % Store complex conjugate
        v.conjSubtomo = conj(fsubtomo); 
        
        % Store complex conjugate of square
        v.conjSubtomo2 = conj(fftn(ifftn(fsubtomo).^2));
    
    
    % Apply alignment parameters to reference and score
    case 'score'

        % Check for stochastic search
        if any(strcmp(p(idx).search_mode,{'shc','sga'}))
            stochastic = true;
        else
            stochastic = false;
        end
        
        % Check for simulated annealing
        sim_anneal = false;
        if sg_check_param(p(idx),'temperature')
            if p(idx).temperature > 0
                stochastic = true;
                sim_anneal = true;
            end
        end
        
        % Loop across each entry
        ali_size = size(ali);
        for j = 1:ali_size(2)
            
            % Loop across all search angles
            for i = 1:ali_size(1)
            
                %%%%% Copy volumes %%%%%
                switch mode{2}
                    case 'singleref'
                        class_idx = 1;
                    otherwise
                        class_idx = find(o.classes == ali(i,j).class);    % Parse reference
                end
                ref = o.ref(class_idx).(ali(i,j).halfset);        % Copy reference
                mask = o.mask{class_idx};                       % Copy mask
        
                
        
                %%%%% Prepare Reference %%%%%

                % Rotate the reference
                ref = sg_rotate_vol(ref,[ali(i,j).phi,ali(i,j).psi,ali(i,j).the],[],o.rot_mode);

                % Rotate mask — skip for spherical masks (rotation is a no-op)
                if ~(isfield(o,'mask_is_sphere') && o.mask_is_sphere)
                    mask = sg_rotate_vol(mask,[ali(i,j).phi,ali(i,j).psi,ali(i,j).the],[],o.rot_mode);
                end

                % Apply filters
                ref = real(ifftn(fftn(ref).*f.rfilt.*o.bpf));

                % Inverse transform particle and normalize under mask
                ref = normalize_under_mask(ref,mask);



                %%%%% Score %%%%%

                % Calculate FLCF — pass precomputed mask FFT for spherical masks
                if isfield(o,'mask_is_sphere') && o.mask_is_sphere
                    scoring_map = calculate_flcf(ref,mask,v.conjSubtomo,v.conjSubtomo2,o.fmask_cache{class_idx});
                else
                    scoring_map = calculate_flcf(ref,mask,v.conjSubtomo,v.conjSubtomo2);
                end
                if o.fcrop
                    scoring_map = fourier_uncrop_volume(scoring_map,o.f_idx);
                end



                %%%%% Find Peak %%%%%

                % Rotate CC mask — skip for spherical masks (rotation is a no-op)
                if isfield(o,'ccmask_is_sphere') && o.ccmask_is_sphere
                    rccmask = o.ccmask;
                else
                    rccmask = sg_rotate_vol(o.ccmask,[ali(i,j).phi,ali(i,j).psi,ali(i,j).the],[],o.rot_mode);
                end

                % Find ccc peak
                [pos, score] = find_subpixel_peak(scoring_map, rccmask);
                if o.fcrop
                    shift = pos-o.full_cen;  % Shift from center of box
                else
                    shift = pos-o.cen;  % Shift from center of box
                end
        
                % Store alignment parameters
                ali(i,j).score = score;
                ali(i,j).new_shift = shift;

                % Check stochastic search exit condition
                if stochastic
                    if i > 1
                        
                        % Basic stochastic hill climb
                        if ali(i,j).score > ali(1,j).score                            
                            break
                            
                        % Simulated annealing
                        elseif sim_anneal
                            
                            % Calculate random number
                            rp   = rand(1);
                            
                            % Check against random probability
                            if (p(idx).temperature/100) > rp
                                
                                % Accept downhill move
                                ali_idx = (1:ali_size(1))~=i;                           % Find all other entries
                                score_cell = num2cell(ones(ali_size(1)-1,1).*-2);
                                [ali(ali_idx,j).score] = score_cell{:};             % Set all other scores to -2
                                break
                                
                            end
                                
                            % Continue alignment
                        end
                    end
                end
                
            end     % End angle loop
        end         % End entry loop

        
           
    otherwise
        error([s.cn,'ACHTUNG!!! Invalid mode!!!']);        
                
end
