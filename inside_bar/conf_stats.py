import sys, pandas as pd, numpy as np
T=pd.read_csv(sys.argv[1]); T=T[~T.open]
T['yr']=pd.to_datetime(T.t_entry).dt.year; T['per']=np.where(T.yr<=2023,'A','B')
def st(g):
    w=g.net_R; pf=w[w>0].sum()/max(1e-9,-w[w<0].sum())
    eq=w.cumsum(); dd=(eq.cummax()-eq).max()
    return pd.Series(dict(n=len(g),win=(g.res=='tp').mean()*100,rr=g.rr.median(),exp=w.mean(),pf=pf,
       expA=g[g.per=='A'].net_R.mean(),expB=g[g.per=='B'].net_R.mean(),yrs=f"{(g.groupby('yr').net_R.sum()>0).sum()}/{g.yr.nunique()}",
       eth=g[g.sym=='ETHUSDT'].net_R.mean(), neth=(g.sym=='ETHUSDT').sum(), lowside=g[g.side=='low'].net_R.mean(), mb=g[g.mb_entry].net_R.mean(), nomb=g[~g.mb_entry].net_R.mean(), nmb=g.mb_entry.sum(),
       syms_pos=(g.groupby('sym').net_R.mean()>0).sum()))
r=T.groupby(['kind','conf','tp']).apply(st).sort_values('exp',ascending=False)
r.to_pickle(sys.argv[2])
with pd.option_context('display.width',300,'display.max_rows',200,'display.max_columns',30,'display.float_format','{:.2f}'.format):
    print(r.reset_index().drop(columns='kind').to_string())
