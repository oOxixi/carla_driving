"""Draw only saved detection boxes over original RGB, for a human-readable report."""
import argparse,json,math,pathlib
from PIL import Image,ImageDraw

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--holdout-root',type=pathlib.Path,required=True);p.add_argument('--detections',type=pathlib.Path,required=True);a=p.parse_args();records=json.loads((a.output/'frozen_sensor_decisions.json').read_text());all_d=json.loads(a.detections.read_text())
 for case,name in [('holdout_extra_250_25','TEST'),('holdout_250_30','R4')]:
  e=next(r for r in records if r['case']==case and r['radius_name']==name);im=Image.open(a.holdout_root/case/'camera.png').convert('RGB');w,h=im.size;assert (w,h)==(800,450);draw=ImageDraw.Draw(im);boxes=[]
  def scale(b):return [b[0]*w,b[1]*h,b[2]*w,b[3]*h]
  if e['formal_bbox_xyxy_norm']:
   box=scale(e['formal_bbox_xyxy_norm']);draw.rectangle(box,outline='#10ed79',width=3);boxes.append(box)
  if case=='holdout_250_30':
   neighbor=next(r for r in all_d if r['case']==case and r['threshold']==.2 and r['id']=='C-0001');box=neighbor['bbox_px'];draw.rectangle(box,outline='#eb4fe8',width=3);boxes.append(box)
  box=scale(e['aux_bbox_xyxy_norm']);draw.rectangle(box,outline='#ffdd14',width=3);boxes.append(box)
  x1=min(b[0] for b in boxes);y1=min(b[1] for b in boxes);x2=max(b[2] for b in boxes);y2=max(b[3] for b in boxes);mx=max(50,(x2-x1));my=max(35,(y2-y1));rect=(max(0,math.floor(x1-mx)),max(0,math.floor(y1-my)),min(w,math.ceil(x2+mx)),min(h,math.ceil(y2+my)));im=im.crop(rect);im=im.resize((im.width*4,im.height*4),Image.Resampling.NEAREST);im.save(a.output/('camera_'+case+'.png'));print(case,'crop',rect,'dimensions',im.size)
if __name__=='__main__':main()
