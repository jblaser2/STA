function inspect_global_avg(rootdir, px)
%% inspect_global_avg
% Render the global average (ref_1.mrc) central slices and a radial density
% profile (averaged over Z) to choose a cylindrical mask radius that encloses
% the real pilus density without the surrounding noise shell.
if nargin < 2 || px <= 0, px = 13.33; end

v = single(sg_mrcread(fullfile(rootdir,'ref','ref_1.mrc')));
b = size(v,1);
c = floor(b/2)+1;

% Radial profile in XY, averaged over all Z
[X,Y] = meshgrid(1:b,1:b);
R = sqrt((X-c).^2 + (Y-c).^2);
xy_mean = mean(v,3);
redges = 0:1:ceil(b/2);
prof = zeros(numel(redges)-1,1);
for i = 1:numel(redges)-1
    m = R>=redges(i) & R<redges(i+1);
    prof(i) = mean(xy_mean(m));
end
rcen = (redges(1:end-1)+redges(2:end))/2;

f = figure('Visible','off','Position',[0 0 1200 400]);
subplot(1,3,1); imagesc(squeeze(v(:,:,c))); axis image off; colormap gray; title('XY (z=center)');
subplot(1,3,2); imagesc(squeeze(v(:,c,:))); axis image off; colormap gray; title('XZ (y=center)');
subplot(1,3,3);
plot(rcen, prof, '-o','LineWidth',1.2); grid on; hold on;
xlabel('radius (px)'); ylabel('mean density'); title('Radial profile (XY, Z-avg)');
yyaxis right; plot(rcen*px, prof, 'LineStyle','none'); ylabel('');
ax = gca; ax.YAxis(2).Visible='off';
% annotate radius in Angstrom on a few ticks
xt = get(gca,'XTick');
set(gca,'XTickLabel',arrayfun(@(r) sprintf('%d\n%.0f\\AA',r,r*px), xt,'uni',0));

out = fullfile(rootdir,'meta','global_avg_profile.png');
exportgraphics(f, out, 'Resolution',150); close(f);
fprintf('[inspect] box=%d px, center=%d, px=%.2f A\n', b, c, px);
fprintf('[inspect] radial profile (r_px : r_A : mean_density):\n');
for i = 1:numel(prof)
    fprintf('   %2d : %5.0f : % .4f\n', round(rcen(i)), rcen(i)*px, prof(i));
end
fprintf('[inspect] wrote %s\n', out);
end
