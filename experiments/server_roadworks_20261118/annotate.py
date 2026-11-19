import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


BOLD = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
REGULAR = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
WHITE = (239, 250, 255, 255)
PALE = (164, 229, 248, 255)
CYAN = (53, 214, 255, 255)
NAVY = (12, 48, 85, 241)


def font(size, bold=True):
    return ImageFont.truetype(BOLD if bold else REGULAR, size, index=2)


def points(values):
    return [tuple(v) for v in values]


def dashed(draw, a, b, fill, dash=11, gap=7, width=3):
    length = math.dist(a, b)
    for i in range(0, int(length), dash+gap):
        end = min(i+dash, length)
        draw.line([(a[0]+(b[0]-a[0])*d/length,
                    a[1]+(b[1]-a[1])*d/length) for d in (i,end)], fill=fill, width=width)


def arrow(draw, path, idx, length, width, fill):
    x,y=path[idx]
    ax,ay=path[max(0,idx-8)]
    norm=math.hypot(x-ax,y-ay)
    ux,uy=(x-ax)/norm,(y-ay)/norm
    vx,vy=-uy,ux
    bx,by=x-ux*length,y-uy*length
    draw.polygon([(x,y),(bx+vx*width/2,by+vy*width/2),
                  (bx+ux*length*0.25,by+uy*length*0.25),
                  (bx-vx*width/2,by-vy*width/2)],fill=fill)


def route_layer(layer, path):
    for blur, alpha, padding in [(11,128,22),(3,200,8),(0,255,0)]:
        coat=Image.new('RGBA',layer.size)
        draw=ImageDraw.Draw(coat)
        for i,(a,b) in enumerate(zip(path,path[1:])):
            t=i/(len(path)-1)
            thickness=int(25-15*t)+padding
            draw.line((a,b),fill=(13,170+int(52*t),255,alpha),width=thickness)
            r=thickness/2
            draw.ellipse((a[0]-r,a[1]-r,a[0]+r,a[1]+r),fill=(13,170+int(52*t),255,alpha))
        if blur == 0:
            draw.line(path,fill=(158,240,255,220),width=4,joint='curve')
            for i,size in [(28,29),(74,21),(111,15)]:
                arrow(draw,path,i,size,size+3,(188,248,255,244))
        arrow(draw,path,-1+len(path),25+padding,31+padding,(95,229,255,alpha))
        layer.alpha_composite(coat.filter(ImageFilter.GaussianBlur(blur)) if blur else coat)


def callout(draw, text, x, y, target=None, step=None, size=33):
    face=font(size)
    h=62
    pad_left=70 if step else 24
    w=round(draw.textlength(text,font=face))+pad_left+25
    if target:
        tx,ty=target
        px=max(x+24,min(x+w-24,tx))
        py=y+h if ty>y+h/2 else y
        if y<=ty<=y+h:
            px=x if tx<x else x+w
            py=y+h/2
        draw.line(((px+2,py+3),(tx+2,ty+3)),fill=(6,25,41,180),width=7)
        draw.line(((px,py),(tx,ty)),fill=(232,248,255,252),width=3)
        draw.ellipse((tx-6,ty-6,tx+6,ty+6),fill=WHITE)
    draw.rounded_rectangle((x+3,y+5,x+w+3,y+h+5),radius=28,fill=(4,20,38,131))
    draw.rounded_rectangle((x,y,x+w,y+h),radius=28,fill=NAVY,outline=(210,243,252,243),width=2)
    if step:
        cx,cy=x+37,y+h/2
        draw.ellipse((cx-17,cy-17,cx+17,cy+17),outline=PALE,width=3)
        draw.text((cx,cy-1),step,font=font(22),fill=WHITE,anchor='mm')
    draw.text((x+pad_left,y+h/2-2),text,font=face,fill=WHITE,anchor='lm')


def title(draw):
    x,y=37,37
    draw.rounded_rectangle((102,47,1104,134),radius=42,fill=(236,248,255,246),
                           outline=(161,219,248,240),width=2)
    draw.ellipse((x,y,x+107,y+107), fill=(10,57,104,251), outline=(157,230,255,255),width=4)
    cx,cy=x+53,y+50
    draw.rounded_rectangle((cx-10,cy-23,cx+10,cy+11),radius=10,fill=WHITE)
    draw.arc((cx-18,cy-13,cx+18,cy+22),0,180,fill=WHITE,width=4)
    draw.line((cx,cy+21,cx,cy+31),fill=WHITE,width=4)
    draw.line((cx-10,cy+31,cx+10,cy+31),fill=WHITE,width=4)
    draw.text((167,88),'\u4ece\u5de6\u4fa7\u5b89\u5168\u7ed5\u8fc7\u65bd\u5de5\u533a\u57df\u548c\u6162\u901f\u81ea\u884c\u8f66',font=font(52),fill=(11,40,76,255),anchor='lm')


def footer(draw,width,height):
    start=41
    end=width-41
    bottom=height-29
    top=bottom-102
    draw.rounded_rectangle((start,top,end,bottom),radius=23,fill=(11,35,57,226),
                           outline=(196,238,253,195),width=2)
    columns=[('\u573a\u666f\u76ee\u6807','\u7ed5\u884c\u5e76\u8d85\u8d8a\u6162\u901f\u81ea\u884c\u8f66'),
             ('\u5f53\u524d\u7ea6\u675f','\u65bd\u5de5\u5360\u9053 \u00b7 \u524d\u65b9\u6162\u884c'),
             ('\u5b89\u5168\u524d\u63d0','\u540c\u5411\u5de6\u8f66\u9053\u53ef\u7528'),
             ('\u6267\u884c\u8981\u6c42','\u901a\u8fc7\u540e\u56de\u5230\u539f\u8f66\u9053')]
    for i,(heading,body) in enumerate(columns):
        edge=start+i*(end-start)/4
        x=edge+29
        if i:
            draw.line((edge,top+20,edge,bottom-19),fill=(167,213,232,114),width=2)
        draw.text((x,top+29),heading,font=font(28),fill=PALE,anchor='lm')
        draw.text((x,top+69),body,font=font(27,False),fill=WHITE,anchor='lm')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('stem')
    parser.add_argument('--output',default='roadworks_annotated.png')
    args=parser.parse_args()
    img=Image.open(f'{args.stem}_rgb.png').convert('RGBA')
    state=json.loads(Path(f'{args.stem}_capture.json').read_text())
    work=points(state['work_polygon'])
    path=points(state['path'])
    bike=tuple(state['bike'])
    warning=tuple(state['warning'])
    ego=tuple(state['ego'])
    left=tuple(state['left'])

    work_layer=Image.new('RGBA',img.size)
    draw=ImageDraw.Draw(work_layer)
    draw.polygon(work,fill=(255,102,55,61))
    for a,b in zip(work,work[1:]+work[:1]):
        draw.line((a,b),fill=(255,99,48,135),width=5)
        dashed(draw,a,b,(255,222,172,245),width=3)
    img.alpha_composite(work_layer)

    route=Image.new('RGBA',img.size)
    route_layer(route,path[15:])
    img.alpha_composite(route)
    layer=Image.new('RGBA',img.size)
    draw=ImageDraw.Draw(layer)
    title(draw)
    footer(draw,img.width,img.height)

    _,second,third=state['steps']
    callout(draw,'\u51cf\u901f',int(ego[0]+235),int(ego[1]-15),step='1')
    callout(draw,'\u5de6\u4fa7\u7ed5\u884c',int(second[0]-334),int(second[1]-42),step='2')
    callout(draw,'\u8fd4\u56de\u539f\u8f66\u9053',int(third[0]-288),max(181,int(third[1]-97)),step='3')
    callout(draw,'\u53ef\u501f\u7528\u5de6\u4fa7\u8f66\u9053',max(60,int(left[0]-384)),int(left[1]+126),left,size=31)
    callout(draw,'\u6162\u901f\u81ea\u884c\u8f66',int(bike[0]+88),int(bike[1]-117),bike,size=31)
    callout(draw,'\u65bd\u5de5\u533a\u57df',max(int(warning[0]+240), int(bike[0]+290)),
            int(warning[1]-57),warning,size=31)
    img.alpha_composite(layer)
    img.convert('RGB').save(args.output,compress_level=5)


if __name__=='__main__':
    main()
