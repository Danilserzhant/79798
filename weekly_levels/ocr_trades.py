"""Распознаёт заголовки и подписи уровней на скриншотах сделок (нужен tesseract),
сохраняет trades.pkl: направление, время, вход, риск, достигнутая цель (R, SL=-1).
python ocr_trades.py <dir>   (OMP_THREAD_LIMIT=1 ускоряет tesseract)"""
import sys, subprocess, re, json, os
from PIL import Image, ImageOps
from concurrent.futures import ThreadPoolExecutor
R=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
D=sys.argv[1] if len(sys.argv)>1 else '.'
def ocr(im, psm):
    return subprocess.run(['tesseract','stdin','stdout','--psm',str(psm)],input=im,capture_output=True).stdout.decode()
def tob(img):
    import io; b=io.BytesIO(); img.save(b,'PNG'); return b.getvalue()
def one(fn):
    im=Image.open(os.path.join(R,fn)).convert('L')
    t=im.crop((75,0,im.width-200,26)); t=t.resize((t.width*3,t.height*3),Image.LANCZOS)
    r=im.crop((1355,20,im.width,665)); r=r.resize((r.width*3,r.height*3),Image.LANCZOS)
    return fn, ocr(tob(t),7).strip(), ocr(tob(r),6 if False else 11)
fns=sorted(f for f in os.listdir(R) if f.endswith('.png'))
with ThreadPoolExecutor(4) as ex: res=list(ex.map(one,fns))
json.dump(res,open(os.path.join(D,'ocr.json'),'w'),ensure_ascii=False)

# ---------- разбор ----------
import pandas as pd
r=res
rows=[];bad=[]
num=r'([\d,]{3,}\.\d{2})'
for fn,t,lab in r:
    lab=' '.join(lab.split()).replace(',','')
    idx,dr,d,tm=fn[:-4].split('_')
    tail=t.split('FVG')[-1]
    m=re.search(r'TP(\d)\s*\((\d)R\)',tail); res=None
    if m: res=int(m.group(2))
    elif re.search(r'\bSL\b',tail): res=-1
    else:
        m=re.search(r'TP(\d)',tail); res={'1':1,'2':2,'3':4,'4':5}.get(m.group(1)) if m else None
    lv={}
    for k,pat in [('sl',r'SL\s*'+num),('e',r'entry\s*'+num),('tp1',r'1R\s*'+num),('tp2',r'2R\s*'+num),('tp3',r'4R\s*'+num),('tp4',r'5R\s*'+num)]:
        mm=re.search(pat,lab.replace(',',''))
        if mm: lv[k]=float(mm.group(1))
    # derive entry/risk from TP ladder (entry+kR)
    R=None;E=None
    pts=[(k2,lv[k]) for k,k2 in [('tp1',1),('tp2',2),('tp3',4),('tp4',5)] if k in lv]
    if 'sl' in lv: pts.append((-1,lv['sl']))
    if len(pts)>=2:
        import numpy as np
        x=np.array([p[0] for p in pts]);y=np.array([p[1] for p in pts])
        b,a=np.polyfit(x,y,1); E=a; R=abs(b)
        if len(pts)>=3 and np.max(np.abs(a+b*x-y))>0.02*R: # outlier -> use median pairwise
            E=lv.get('e',E)
    if 'e' in lv and E and abs(lv['e']-E)<0.3*R: E=lv['e']
    sweep=re.search(r'sweep\s*([\d.]+)h',t); depth=re.search(r'depth\s*([\d.]+)%',t); risk=re.search(r'risk\s*([\d.]+)%',t)
    row=dict(n=int(idx),dir=dr,time=pd.Timestamp(d+' '+tm[:2]+':'+tm[2:]),res=res,entry=E,risk=R,
             risk_pct=float(risk.group(1)) if risk else None,sweep_h=float(sweep.group(1)) if sweep else None,
             depth=float(depth.group(1)) if depth else None, tf15='15min' in t)
    if res is None or E is None: bad.append((fn,t,lab[:150]))
    rows.append(row)
df=pd.DataFrame(rows)
print('bad',len(bad)); [print(*b,sep=' | ') for b in bad[:20]]
# графики, где OCR не прочитал подписи — значения сняты вручную
fix={575:(102307.00,382.32,4),716:(114311.90,279.94,4),717:(114157.40,564.22,1),772:(110981.70,289.91,5),863:(76000.00,384.83,-1)}
for n,(e,rk,rs) in fix.items():
    i=df.index[df.n==n][0]; df.loc[i,['entry','risk','res']]=[e,rk,rs]
df.to_pickle(os.path.join(D,'trades.pkl')); print(df.isna().sum().sum(), df.res.value_counts().to_dict())
