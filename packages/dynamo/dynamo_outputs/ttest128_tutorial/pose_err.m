run('/home/jblaser2/Research/dynamo/dynamo_activate.m');
cd('/home/jblaser2/Research/STA/dynamo/dynamo_outputs/ttest128_tutorial');
Ti=dread('ttest128/initial.tbl'); Tr=dread('ttest128/real.tbl');
ds = Tr(:,4:6)-Ti(:,4:6); shiftErr = sqrt(sum(ds.^2,2));
ang=zeros(size(Tr,1),1);
for k=1:size(Tr,1)
  Rr=dynamo_euler2matrix(Tr(k,7:9)); Ri=dynamo_euler2matrix(Ti(k,7:9));
  Rrel=Rr*Ri'; c=(trace(Rrel)-1)/2; c=max(min(c,1),-1); ang(k)=acosd(c);
end
fprintf('SHIFTerr_vox mean %.2f median %.2f max %.2f\n',mean(shiftErr),median(shiftErr),max(shiftErr));
fprintf('ANGLEerr_deg mean %.1f median %.1f max %.1f\n',mean(ang),median(ang),max(ang));
fprintf('init_angles_allzero %d init_shifts_allzero %d\n', all(all(Ti(:,7:9)==0)), all(all(Ti(:,4:6)==0)));
