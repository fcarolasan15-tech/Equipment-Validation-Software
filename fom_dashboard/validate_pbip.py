"""Static checks for a generated Power BI Project before handing it to the user.

    python validate_pbip.py <project folder containing the .pbip>

Power BI Desktop is not available on Linux, so this is the safety net. It checks:
  * the .pbip / definition.pbir / model.bim / report.json files exist and parse
  * every DAX measure / calculated column: balanced quotes and brackets, every 'Table'[Column]
    and [Measure] reference exists, no measure shares a name with a column
  * every M partition: balanced quotes/brackets
  * every visual field, sort, filter and conditional-format reference exists in the model
  * every visual sits inside its page; sortByColumn targets exist
Exit code 1 if anything is wrong.
"""
import json, re, sys, os, glob

def main(folder):
    probs = []
    pbips = glob.glob(os.path.join(folder, "*.pbip"))
    if not pbips:
        print(f"FAIL: no .pbip in {folder}"); return 1
    name = os.path.splitext(os.path.basename(pbips[0]))[0]
    rep, sm = os.path.join(folder, f"{name}.Report"), os.path.join(folder, f"{name}.SemanticModel")
    for p in [os.path.join(rep, "definition.pbir"), os.path.join(rep, "report.json"), os.path.join(sm, "model.bim"),
              os.path.join(sm, "definition.pbism")]:
        if not os.path.exists(p): probs.append(f"missing file {p}")
    if probs:
        print("\n".join(probs)); return 1
    m = json.load(open(os.path.join(sm, "model.bim"), encoding="utf-8"))
    T = m["model"]["tables"]
    names = [x["name"] for t in T for x in t.get("measures", [])]
    cols = {(t["name"], c["name"]) for t in T for c in t["columns"]}
    colnames = {c for _, c in cols}
    if len(names) != len(set(names)): probs.append("duplicate measure names")
    if set(names) & colnames: probs.append(f"measure/column name clash: {set(names) & colnames}")
    strip = lambda e: re.sub(r'"(?:[^"]|"")*"', '""', e)
    for t in T:
        tcols = {c["name"] for c in t["columns"]}
        for c in t["columns"]:
            if c.get("sortByColumn") and c["sortByColumn"] not in tcols:
                probs.append(f"{t['name']}[{c['name']}] sorts by missing column {c['sortByColumn']}")
        items = [(x["name"], x["expression"]) for x in t.get("measures", [])] + \
                [(c["name"], c["expression"]) for c in t["columns"] if c.get("type") == "calculated"]
        for n, e in items:
            e = e if isinstance(e, str) else "\n".join(e)
            if e.count('"') % 2: probs.append(f"DAX [{n}]: odd number of quotes")
            e2 = strip(e)
            if e2.count("(") != e2.count(")"): probs.append(f"DAX [{n}]: unbalanced parentheses")
            for a, b, c in re.findall(r"(?:'([^']+)'|\b([A-Za-z_]\w*))\[([^\]]+)\]", e2):
                if (a or b, c) not in cols: probs.append(f"DAX [{n}]: unknown column {a or b}[{c}]")
            for r in re.findall(r"(?<![\w'\]])\[([^\]]+)\]", e2):
                if r not in names and not r.startswith("@"): probs.append(f"DAX [{n}]: unknown measure [{r}]")
        for p in t.get("partitions", []):
            e = p["source"]["expression"]; e = e if isinstance(e, str) else "\n".join(e)
            if p["source"].get("type") == "m":
                for o, cl in ["()", "{}", "[]"]:
                    if e.count(o) != e.count(cl): probs.append(f"M '{t['name']}': unbalanced {o}{cl}")
                if e.count('"') % 2: probs.append(f"M '{t['name']}': odd number of quotes")
    r = json.load(open(os.path.join(rep, "report.json"), encoding="utf-8"))
    nvis = 0
    for s in r["sections"]:
        for v in s["visualContainers"]:
            nvis += 1
            sv = json.loads(v["config"])["singleVisual"]
            where = f"page '{s['displayName']}' {sv['visualType']} at ({v['x']},{v['y']})"
            if v["x"] + v["width"] > s["width"] + 1 or v["y"] + v["height"] > s["height"] + 1:
                probs.append(f"{where}: outside the page")
            q = sv.get("prototypeQuery")
            if q:
                al = {f["Name"]: f["Entity"] for f in q["From"]}
                for sel in q["Select"] + [o["Expression"] for o in q.get("OrderBy", [])]:
                    k = "Measure" if "Measure" in sel else "Column"
                    ent, p = al[sel[k]["Expression"]["SourceRef"]["Source"]], sel[k]["Property"]
                    if (k == "Measure" and p not in names) or (k == "Column" and (ent, p) not in cols):
                        probs.append(f"{where}: unknown field {ent}.{p}")
            for mm in re.findall(r'"Property": "([^"]+)"', v["filters"] + json.dumps(sv.get("objects", {}))):
                if mm not in names and mm not in colnames: probs.append(f"{where}: unknown reference {mm}")
    if probs:
        print(f"FAIL ({len(probs)} problems)"); print("\n".join(sorted(set(probs)))); return 1
    print(f"OK: {len(T)} tables, {len(names)} measures, {len(r['sections'])} pages, {nvis} visuals - no broken references")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
