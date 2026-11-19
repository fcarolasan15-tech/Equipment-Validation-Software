"""Replays the dashboard's Power Query rules in pandas and prints the values the cards/tables should show.

    python -I fom_expected_values.py <GHP .xlsx or .csv> <Line FOM .xlsx> [--asof YYYY-MM-DD]
"""
import sys, re, argparse
import pandas as pd

ap = argparse.ArgumentParser(); ap.add_argument("ghp"); ap.add_argument("line"); ap.add_argument("--asof")
a = ap.parse_args()
norm = lambda c: " ".join(str(c).split()).upper()
key = lambda v: "" if pd.isna(v) else re.sub(r"[^A-Z0-9&]", "", str(v).upper())
DEPT = {"PREPRECEIVING": "Prep Receiving", "PREPPT": "Prep PT", "PREPMTCE": "Prep Mtce", "MAINTENANCEPREP": "Prep Mtce", "PREPMAINTENANCE": "Prep Mtce",
        "COOKROOM": "Cookroom", "SPDCOOKROOM": "Cookroom", "CRUSH": "Crush", "CRUSHED": "Crush", "SPDCRUSHED": "Crush", "SPDCRUSH": "Crush",
        "SPDMTCE": "SPD Mtce", "TPD": "TPD", "POD": "POD", "CANPLANT": "Can Plant", "CANPLANTMTCE": "Can Plant Mtce", "LPD": "LPD", "LPDMTCE": "LPD Mtce",
        "FPDIPIC": "FPD/IPIC", "FPD": "FPD/IPIC", "IPIC": "FPD/IPIC", "TETRA": "Tetra", "JNDFDM": "JnD/FDM", "J&D": "JnD/FDM", "JND": "JnD/FDM", "JD": "JnD/FDM",
        "J&DFDM": "JnD/FDM", "GPSLMTCE": "GPSL Mtce"}
CAT = {"METAL": "Metal", "GLASS": "Glass", "HAIR": "Hair", "INSECT": "Insect", "INSECTS": "Insect", "PAINTFLAKE": "Paint Flake", "PAINTFLAKES": "Paint Flake",
       "RUBBER": "Rubber", "THREAD": "Thread", "THREADS": "Thread", "WOOD": "Wood", "PLASTIC": "Plastic", "STONE": "Stone", "GREASE": "Grease", "PAPER": "Paper",
       "PERSONNEL": "Personnel", "CONVEYORSTRIP": "Conveyor Strip", "OTHER": "Other", "OTHERS": "Other"}
def dept(v):
    if pd.isna(v) or not str(v).strip(): return None
    k = key(v); return DEPT.get(k.replace("&", ""), DEPT.get(k, " ".join(str(v).split()).upper()))
def cat(v):
    if pd.isna(v) or not str(v).strip(): return None
    return CAT.get(key(v), " ".join(str(v).split()).upper())
def todate(v):
    if pd.isna(v): return pd.NaT
    if isinstance(v, (pd.Timestamp,)) or hasattr(v, "year"): return pd.Timestamp(v).normalize()
    s = str(v).strip(); p = s.split("/")
    try: return pd.Timestamp(int(p[2]), int(p[1]), int(p[0])) if len(p) == 3 else pd.to_datetime(s, format="%d-%b-%y")
    except Exception: return pd.NaT

# ---- GHP
if a.ghp.lower().endswith(".csv"):
    g = pd.read_csv(a.ghp, encoding="cp1252", dtype=str)
else:
    g = pd.concat([d for d in pd.read_excel(a.ghp, sheet_name=None).values() if "FOM CATEGORY" in [norm(c) for c in d.columns]])
g.columns = [norm(c) for c in g.columns]
g = g[g["DATE"].notna() | g["FINDING"].fillna("").str.strip().ne("")]
g["Date"] = g["DATE"].map(todate)
g["Dept"] = g["DEPARTMENT"].map(dept).fillna("Not recorded")
g["Cat"] = g["FOM CATEGORY"].map(cat).fillna("Not recorded")
g["Status"] = g["STATUS"].map(lambda v: {"CORRECTED": "Corrected", "UNCORRECTED": "Uncorrected"}.get(key(v), "Not stated"))
# ---- Line FOM
x = pd.read_excel(a.line, sheet_name=[s for s in pd.ExcelFile(a.line).sheet_names if "HAZARD" in s.upper()][0])
x.columns = [norm(c) for c in x.columns]
x = x[x["DATE"].notna() | x["COUNT"].notna() | x["FOM CODE"].notna()]
x["Date"] = x["DATE"].map(todate)
x["n"] = pd.to_numeric(x["COUNT"], errors="coerce")
x["Type"] = x["FOM CODE"].map(cat); x["Src"] = x["POSSIBLE SOURCE - DEPARTMENT"].map(dept)
def grp(r):
    m, p = key(r["FOM DETECTION"]), key(r["FOM DETECTION LINE/AREA #"])
    if m == "XRAY": return "X-Ray: Labelling" if p.startswith("LABELLING") else "X-Ray: J&D Juice" if p.startswith("JUICE") else "X-Ray: IPIC"
    if m == "METALDETECTOR": return "Metal Detection: Plastic Cup" if "PLASTICCUP" in p else "Metal Detection: Aseptic Crushed" if "CRUSHED" in p else "Metal Detection: LPD" if p.startswith("LPD") else "Metal Detection: Other"
    if m == "VISUALINSPECTION": return "Visual Inspection: Lab Audits" if "LABAUDIT" in p else "Visual Inspection: Pre-Shipment" if "PRESHIPMENT" in p else "Visual Inspection: Metal Fragment" if "METALFRAGMENT" in p else "Visual Inspection: Line Interception"
    return "Not recorded"
x["Group"] = x.apply(grp, axis=1)

rd = pd.Timestamp(a.asof) if a.asof else max(g["Date"].max(), x["Date"].max())
fy = pd.Timestamp(rd.year - (1 if rd.month < 5 else 0), 5, 1); ms = rd.replace(day=1); ws = rd - pd.Timedelta(days=rd.weekday())
pm_s, pm_e = (ms - pd.DateOffset(months=1)), ms - pd.Timedelta(days=1); pw_s, pw_e = ws - pd.Timedelta(days=7), ws - pd.Timedelta(days=1)
win = lambda d, s, e: d[(d["Date"] >= s) & (d["Date"] <= e)]
gy, xy = win(g, fy, rd), win(x, fy, rd)
c, u = (gy["Status"] == "Corrected").sum(), (gy["Status"] == "Uncorrected").sum()
print(f"Report date {rd:%a %d %b %Y} · FY start {fy:%d %b %Y}\n")
print("GHP rows loaded", len(g), "| no date", g["Date"].isna().sum())
print(f"GHP findings YTD {len(gy)} | MTD {len(win(g, ms, rd))} | WTD {len(win(g, ws, rd))} | last month {len(win(g, pm_s, pm_e))} | last week {len(win(g, pw_s, pw_e))}")
print(f"GHP corrected {c}, uncorrected {u}, not stated {(gy['Status'] == 'Not stated').sum()} -> % corrected {c / (c + u):.1%}")
print("Top GHP category:", gy["Cat"].value_counts().head(3).to_dict(), "| top dept:", gy["Dept"].value_counts().head(3).to_dict())
run = (xy["n"].notna()).sum()
print(f"\nLine FOM pieces YTD {xy['n'].sum():.0f} ({(xy['n'] > 0).sum()} incidents) | MTD {win(x, ms, rd)['n'].sum():.0f} | WTD {win(x, ws, rd)['n'].sum():.0f}"
      f" | last month {win(x, pm_s, pm_e)['n'].sum():.0f} | last week {win(x, pw_s, pw_e)['n'].sum():.0f}")
print(f"Running line-days YTD {run} -> {xy['n'].sum() * 100 / run:.2f} FOM per 100; MTD rate {win(x, ms, rd)['n'].sum() * 100 / win(x, ms, rd)['n'].notna().sum():.2f}")
und = x[x["Date"].isna() & (x["n"] > 0)]
print("Undated FOM rows (Excel row):", [int(i) + 2 for i in und.index], "pieces", und["n"].sum())
f = xy[xy["n"] > 0].assign(M=lambda d: d["Date"].dt.strftime("%m %b"))
print("Top FOM type:", f.groupby("Type")["n"].sum().sort_values(ascending=False).head(3).to_dict())
print("Top source:", f.groupby("Src")["n"].sum().sort_values(ascending=False).head(3).to_dict())
print("Top detection:", f.groupby("Group")["n"].sum().sort_values(ascending=False).head(3).to_dict())
mon = lambda d: d["Date"].dt.strftime("%m %b")
print("\nGHP findings by category x month (this FY):"); print(pd.crosstab(gy["Cat"], mon(gy), margins=True, margins_name="Total").to_string())
print("\nLine FOM pieces by type x month:"); print(f.pivot_table(index="Type", columns="M", values="n", aggfunc="sum", margins=True, margins_name="Total").fillna("").to_string())
print("\nLine FOM pieces by detection point x month:"); print(f.pivot_table(index="Group", columns="M", values="n", aggfunc="sum", margins=True, margins_name="Total").fillna("").to_string())
