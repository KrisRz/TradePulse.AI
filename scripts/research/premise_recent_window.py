"""Premise check 2026-11-14: do the last 7 days of BTC (return, volatility,
volume, range) say anything about the next 7 days? And the #12 premise: does
volatility cluster, and is a high-vol LONG state followed by deeper drops?

Read-only, data < 2026-07-16, non-overlapping samples. Results: plan.md,
"STAN BOTA 2026-11-14". Usage: PYTHONPATH=. python scripts/research/premise_recent_window.py
"""
import pandas as pd, numpy as np
from scipy.stats import spearmanr
df=pd.read_csv("data/ml/historical/BTCUSDT_1d.csv",parse_dates=["timestamp"],index_col="timestamp")
df=df[df.index<"2026-07-16"]; c=df.close; r=c.pct_change()
long=(c.ewm(span=20,adjust=False).mean()>c.ewm(span=100,adjust=False).mean())
X=pd.DataFrame({"ret7":c.pct_change(7),"vol7":r.rolling(7).std(),"volchg7":df.volume.rolling(7).mean()/df.volume.rolling(30).mean()-1,
 "range7":(df.high.rolling(7).max()/df.low.rolling(7).min()-1),"vol20":r.rolling(20).std()})
X["fwd7"]=c.shift(-7)/c-1; X["fwdvol20"]=r.rolling(20).std().shift(-20)
X["fwddd20"]=(c[::-1].rolling(20).min()[::-1].shift(-1)/c-1)
X["long"]=long; X=X.iloc[120:].dropna()
S=X.iloc[::7]  # non-overlapping weekly samples
print("non-overlapping weekly samples:",len(S)," of which EMA-long:",int(S.long.sum()))
for name,sub in [("all",S),("2017-2021",S[:"2021"]),("2022-2026",S["2022":]),("EMA long only",S[S.long]),("EMA long 2022+",S[S.long]["2022":])]:
    out=[]
    for f in ["ret7","vol7","volchg7","range7"]:
        rho,p=spearmanr(sub[f],sub.fwd7); out.append(f"{f} rho={rho:+.3f} p={p:.2f}")
    print(f"{name:16s} n={len(sub):3d} | "+" | ".join(out))
print("\n-- when long: next-7d return by tercile of past-7d return (weekly samples)")
L=S[S.long].copy(); L["q"]=pd.qcut(L.ret7,3,labels=["worst7d","mid","best7d"])
print(L.groupby("q",observed=True).fwd7.agg(["count","mean","median"]).round(4))
print("\n-- #12 premise: vol clustering (20d samples)")
T=X.iloc[::20]; print("rho(vol20, next vol20) =",round(spearmanr(T.vol20,T.fwdvol20)[0],3),"n",len(T))
TL=T[T.long].copy(); TL["q"]=pd.qcut(TL.vol20,3,labels=["lowvol","mid","highvol"])
print(TL.groupby("q",observed=True).agg(n=("fwddd20","count"),worst_fwd_dd20=("fwddd20","min"),mean_fwd_dd20=("fwddd20","mean")).round(3))
TL["f20"]=(c.shift(-20)/c-1).reindex(TL.index); print(TL.groupby("q",observed=True).f20.agg(["mean","median"]).round(3))
