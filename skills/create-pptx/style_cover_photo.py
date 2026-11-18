#!/usr/bin/env python3
"""Apply an editable artistic crop/frame to an existing one-slide PPTX cover.

Uses standard-library OOXML edits and keeps the source image, text, and logos
editable. It preserves the source slide's namespace and extension markup.
"""
import argparse
import copy
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET

P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def picture_fragment(data: bytes, picture_id: str | None):
    matches=list(re.finditer(rb"<p:pic\b.*?</p:pic>",data,re.S))
    if picture_id:
        found=next((m for m in matches if re.search(rb'<p:cNvPr\b[^>]*\bid="'+picture_id.encode()+rb'"',m.group())),None)
    else:
        root=ET.fromstring(data); sizes={}
        for pic in root.findall(f".//{{{P}}}pic"):
            nv=pic.find(f"{{{P}}}nvPicPr/{{{P}}}cNvPr"); ext=pic.find(f"{{{P}}}spPr/{{{A}}}xfrm/{{{A}}}ext")
            if nv is not None and ext is not None: sizes[nv.get('id')]=int(ext.get('cx',0))*int(ext.get('cy',0))
        best=max(sizes,key=sizes.get) if sizes else None
        found=next((m for m in matches if re.search(rb'<p:cNvPr\b[^>]*\bid="'+best.encode()+rb'"',m.group())),None) if best else None
    if not found: raise ValueError("Cover picture not found")
    return found


def set_xfrm(fragment: bytes, x: int, y: int, cx: int, cy: int) -> bytes:
    m=re.search(rb"<a:xfrm\b[^>]*>.*?</a:xfrm>",fragment,re.S)
    if not m: raise ValueError("Cover picture has no transform")
    xf=m.group()
    for tag,attrs in ((b"off",{b"x":x,b"y":y}),(b"ext",{b"cx":cx,b"cy":cy})):
        o=re.search(rb"<a:"+tag+rb"\b[^>]*/>",xf)
        if not o: raise ValueError("Incomplete picture transform")
        raw=o.group()
        for key,val in attrs.items():
            raw,n=re.subn(rb"\b"+key+rb'="[^"]*"',key+b'="'+str(val).encode()+b'"',raw,count=1)
            if not n: raw=raw[:-2]+b" "+key+b'="'+str(val).encode()+b'"/>'
        xf=xf[:o.start()]+raw+xf[o.end():]
    return fragment[:m.start()]+xf+fragment[m.end():]


def backing_shape(shape_id: int, name: str, x: int, y: int, cx: int, cy: int, geom: str, color: str, adj: int | None) -> bytes:
    av=f'<a:avLst><a:gd name="adj" fmla="val {adj}"/></a:avLst>' if adj else '<a:avLst/>'
    xml=(f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="Photo treatment backing: {name}"/>'
         f'<p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{x}" y="{y}"/>'
         f'<a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="{geom}">{av}</a:prstGeom>'
         f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill><a:ln><a:noFill/></a:ln></p:spPr></p:sp>').encode()
    return xml


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',required=True,type=Path,help='One-slide cover PPTX')
    ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--style',required=True,choices=['circle-halo','angled-layer','soft-frame'])
    ap.add_argument('--photo-id',help='Cover image shape ID; defaults to largest picture')
    ap.add_argument('--source-ratio',default='16:9',help='Original image aspect ratio, such as 16:9')
    args=ap.parse_args()
    if not args.input.is_file(): ap.error('input cover deck does not exist')
    try: swr,shr=(float(v) for v in args.source_ratio.split(':',1)); source_aspect=swr/shr
    except Exception: ap.error('source-ratio must look like 16:9')
    args.output.parent.mkdir(parents=True,exist_ok=True)

    with ZipFile(args.input) as zin:
        entries=[(info,zin.read(info.filename)) for info in zin.infolist()]
        pres=ET.fromstring(dict((i.filename,d) for i,d in entries)['ppt/presentation.xml'])
        size=pres.find(f"{{{P}}}sldSz")
        if size is None or len(pres.find(f"{{{P}}}sldIdLst"))!=1: raise ValueError('Input must be a one-slide presentation')
        sw,sh=int(size.get('cx')),int(size.get('cy'))
        slide_path='ppt/slides/slide1.xml'; data=dict((i.filename,d) for i,d in entries)[slide_path]

        # Remove a treatment backing from a previous run before applying the new one.
        for m in reversed(list(re.finditer(rb'<p:sp\b.*?</p:sp>',data,re.S))):
            if b'Photo treatment backing:' in m.group(): data=data[:m.start()]+data[m.end():]
        photo_m=picture_fragment(data,args.photo_id); photo=photo_m.group()
        if args.style=='circle-halo':
            d=round(sh*.73); x=sw-round(d*1.05); y=(sh-d)//2; cx=cy=d; geom='ellipse'; color='E4EFED'; pad=round(d*.05); adj=None; line=None
        elif args.style=='angled-layer':
            x=round(sw*.525); y=round(sh*.11); cx=round(sw*.445); cy=round(sh*.78); geom='parallelogram'; color='D5E9E8'; pad=round(sw*.025); adj=None; line=None
        else:
            x=round(sw*.55); y=round(sh*.10); cx=round(sw*.42); cy=round(sh*.80); geom='roundRect'; color='F1F6F5'; pad=round(sw*.013); adj=26000; line='D3E5E4'
        photo=set_xfrm(photo,x,y,cx,cy)
        aspect=(cx/cy)
        if aspect<source_aspect:
            visible=aspect/source_aspect; crop=round((1-visible)*100000)
            l,r=(crop,1000)
            cropxml=f'<a:srcRect l="{l}" r="{r}"/>'.encode()
        else:
            visible=source_aspect/aspect; crop=round((1-visible)*100000)
            cropxml=f'<a:srcRect t="{crop//2}" b="{crop-crop//2}"/>'.encode()
        photo=re.sub(rb'<a:srcRect\b[^>]*/>',cropxml,photo,count=1)
        photo=re.sub(rb'<a:picLocks\b[^>]*/>',b'',photo)
        geometry=f'<a:prstGeom prst="{geom}"><a:avLst>'.encode()
        if adj: geometry+=f'<a:gd name="adj" fmla="val {adj}"/>'.encode()
        geometry+=b'</a:avLst></a:prstGeom>'
        photo=re.sub(rb'<a:prstGeom\b.*?</a:prstGeom>',geometry,photo,count=1,flags=re.S)
        if line:
            photo=re.sub(rb'<a:ln><a:noFill/></a:ln>',f'<a:ln w="25400"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>'.encode(),photo,count=1)
        root=ET.fromstring(data); ids=[int(n.get('id')) for n in root.findall('.//{'+P+'}cNvPr') if n.get('id','').isdigit()]
        back_id=max(ids,default=0)+1
        if args.style=='circle-halo': bx=x-pad; by=y-pad; bcx=cx+2*pad; bcy=cy+2*pad; backgeom='ellipse'; backadj=None
        elif args.style=='angled-layer': bx=x+pad; by=y+round(pad*.6); bcx=cx; bcy=cy; backgeom='parallelogram'; backadj=None
        else: bx=x-pad; by=y-pad; bcx=cx+2*pad; bcy=cy+2*pad; backgeom='roundRect'; backadj=adj
        backing=backing_shape(back_id,args.style,bx,by,bcx,bcy,backgeom,color,backadj)
        data=data[:photo_m.start()]+backing+photo+data[photo_m.end():]
        ET.fromstring(data)
        with ZipFile(args.output,'w',ZIP_DEFLATED) as zout:
            for info,original in entries:
                zout.writestr(copy.copy(info),data if info.filename==slide_path else original)
    print(args.output)


if __name__=='__main__': main()
