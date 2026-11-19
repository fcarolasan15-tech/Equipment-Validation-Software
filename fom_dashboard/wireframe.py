"""Draw a PNG layout wireframe of every page of a generated Power BI Project (no Power BI needed).

    python wireframe.py <project folder> <output folder>

Shows panels, titles, slicers, chart types and the fields/measures each visual uses («Measure» = card).
Use it to let the user review layout before they open the project; say clearly it is a wireframe, not a screenshot.
"""
import json, os, sys, glob
from PIL import Image, ImageDraw, ImageFont

NAMES = {"lineClusteredColumnComboChart": "combo chart", "clusteredBarChart": "bar chart", "clusteredColumnChart": "column chart",
         "columnChart": "stacked column", "barChart": "stacked bar", "lineChart": "line chart", "tableEx": "table",
         "pivotTable": "matrix", "treemap": "treemap", "pieChart": "pie chart", "donutChart": "donut"}

def font(sz, bold=False):
    for f in [f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf"]:
        try: return ImageFont.truetype(f, sz)
        except OSError: pass
    return ImageFont.load_default()

def lit(obj, *path):
    for p in path:
        if isinstance(obj, list): obj = obj[0] if obj else {}
        obj = obj.get(p, {}) if isinstance(obj, dict) else {}
    return obj.get("expr", {}).get("Literal", {}).get("Value", "") if isinstance(obj, dict) else ""

def main(folder, out):
    name = os.path.splitext(os.path.basename(glob.glob(os.path.join(folder, "*.pbip"))[0]))[0]
    rep = os.path.join(folder, f"{name}.Report")
    r = json.load(open(os.path.join(rep, "report.json"), encoding="utf-8"))
    logo_p = os.path.join(rep, "StaticResources", "RegisteredResources", "logo.png")
    logo = Image.open(logo_p).convert("RGBA") if os.path.exists(logo_p) else None
    os.makedirs(out, exist_ok=True)
    for s in r["sections"]:
        im = Image.new("RGB", (s["width"], s["height"]), "#F3F6F1"); d = ImageDraw.Draw(im)
        for v in sorted(s["visualContainers"], key=lambda v: v["z"]):
            sv = json.loads(v["config"])["singleVisual"]; t = sv["visualType"]
            x, y, w, h = v["x"], v["y"], v["width"], v["height"]; vc = sv.get("vcObjects", {})
            if t == "image":
                if logo: lg = logo.resize((w, h)); im.paste(lg, (x, y), lg)
                continue
            if lit(vc, "background", "properties", "show") == "true":
                col = lit(vc, "background", "properties", "color", "solid", "color").strip("'") or "#FFFFFF"
                d.rounded_rectangle([x, y, x + w, y + h], radius=8, fill=col, outline="#DDE5DA" if col == "#FFFFFF" else col)
            title = lit(vc, "title", "properties", "text").strip("'")
            if t == "textbox":
                yy = y + 4
                for p in sv["objects"]["general"][0]["properties"]["paragraphs"]:
                    txt = "".join(r_["value"] for r_ in p["textRuns"])
                    if not txt: continue
                    st = p["textRuns"][0]["textStyle"]; sz = int(float(st["fontSize"].replace("pt", "")) * 1.25)
                    f = font(sz, "fontWeight" in st); line = ""
                    for wd in txt.split(" "):
                        if d.textlength(line + wd + " ", font=f) > w - 12:
                            d.text((x + 6, yy), line, fill=st.get("color", "#1B2A1E"), font=f); yy += sz + 3; line = ""
                        line += wd + " "
                    d.text((x + 6, yy), line, fill=st.get("color", "#1B2A1E"), font=f); yy += sz + 4
            elif t == "card":
                m = sv["prototypeQuery"]["Select"][0]["Measure"]["Property"]
                sz = int(float(lit(sv["objects"], "labels", "properties", "fontSize")[:-1] or 12) * 1.1)
                d.text((x + 4, y + max(0, (h - sz) // 2)), "«" + m + "»", fill="#2E7D32" if sz > 20 else "#5F6B61", font=font(min(sz, 22), sz > 20))
            elif t == "slicer":
                d.rounded_rectangle([x, y + 20, x + w, y + h - 4], radius=4, outline="#B7C4B3", fill="#FFFFFF")
                d.text((x + 4, y + 2), lit(sv["objects"], "header", "properties", "text").strip("'"), fill="#5F6B61", font=font(12))
                d.text((x + 8, y + 28), "All  ▾", fill="#1B2A1E", font=font(13))
            elif t == "actionButton" or "prototypeQuery" not in sv:
                txt = lit(sv.get("objects", {}), "text", "properties", "text").strip("'")
                if txt:
                    d.rounded_rectangle([x, y, x + w, y + h], radius=6, fill="#2E7D32")
                    d.text((x + 8, y + h // 2 - 7), txt, fill="#FFFFFF", font=font(12, True))
                else:
                    d.rectangle([x + 2, y + 2, x + w - 2, y + h - 2], outline="#2E7D32", width=1)
                    d.text((x + w - 120, y + h - 16), "(click → weekly)", fill="#2E7D32", font=font(10))
            else:
                d.text((x + 12, y + 10), title, fill="#0B3D12", font=font(14, True))
                sel = [q.get("Measure", q.get("Column"))["Property"] for q in sv["prototypeQuery"]["Select"]]
                d.rectangle([x + 12, y + 40, x + w - 12, y + h - 12], outline="#E1E8DE")
                d.text((x + 20, y + 48), "[" + NAMES.get(t, t) + "]", fill="#8BC34A", font=font(13, True))
                for i, f_ in enumerate(sel[:9]): d.text((x + 20, y + 68 + 16 * i), "• " + f_, fill="#5F6B61", font=font(12))
        p = os.path.join(out, f"wireframe_{s['displayName'].replace(' ', '_')}.png"); im.save(p); print(p)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
