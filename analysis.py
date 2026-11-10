import pandas as pd, numpy as np, re, math, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

H="/tmp/data/Statutory_Homelessness_Detailed_Local_Authority_Data_202603.ods"
R="/tmp/data/priceindexofprivaterentsukmonthlypricestatistics.xlsx"

def num(s):
    s=str(s).strip()
    if s in ("nan","None","[z]","[x]","[c]","[w]","[u]",":",""): return np.nan
    s=re.sub(r"[^0-9.\-]","",s)
    try: return float(s)
    except: return np.nan

def load_ods(sheet):
    df=pd.read_excel(H,sheet_name=sheet,engine="odf",header=None)
    hdr=next(i for i in range(12) if str(df.iloc[i,0]).strip()=="Organisation Identification Code")
    out=df.iloc[hdr+1:].copy(); out.columns=[str(c) for c in df.iloc[hdr]]
    return out.reset_index(drop=True)

# ---------- homelessness ----------
ta1=load_ods("TA1"); ta9=load_ods("TA9_TATYPE")
cc="Organisation Identification Code"; cn="Area Name"
col_tot=[c for c in ta1.columns if c.startswith("Households in TA Total[")][0]
col_rate=[c for c in ta1.columns if c.startswith("Households in TA Total(per thousand)")][0]
col_broad=[c for c in ta1.columns if c.startswith("Households owed a TA duty in another LATotal")][0]
col_placed=[c for c in ta9.columns if c.startswith("Placed in temporary accommodation in another LATotal")][0]

a=ta1[[cc,cn,col_tot,col_rate,col_broad]].copy()
a.columns=["code","name","ta_total","ta_per_1000","out_broad"]
b=ta9[[cc,col_placed]].copy(); b.columns=["code","placed_other_la"]
b=b.drop_duplicates("code")
h=a.drop_duplicates("code").merge(b,on="code",how="left")
for c in ["ta_total","ta_per_1000","out_broad","placed_other_la"]: h[c]=h[c].map(num)
h=h[h.code.astype(str).str.match(r"E09\d{6}$")].copy()

# ---------- rents ----------
r=pd.read_excel(R,sheet_name="Table 1",header=2, engine="openpyxl",
                usecols=["Time period","Area code","Area name","Rental price one bed"])
r["Time period"]=pd.to_datetime(r["Time period"],errors="coerce")
r["rent1b"]=r["Rental price one bed"].map(num)
r=r[r["Area code"].astype(str).str.match(r"E09\d{6}$")]
mar=r[r["Time period"]==pd.Timestamp("2026-03-01")][["Area code","Area name","rent1b"]]
mar.columns=["code","rent_name","rent_1bed_mar26"]
q1=r[r["Time period"].isin([pd.Timestamp("2026-01-01"),pd.Timestamp("2026-02-01"),pd.Timestamp("2026-03-01")])]
q1avg=q1.groupby("Area code")["rent1b"].mean().rename("rent_1bed_q1avg").reset_index().rename(columns={"Area code":"code"})

# ---------- join ----------
d=h.merge(mar,on="code",how="inner").merge(q1avg,on="code",how="left")
d["out_share"]=d["placed_other_la"]/d["ta_total"]
d["out_share_broad"]=d["out_broad"]/d["ta_total"]
d=d.dropna(subset=["rent_1bed_mar26","out_share"]).reset_index(drop=True)
print("ROWS AFTER JOIN:",len(d))
print("City of London present?", (d.name.str.contains("City of London")).any())
print("name mismatches:", [(x,y) for x,y in zip(d.name,d.rent_name) if x.replace("&","and")!=y.replace("&","and")][:40])

# ---------- stats ----------
def betacf(a,b,x):
    MAXIT,EPS,FPMIN=200,3e-12,1e-300
    qab,qap,qam=a+b,a+1.0,a-1.0
    c=1.0; dd=1.0-qab*x/qap
    if abs(dd)<FPMIN: dd=FPMIN
    dd=1.0/dd; hh=dd
    for m in range(1,MAXIT+1):
        m2=2*m
        aa=m*(b-m)*x/((qam+m2)*(a+m2))
        dd=1.0+aa*dd; c=1.0+aa/c
        if abs(dd)<FPMIN: dd=FPMIN
        if abs(c)<FPMIN: c=FPMIN
        dd=1.0/dd; hh*=dd*c
        aa=-(a+m)*(qab+m)*x/((a+m2)*(qap+m2))
        dd=1.0+aa*dd; c=1.0+aa/c
        if abs(dd)<FPMIN: dd=FPMIN
        if abs(c)<FPMIN: c=FPMIN
        dd=1.0/dd; de=dd*c; hh*=de
        if abs(de-1.0)<EPS: break
    return hh

def betai(a,b,x):
    if x<=0: return 0.0
    if x>=1: return 1.0
    bt=math.exp(math.lgamma(a+b)-math.lgamma(a)-math.lgamma(b)+a*math.log(x)+b*math.log(1-x))
    if x<(a+1)/(a+b+2): return bt*betacf(a,b,x)/a
    return 1.0-bt*betacf(b,a,1-x)/b

def spearman(x,y):
    x=pd.Series(x).rank(); y=pd.Series(y).rank()
    n=len(x); rho=np.corrcoef(x,y)[0,1]
    if n<3 or abs(rho)>=1: return rho,float("nan")
    t=rho*math.sqrt((n-2)/(1-rho**2)); df=n-2
    p=betai(df/2,0.5,df/(df+t*t))
    return rho,p

rho,p=spearman(d.rent_1bed_mar26,d.out_share)
rho_q,p_q=spearman(d.rent_1bed_q1avg,d.out_share)
rho_d,p_d=spearman(d.ta_per_1000,d.out_share)
rho_b,p_b=spearman(d.rent_1bed_mar26,d.out_share_broad)

top3=d.nlargest(3,"rent_1bed_mar26")
d_ex=d.drop(top3.index)
rho_x,p_x=spearman(d_ex.rent_1bed_mar26,d_ex.out_share)

print(f"\nSPEARMAN rent(Mar26 1-bed) vs out-of-borough share : rho={rho:.3f}  p={p:.4f}  n={len(d)}")
print(f"SPEARMAN rent(Q1-2026 avg)  vs share               : rho={rho_q:.3f}  p={p_q:.4f}")
print(f"SPEARMAN TA per 1000 hh (demand) vs share          : rho={rho_d:.3f}  p={p_d:.4f}")
print(f"SPEARMAN rent vs BROAD out-of-area share           : rho={rho_b:.3f}  p={p_b:.4f}")
print(f"Drop 3 priciest ({', '.join(top3.name)}): rho={rho_x:.3f} p={p_x:.4f} n={len(d_ex)}")

d.sort_values("rent_1bed_mar26",ascending=False).to_csv("/tmp/work/joined_32_boroughs.csv",index=False)
print("\nTOP 6 BY RENT");print(d.nlargest(6,"rent_1bed_mar26")[["name","rent_1bed_mar26","ta_total","placed_other_la","out_share"]].to_string(index=False))
print("\nBOTTOM 6 BY RENT");print(d.nsmallest(6,"rent_1bed_mar26")[["name","rent_1bed_mar26","ta_total","placed_other_la","out_share"]].to_string(index=False))
print("\nTOP 6 BY OUT-OF-BOROUGH SHARE");print(d.nlargest(6,"out_share")[["name","rent_1bed_mar26","ta_total","placed_other_la","out_share"]].to_string(index=False))

for nm in ["Kensington","Havering","Newham"]:
    row=d[d.name.str.contains(nm)]
    print(f"\nCHECK {nm}:");print(row[["code","name","rent_name","rent_1bed_mar26","ta_total","placed_other_la","out_share"]].to_string(index=False))

json.dump({"rho":rho,"p":p,"n":int(len(d)),"rho_q":rho_q,"rho_demand":rho_d,
           "rho_drop3":rho_x,"p_drop3":p_x,"rho_broad":rho_b},open("/tmp/work/stats.json","w"),indent=1)

# ---------- chart ----------
fig,ax=plt.subplots(figsize=(11,7.5))
ax.scatter(d.rent_1bed_mar26,d.out_share*100,s=46,color="#1f4e79",zorder=3)
for _,row in d.iterrows():
    ax.annotate(row["name"],(row.rent_1bed_mar26,row.out_share*100),
                fontsize=7.3,xytext=(4,3),textcoords="offset points",color="#222222")
ax.set_xlabel("Average monthly rent, one bedroom, March 2026 (£)",fontsize=10)
ax.set_ylabel("Share of temporary accommodation households placed outside the borough (%)",fontsize=10)
ax.set_title("London boroughs: private rent level and out-of-borough placement, March 2026",fontsize=12.5,pad=12)
ax.text(0.985,0.045,f"Spearman rho = {rho:.3f}   p = {p:.3f}   n = {len(d)}",
        transform=ax.transAxes,fontsize=10,va="bottom",ha="right",
        bbox=dict(boxstyle="round,pad=0.45",fc="#f4f4f4",ec="#999999"))
ax.grid(alpha=0.25,zorder=0); ax.set_axisbelow(True)
for s in ["top","right"]: ax.spines[s].set_visible(False)
ax.margins(x=0.09,y=0.09)
plt.tight_layout()
plt.savefig("/tmp/work/rent_vs_out_of_borough.png",dpi=165)
print("\nchart saved")
