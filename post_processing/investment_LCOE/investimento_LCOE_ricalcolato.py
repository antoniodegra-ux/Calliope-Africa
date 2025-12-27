# -*- coding: utf-8 -*-
"""
existing: Investments + LCOE con Diesel backup
+ Tabella cumulata degli investimenti totali per scenario (2030–2040)
"""

from pathlib import Path
import re, yaml
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ========= CONFIG =========
BASE_2030 = Path("/Users/antoniodegrazia/Desktop/run_2030_new_true")
BASE_2035 = Path("/Users/antoniodegrazia/Desktop/run_2035_new_true")
BASE_2040 = Path("/Users/antoniodegrazia/Desktop/run_2040_new_true")

OUT_DIR   = Path("/Users/antoniodegrazia/Desktop/planning/grafici/INVESTIMENTO GRAFICO")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUTFIG        = OUT_DIR / "existing_Investment_LCOE_withDiesel_2030_2035_2040.png"
OUT_CSV_DETAIL= OUT_DIR / "existing_Investment_detail_withDiesel_2030_2035_2040.csv"
OUT_CSV_LCOE  = OUT_DIR / "existing_LCOE_detail_withDiesel_2030_2035_2040.csv"
OUT_TABLE     = OUT_DIR / "existing_Investment_Cumulative_Table.png"

RESULTS_SUB = Path("results")
DISCOUNT_RATE = 0.10
BASE_YEAR = 2025

# Diesel params
DIESEL_EFF = 0.35
DIESEL_FUEL_PRICE = 0.0493
DIESEL_CAPEX = 708.0
DIESEL_FOM   = 24.0

# Colori
COL = {"OCGT":"#f4b6b6", "Wind":"#66b3ff", "PV":"#ffd34d",
       "Storage":"#b9d97c", "Transmission":"#a7a7a7"}
LCOE_COLOR = "red"

# Regex
PV_NEW   = re.compile(r"^PV_.*_MSR(?!.*installed$)", re.IGNORECASE)
WIND_NEW = re.compile(r"^Wind_.*_MSR(?!.*installed$)", re.IGNORECASE)
INST_END = re.compile(r"_installed$", re.IGNORECASE)
EXCLUDE_TECHS = ["BESS","PHES","transmission","new_transmission",
                 "220_kV","132_kV","400_kV","500_kV","installed"]

# ========= UTIL =========
def discount_to_2025(val, year):
    n = max(0, int(year) - BASE_YEAR)
    return val / ((1.0+DISCOUNT_RATE)**n)

def read_costs_generation(tech_yaml_path: Path) -> dict:
    with open(tech_yaml_path,"r") as f:
        y = yaml.safe_load(f) or {}
    techs = (y.get("techs") or {})
    out={}
    for t,tdef in techs.items():
        mon=((tdef or {}).get("costs") or {}).get("monetary") or {}
        out[t]={"capex":mon.get("energy_cap"),"om_annual":mon.get("om_annual")}
    return out

def read_tx_costs_and_distances(tx_links_yaml: Path):
    with open(tx_links_yaml,"r") as f:
        y = yaml.safe_load(f) or {}
    tx_costs={"energy_cap":None,"energy_cap_per_distance":None}
    if "new_transmission" in (y.get("techs") or {}):
        mon=((y["techs"]["new_transmission"]).get("costs") or {}).get("monetary") or {}
        tx_costs["energy_cap"]=mon.get("energy_cap")
        tx_costs["energy_cap_per_distance"]=mon.get("energy_cap_per_distance")
    dist_map={}
    for pair,blob in (y.get("links") or {}).items():
        try: A,B=[s.strip() for s in pair.split(",")]
        except: continue
        key=tuple(sorted([A,B]))
        if "new_transmission" in (blob.get("techs") or {}):
            d=(blob["techs"]["new_transmission"] or {}).get("distance")
            if d is not None: dist_map[key]=float(d)
    return tx_costs,dist_map

# ========= COMPONENTI =========
def compute_investments_from_ecap(df_cap, gen_costs, tx_costs, tx_dist):
    out={"PV":0.0,"Wind":0.0,"OCGT":0.0,"Storage":0.0,"Transmission":0.0}
    if df_cap.empty: return pd.Series(out,dtype=float)
    for _,row in df_cap.iterrows():
        tech=str(row["techs"]); capkW=float(row["energy_cap"])
        if capkW<=0 or INST_END.search(tech): continue
        if   PV_NEW.match(tech): cat="PV"
        elif WIND_NEW.match(tech): cat="Wind"
        elif tech=="OCGT_NG_new": cat="OCGT"
        elif tech in ("BESS","PHES"): cat="Storage"
        elif tech.startswith("new_transmission"): continue
        else: continue
        c=(gen_costs.get(tech) or {}).get("capex")
        if c: out[cat]+=capkW*float(c)
    pair_cap={}
    mask_tx=pd.Series(df_cap["techs"]).astype(str).str.startswith("new_transmission",na=False)
    for _,row in df_cap[mask_tx].iterrows():
        locA=str(row["locs"]).strip(); techf=str(row["techs"]).strip(); capkW=float(row["energy_cap"])
        if capkW<=0 or ":" not in techf: continue
        _,nodeB=techf.split(":",1); pair=tuple(sorted([locA,nodeB.strip()]))
        pair_cap[pair]=max(pair_cap.get(pair,0.0),capkW)
    c_cap=tx_costs.get("energy_cap"); c_dist=tx_costs.get("energy_cap_per_distance")
    for pair,capkW in pair_cap.items():
        d100=tx_dist.get(pair,0.0)
        out["Transmission"]+=capkW*(float(c_cap) if c_cap else 0.0)+capkW*d100*(float(c_dist) if c_dist else 0.0)
    return pd.Series(out,dtype=float)

def compute_Ft(df_cap,gen_costs):
    Ft=0.0
    for _,row in df_cap.iterrows():
        tech=str(row["techs"]); capkW=float(row["energy_cap"])
        if capkW<=0 or INST_END.search(tech): continue
        om=(gen_costs.get(tech) or {}).get("om_annual")
        if om: Ft+=capkW*float(om)
    return Ft

def compute_Vt(results_dir):
    p=results_dir/"results_cost_var.csv"
    if not p.exists(): return 0.0
    df=pd.read_csv(p)
    if "costs" in df.columns:
        df=df[df["costs"].astype(str).str.lower()=="monetary"]
    return float(pd.to_numeric(df.iloc[:,-1],errors="coerce").replace([np.inf,-np.inf],np.nan).dropna().sum())

def compute_Et(results_dir):
    p=results_dir/"results_carrier_prod.csv"
    if not p.exists(): return 0.0
    df=pd.read_csv(p)
    if "techs" not in df.columns or "carrier_prod" not in df.columns: return 0.0
    exclude="|".join(EXCLUDE_TECHS)
    mask=~df["techs"].astype(str).str.contains(exclude,case=False,na=False)
    return float(pd.to_numeric(df.loc[mask,"carrier_prod"],errors="coerce").sum())

def compute_unmet_and_diesel(results_dir,year):
    p=results_dir/"results_unmet_demand.csv"
    if not p.exists(): 
        return dict(E_unmet=0.0,P_diesel=0.0,capex_d=0.0,fom_d=0.0,vcost_d=0.0)
    df=pd.read_csv(p)
    if "unmet_demand" in df.columns:
        s=pd.to_numeric(df["unmet_demand"],errors="coerce").fillna(0.0)
    else:
        num=[c for c in df.columns if df[c].dtype.kind in "if"]
        s=pd.to_numeric(df[num].sum(axis=1),errors="coerce").fillna(0.0)
    s_pos=s[s>0]
    if s_pos.empty:
        return dict(E_unmet=0.0,P_diesel=0.0,capex_d=0.0,fom_d=0.0,vcost_d=0.0)
    E_unmet=float(s_pos.sum()); peak=float(s_pos.max())
    P_diesel=peak/DIESEL_EFF
    capex=P_diesel*DIESEL_CAPEX; fom=P_diesel*DIESEL_FOM
    fuel_kwh=E_unmet/DIESEL_EFF; vcost=fuel_kwh*DIESEL_FUEL_PRICE
    return dict(E_unmet=E_unmet,P_diesel=P_diesel,
                capex_d=discount_to_2025(capex,year),
                fom_d=discount_to_2025(fom,year),
                vcost_d=discount_to_2025(vcost,year))

def compute_lcoe(It_busd,Ft_usd,Vt_usd,Et_kWh,year):
    if Et_kWh<=0: return np.nan
    return (It_busd*1e9 + Ft_usd + Vt_usd)/Et_kWh*1000.0

# ========= PIPELINE =========
def collect_year(base_dir,year):
    run_dir=base_dir/"run_existing"
    wanted=[f"existing_VRES_{year}_nostorage",
            f"existing_VRES_{year}_BESS",
            f"existing_VRES_{year}_PHES",
            f"existing_GT+VRES_{year}_nostorage",
            f"existing_GT+VRES_{year}_BESS",
            f"existing_GT+VRES_{year}_PHES"]
    rows=[]
    for scen in wanted:
        scen_dir=run_dir/scen; results_dir=scen_dir/"results"
        df_cap=pd.read_csv(results_dir/"results_energy_cap.csv")
        tech_yaml=scen_dir/"Model_config"/"Technologies.yaml"
        tx_yaml=scen_dir/"Model_config"/"Transmission_links.yaml"
        gen_costs=read_costs_generation(tech_yaml)
        tx_costs,tx_dist=read_tx_costs_and_distances(tx_yaml)
        inv_usd=compute_investments_from_ecap(df_cap,gen_costs,tx_costs,tx_dist)
        inv_usd_disc=inv_usd.apply(lambda v: discount_to_2025(v,int(year)))
        inv_busd=inv_usd_disc/1e9
        Ft=discount_to_2025(compute_Ft(df_cap,gen_costs),year)
        Vt=discount_to_2025(compute_Vt(results_dir),year)
        Et_raw=compute_Et(results_dir)
        diesel=compute_unmet_and_diesel(results_dir,year)
        Et=Et_raw+diesel["E_unmet"]
        inv_busd_total=float(inv_busd.fillna(0.0).sum())+diesel["capex_d"]/1e9
        LCOE=compute_lcoe(inv_busd_total,Ft+diesel["fom_d"],Vt+diesel["vcost_d"],Et,year)
        group="VRES+GT" if "+vres" in scen.lower() else "VRES"
        if "nostorage" in scen.lower(): code="N"
        elif "bess" in scen.lower(): code="B"
        elif "phes" in scen.lower(): code="P"
        else: code="?"
        rows.append({"group":group,"code":code,"PV":inv_busd.get("PV",0.0),
                     "Wind":inv_busd.get("Wind",0.0),"OCGT":inv_busd.get("OCGT",0.0),
                     "Storage":inv_busd.get("Storage",0.0),"Transmission":inv_busd.get("Transmission",0.0),
                     "Total_Investment_BUSD":inv_busd.fillna(0.0).sum(),
                     "LCOE":LCOE})
    return pd.DataFrame(rows)

# ========= MAIN =========
df30=collect_year(BASE_2030,2030)
df35=collect_year(BASE_2035,2035)
df40=collect_year(BASE_2040,2040)

# ======== TAB cumulata ========
df30["year"]="2030"
df35["year"]="2035"
df40["year"]="2040"
df_all=pd.concat([df30,df35,df40],ignore_index=True)

# Calcolo investimento cumulato per scenario
df_all["scenario"]=df_all["group"]+"_"+df_all["code"]
cumul=df_all.groupby("scenario")["Total_Investment_BUSD"].sum().reset_index()
cumul["Total_Investment_BUSD"]=cumul["Total_Investment_BUSD"].round(2)
cumul=cumul.sort_values("scenario")

# Salva CSV
cumul.to_csv(OUT_DIR/"existing_Investment_Cumulative.csv",index=False)

# Disegna tabella PNG
fig,ax=plt.subplots(figsize=(5,2.8))
ax.axis("off")
tbl=ax.table(cellText=cumul.values,
             colLabels=["Scenario","Total Investment [B$]"],
             loc="center",cellLoc="center")
tbl.auto_set_font_size(False)
tbl.set_fontsize(10)
tbl.scale(1.4,1.4)
plt.tight_layout()
plt.savefig(OUT_TABLE,dpi=300,bbox_inches="tight")
plt.close(fig)

print("✅ Tabella salvata:", OUT_TABLE)
print("✅ Figura investimenti:", OUTFIG)
