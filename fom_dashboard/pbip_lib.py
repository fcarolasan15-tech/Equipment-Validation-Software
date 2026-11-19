"""pbip_lib - toolkit (FOM copy: write_project takes several source files) for generating Power BI Projects (PBIP: report.json + model.bim) in the Cannery QA style.

Usage pattern (see build_ftq_dashboard.py for a complete example):
    from pbip_lib import *
    set_header_tagline("Cannery QA  ·  <subject>  ·  Target <x>")
    meas(...)                      # register DAX measures (go into the _Measures table)
    tables = [table(...), ...]     # Power Query (M) partitions + column metadata
    visual(...), card(...), ...    # place visuals on pages (page id strings)
    write_project(out_dir, name, tables, relationships, pages, source, logo)
"""
import json, uuid, os, shutil, hashlib

def tag(): return str(uuid.uuid4())
MT = "_Measures"

DARK, GREEN, LIME, BG, RED, AMBER, INK, MUTED, LINE, SOFT = (
    "#0B3D12", "#2E7D32", "#8BC34A", "#F3F6F1", "#C62828", "#F9A825", "#1B2A1E", "#5F6B61", "#DDE5DA", "#F6FAF3")
# Pages are 16:9, 1280 x 720 (Power BI's standard size), fit to page - the team's preference since v2.4.
CONFIG = {"tagline": "Cannery QA", "page_w": 1280, "page_h": 720, "background": None}
# Every font is Arial (team decision, v2.5). Text sizes are chosen to stay readable on a 16:9 page.
FONT = "Arial"
SUB = "#3F4A41"   # darker grey for subtitles / secondary text (contrast on the cream background)
def set_header_tagline(text): CONFIG["tagline"] = text

# =====================================================================================  MEASURES
measures = []
def meas(name, expr, fmt=None, folder=None, desc=None):
    e = expr.strip("\n")
    m = {"name": name, "expression": e.split("\n") if "\n" in e else e.strip(), "lineageTag": tag()}
    if fmt: m["formatString"] = fmt
    if folder: m["displayFolder"] = folder
    if desc: m["description"] = desc
    measures.append(m)

def finalize_measures():
    """Collapse one-line expressions to plain strings (call once, after all meas())."""
    for m in measures:
        if isinstance(m["expression"], list) and len(m["expression"]) == 1:
            m["expression"] = m["expression"][0]
    return measures

# =====================================================================================  TABLES
def col(name, dt, src=None, fmt=None, hidden=False, sort_by=None, key=False, summarize="none", desc=None):
    c = {"name": name, "dataType": dt, "sourceColumn": src or name, "lineageTag": tag(), "summarizeBy": summarize}
    if fmt: c["formatString"] = fmt
    elif dt == "dateTime": c["formatString"] = "dd mmm yyyy"
    if hidden: c["isHidden"] = True
    if sort_by: c["sortByColumn"] = sort_by
    if key: c["isKey"] = True
    if desc: c["description"] = desc
    return c

def calc_col(name, dt, expr, fmt=None, desc=None):
    c = {"type": "calculated", "name": name, "dataType": dt, "isDataTypeInferred": True, "expression": expr,
         "lineageTag": tag(), "summarizeBy": "none"}
    if fmt: c["formatString"] = fmt
    if desc: c["description"] = desc
    return c

def table(name, columns, m, hidden=False, extra=None):
    t = {"name": name, "lineageTag": tag(), "columns": columns,
         "partitions": [{"name": name, "mode": "import", "source": {"type": "m", "expression": m.strip("\n").split("\n")}}]}
    if hidden: t["isHidden"] = True
    if extra: t.update(extra)
    return t

S_ = "string"

def rel(ft, fc, tt, tc, active=True):
    r = {"name": tag(), "fromTable": ft, "fromColumn": fc, "toTable": tt, "toColumn": tc}
    if not active: r["isActive"] = False
    return r

# =====================================================================================  REPORT helpers
def L(v): return {"expr": {"Literal": {"Value": v}}}
def S(s): return L("'" + s.replace("'", "''") + "'")
def N(n): return L(f"{n}D")
def B(b): return L("true" if b else "false")
def color(h): return {"solid": {"color": S(h)}}
def mcolor(m): return {"solid": {"color": {"expr": {"Measure": {"Expression": {"SourceRef": {"Entity": MT}}, "Property": m}}}}}

class Q:
    def __init__(self):
        self.frm, self.sel, self.alias, self.proj, self.order = [], [], {}, {}, []
    def src(self, ent):
        if ent not in self.alias:
            a = "".join(ch for ch in ent.lower() if ch.isalpha())[:1] or "t"
            base, i = a, 1
            while a in self.alias.values(): a = f"{base}{i}"; i += 1
            self.alias[ent] = a
            self.frm.append({"Name": a, "Entity": ent, "Type": 0})
        return self.alias[ent]
    def ref(self, ent, prop, kind):
        return {("Measure" if kind == "m" else "Column"): {"Expression": {"SourceRef": {"Source": self.src(ent)}}, "Property": prop}}
    def add(self, role, ent, prop, kind="c"):
        name = f"{ent}.{prop}"
        if not any(s["Name"] == name for s in self.sel):
            e = self.ref(ent, prop, kind); e["Name"] = name; e["NativeReferenceName"] = prop
            self.sel.append(e)
        p = {"queryRef": name}
        if role in ("Category", "Rows", "Group") and role not in self.proj: p["active"] = True
        self.proj.setdefault(role, []).append(p)
        return self
    def m(self, role, prop): return self.add(role, MT, prop, "m")
    def sort(self, ent, prop, kind="c", desc=False):
        self.order.append({"Direction": 2 if desc else 1, "Expression": self.ref(ent, prop, kind)}); return self
    def build(self):
        q = {"Version": 2, "From": self.frm, "Select": self.sel}
        if self.order: q["OrderBy"] = self.order
        return q

containers, _z = [], [0]
def visual(page, vtype, x, y, w, h, q=None, objects=None, vc=None, title=None, filters=None, extra=None, panel=True, header=True, subtitle=None):
    _z[0] += 1000
    vco = dict(vc or {})
    if title:
        vco.setdefault("title", [{"properties": {"show": B(True), "text": S(title), "fontColor": color(DARK), "fontSize": N(11),
                                                   "bold": B(True), "fontFamily": S(FONT)}}])
        if subtitle:
            vco["subTitle"] = [{"properties": {"show": B(True), "text": S(subtitle), "fontColor": color(SUB), "fontSize": N(9), "fontFamily": S(FONT)}}]
    else:
        vco.setdefault("title", [{"properties": {"show": B(False)}}])
    if panel:
        vco.setdefault("background", [{"properties": {"show": B(True), "color": color("#FFFFFF"), "transparency": N(0)}}])
        vco.setdefault("border", [{"properties": {"show": B(True), "color": color(LINE), "radius": N(10)}}])
        vco.setdefault("padding", [{"properties": {"top": N(4), "bottom": N(4), "left": N(8), "right": N(8)}}])
    else:
        vco.setdefault("background", [{"properties": {"show": B(False)}}])
    if not header:
        vco["visualHeader"] = [{"properties": {"show": B(False)}}]
    sv = {"visualType": vtype, "drillFilterOtherVisuals": True, "vcObjects": vco}
    if q is not None:
        sv["projections"] = q.proj; sv["prototypeQuery"] = q.build()
    if objects: sv["objects"] = objects
    if extra: sv.update(extra)
    name = hashlib.md5(f"{page}{vtype}{x}{y}{_z[0]}".encode()).hexdigest()[:20]
    cfg = {"name": name, "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": _z[0], "width": w, "height": h, "tabOrder": _z[0]}}],
           "singleVisual": sv}
    containers.append((page, {"x": x, "y": y, "z": _z[0], "width": w, "height": h, "config": json.dumps(cfg, ensure_ascii=False),
                              "filters": json.dumps(filters or [], ensure_ascii=False), "tabOrder": _z[0]}))

def st(size, col=INK, bold=False, family=None):
    s = {"fontSize": f"{size}pt", "color": col, "fontFamily": family or FONT}
    if bold: s["fontWeight"] = "bold"
    return s

def textbox(page, x, y, w, h, runs, bg=None, border=False, align="left"):
    paragraphs = [{"textRuns": [{"value": t, "textStyle": s} for t, s in para], "horizontalTextAlignment": align} for para in runs]
    vc = {}
    if bg: vc["background"] = [{"properties": {"show": B(True), "color": color(bg), "transparency": N(0)}}]
    if border: vc["border"] = [{"properties": {"show": B(True), "color": color(LINE), "radius": N(10)}}]
    visual(page, "textbox", x, y, w, h, objects={"general": [{"properties": {"paragraphs": paragraphs}}]}, vc=vc, panel=bool(bg), header=False)

def panel(page, x, y, w, h, fill="#FFFFFF"):
    textbox(page, x, y, w, h, [[("", st(6))]], bg=fill, border=True)

def card(page, x, y, w, h, measure, size=26, col_measure=None, col_static=INK, wrap=False, bold=False):
    q = Q().m("Values", measure)
    lab = {"fontSize": N(size), "fontFamily": S(FONT), "color": mcolor(col_measure) if col_measure else color(col_static)}
    if bold: lab["bold"] = B(True)
    objs = {"labels": [{"properties": lab}], "categoryLabels": [{"properties": {"show": B(False)}}]}
    if wrap: objs["wordWrap"] = [{"properties": {"show": B(True)}}]
    visual(page, "card", x, y, w, h, q, objs, panel=False, header=False)

def slicer(page, x, y, w, h, fields, title, mode="Dropdown", single=False, desc=False, sync=None):
    q = Q()
    for ent, prop in fields: q.add("Values", ent, prop)
    if desc: q.sort(fields[0][0], fields[0][1], desc=True)
    objs = {"data": [{"properties": {"mode": S(mode)}}],
            "selection": [{"properties": {"singleSelect": B(single), "selectAllCheckboxEnabled": B(not single)}}],
            "header": [{"properties": {"show": B(True), "text": S(title), "fontColor": color(SUB), "textSize": N(9), "fontFamily": S(FONT), "bold": B(True)}}],
            "items": [{"properties": {"fontColor": color(INK), "textSize": N(10), "fontFamily": S(FONT)}}]}
    extra = {"syncGroup": {"groupName": sync or title, "fieldChanges": True, "filterChanges": True}}
    visual(page, "slicer", x, y, w, h, q, objs, panel=False, extra=extra)

def axis(start=None, end=None, sec=None, labels=True, legend=True):
    ax = {"fontFamily": S(FONT), "fontSize": N(9), "labelColor": color(INK)}
    va = {"showAxisTitle": B(False), "gridlineShow": B(True), "gridlineColor": color("#E8EEE6"), **ax}
    if start is not None: va["start"] = N(start)
    if end is not None: va["end"] = N(end)
    if sec is not None:
        va["secShow"] = B(sec.get("show", True))
        if "start" in sec: va["secStart"] = N(sec["start"])
        if "end" in sec: va["secEnd"] = N(sec["end"])
    o = {"valueAxis": [{"properties": va}],
         # maxMarginFactor: let long category names (defects, locations) use more room before they are cut off
         "categoryAxis": [{"properties": {"showAxisTitle": B(False), "concatenateLabels": B(False), "maxMarginFactor": N(40), **ax}}],
         "legend": [{"properties": {"show": B(legend), "position": S("Top"), "fontSize": N(9), "fontFamily": S(FONT), "labelColor": color(INK)}}]}
    if labels: o["labels"] = [{"properties": data_labels()}]
    return o

def series_color(o, m, h):
    o.setdefault("dataPoint", []).append({"properties": {"fill": color(h)}, "selector": {"metadata": f"{MT}.{m}"}})

def topn(ent, prop, by, n):
    return [{"name": hashlib.md5(f"topn{ent}{prop}{n}{by}".encode()).hexdigest()[:20],
             "expression": {"Column": {"Expression": {"SourceRef": {"Entity": ent}}, "Property": prop}},
             "filter": {"Version": 2,
                        "From": [{"Name": "subquery", "Expression": {"Subquery": {"Query": {
                            "Version": 2, "From": [{"Name": "i", "Entity": ent, "Type": 0}, {"Name": "m", "Entity": MT, "Type": 0}],
                            "Select": [{"Column": {"Expression": {"SourceRef": {"Source": "i"}}, "Property": prop}, "Name": "field"}],
                            "OrderBy": [{"Direction": 2, "Expression": {"Measure": {"Expression": {"SourceRef": {"Source": "m"}}, "Property": by}}}],
                            "Top": n}}}, "Type": 2}, {"Name": "i", "Entity": ent, "Type": 0}],
                        "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "i"}}, "Property": prop}}],
                                                        "Table": {"SourceRef": {"Source": "subquery"}}}}}]},
             "type": "TopN", "howCreated": 1, "isHiddenInViewMode": False}]

def table_style(extra_values=None):
    o = {"grid": [{"properties": {"gridVertical": B(False), "rowPadding": N(2), "textSize": N(9)}}],
         "columnHeaders": [{"properties": {"backColor": color(DARK), "fontColor": color("#FFFFFF"), "fontSize": N(9), "bold": B(True),
                                           "fontFamily": S(FONT), "wordWrap": B(True), "autoSizeColumnWidth": B(True)}}],
         "values": [{"properties": {"backColorSecondary": color(SOFT), "fontSize": N(9), "fontFamily": S(FONT), "fontColor": color(INK), "wordWrap": B(True)}}],
         "total": [{"properties": {"totals": B(True), "fontColor": color(DARK), "bold": B(True)}}]}
    if extra_values: o["values"] += extra_values
    return o

def data_labels(size=9, col=None):
    """Data-label properties: Arial, readable size, dark text."""
    return {"show": B(True), "fontSize": N(size), "fontFamily": S(FONT), "color": color(col or INK)}

def kpi_tile(page, x, y, w, h, label, value, value_color=None, line1=None, line1_color=None, line2=None, accent=GREEN, value_size=22):
    """Compact KPI tile for 16:9 pages: label, big value, up to two small lines. Works for h >= 64 (value only) or ~96 (with lines)."""
    panel(page, x, y, w, h)
    textbox(page, x, y + 8, 4, h - 16, [[("", st(6))]], bg=accent)
    textbox(page, x + 10, y + 2, w - 14, 18, [[(label, st(8, SUB, True))]])
    card(page, x + 6, y + 18, w - 12, 40, value, size=value_size, col_measure=value_color, bold=True)
    if line1: card(page, x + 6, y + 56, w - 12, 20, line1, size=9, col_measure=line1_color, col_static=INK)
    if line2: card(page, x + 6, y + 74, w - 12, 20, line2, size=8, col_static=SUB, wrap=True)

def header(page, title):
    W = CONFIG["page_w"]
    textbox(page, 0, 0, W, 52, [[("", st(6))]], bg=DARK)
    visual(page, "image", 8, 2, 48, 48, objects={
        "general": [{"properties": {"imageUrl": {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources", "PackageType": 1, "ItemName": "logo.png"}}}}}],
        "imageScaling": [{"properties": {"imageScalingType": S("Fit")}}]}, panel=False, header=False)
    textbox(page, 62, 4, 640, 46, [[(title, st(15, "#FFFFFF", True))],
                                   [(CONFIG["tagline"], st(8, "#CFE8C0"))]])
    card(page, 700, 10, W - 712, 32, "Header Subtitle", size=10, col_static="#E3F2D9")

def filter_bar(page, y, items, h=50):
    """Row of dropdown slicers on a white strip; returns the x where free space starts."""
    panel(page, 12, y, CONFIG["page_w"] - 24, h)
    x = 20
    for fields, title, w, kw in items:
        slicer(page, x, y + 2, w, h - 4, fields, title, **kw); x += w + 8
    return x


# =====================================================================================  SOURCE + WRITE
def source_expressions(sources):
    """sources = [(parameter name, workbook query name, URL or path), ...]. One text parameter + one shared, buffered
    workbook query per file. http(s) -> Web.Contents (SharePoint/OneDrive), otherwise File.Contents."""
    out = []
    for param, wbq, src in sources:
        fn = "Web.Contents" if src.lower().startswith("http") else "File.Contents"
        out.append({"name": param, "kind": "m", "lineageTag": tag(),
                    "expression": '"' + src.replace('"', '""') + '" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]',
                    "annotations": [{"name": "PBI_ResultType", "value": "Text"}]})
        out.append({"name": wbq, "kind": "m", "lineageTag": tag(),
                    "expression": ["let", f"    Source = Excel.Workbook(Binary.Buffer({fn}({param})), null, true)", "in", "    Source"],
                    "annotations": [{"name": "PBI_ResultType", "value": "Table"}]})
    return out

def page_background():
    bg = [{"properties": {"color": color(BG), "transparency": N(0)}}]
    if CONFIG["background"]:
        bg[0]["properties"]["image"] = {"image": {
            "name": S("background.png"),
            "url": {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources", "PackageType": 1, "ItemName": "background.png"}}},
            "scaling": S("Fit")}}
    return bg

def section(name, display, h, ordinal):
    W, H = CONFIG["page_w"], CONFIG["page_h"]
    h = max(h, H)   # 16:9 page; a taller page (h > H) scrolls with fit-to-width
    return {"name": name, "displayName": display, "displayOption": 1 if h == H else 2, "width": W, "height": h, "ordinal": ordinal,
            "config": json.dumps({"objects": {"background": page_background(),
                                              "outspace": [{"properties": {"color": color(BG)}}]}}),
            "filters": "[]", "visualContainers": [c for p, c in containers if p == name]}

THEME = {"name": "Cannery QA",
         "dataColors": [GREEN, AMBER, "#1565C0", RED, "#00897B", "#6D4C41", "#7B1FA2", LIME, DARK, "#C0CA33"],
         "background": "#FFFFFF", "foreground": INK, "tableAccent": GREEN,
         "good": GREEN, "neutral": AMBER, "bad": RED, "maximum": GREEN, "center": AMBER, "minimum": RED,
         "textClasses": {k: {"fontFace": FONT, "color": c, "fontSize": z} for k, c, z in [
             ("callout", INK, 22), ("title", DARK, 11), ("header", DARK, 10), ("label", INK, 9),
             ("largeTitle", DARK, 14), ("smallLabel", SUB, 8), ("largeLabel", INK, 11), ("boldLabel", INK, 9), ("dataTitle", DARK, 11)]}}

def write_project(out, name, tables, relationships, pages, sources, logo, background=None):
    """background: optional 16:9 PNG used as every page's background image (Fit)."""
    CONFIG["background"] = background
    """pages = [(page_id, display_name, height), ...] in tab order. Deletes and recreates `out`."""
    model = {
        "name": name, "compatibilityLevel": 1567,
        "model": {
            "culture": "en-US", "defaultPowerBIDataSourceVersion": "powerBI_V3", "sourceQueryCulture": "en-US",
            "dataAccessOptions": {"legacyRedirects": True, "returnErrorValuesAsNull": True},
            "tables": tables, "relationships": relationships, "expressions": source_expressions(sources),
            "annotations": [
                {"name": "PBI_QueryOrder", "value": json.dumps([q for p_, w_, _ in sources for q in (p_, w_)] + [t["name"] for t in tables])},
                {"name": "__PBI_TimeIntelligenceEnabled", "value": "0"}]}}
    report = {
        "config": json.dumps({"version": "5.59", "themeCollection": {"customTheme": {"name": "CanneryQA_Theme.json", "version": "5.59", "type": 1}},
                              "activeSectionIndex": 0, "defaultDrillFilterOtherVisuals": True,
                              "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": 1, "useNewFilterPaneExperience": True,
                                           "allowChangeFilterTypes": True, "useEnhancedTooltips": True}}),
        "layoutOptimization": 0,
        "resourcePackages": [{"resourcePackage": {"name": "RegisteredResources", "type": 1, "disabled": False, "items": [
            {"type": 202, "path": "CanneryQA_Theme.json", "name": "CanneryQA_Theme.json"},
            {"type": 100, "path": "logo.png", "name": "logo.png"}] +
            ([{"type": 100, "path": "background.png", "name": "background.png"}] if background else [])}}],
        "sections": [section(pid, disp, h, i) for i, (pid, disp, h) in enumerate(pages)],
        "filters": "[]"}
    if os.path.exists(out): shutil.rmtree(out)
    rep, sm = f"{out}/{name}.Report", f"{out}/{name}.SemanticModel"
    os.makedirs(f"{rep}/StaticResources/RegisteredResources"); os.makedirs(sm)
    def wj(p, obj):
        with open(p, "w", encoding="utf-8") as f: json.dump(obj, f, indent=2, ensure_ascii=False)
    wj(f"{out}/{name}.pbip", {"version": "1.0", "artifacts": [{"report": {"path": f"{name}.Report"}}], "settings": {"enableAutoRecovery": True}})
    wj(f"{rep}/definition.pbir", {"version": "4.0", "datasetReference": {"byPath": {"path": f"../{name}.SemanticModel"}}})
    wj(f"{rep}/report.json", report)
    wj(f"{rep}/StaticResources/RegisteredResources/CanneryQA_Theme.json", THEME)
    shutil.copy(logo, f"{rep}/StaticResources/RegisteredResources/logo.png")
    if background: shutil.copy(background, f"{rep}/StaticResources/RegisteredResources/background.png")
    wj(f"{sm}/definition.pbism", {"version": "1.0", "settings": {}})
    wj(f"{sm}/model.bim", model)
    for folder, typ in [(rep, "Report"), (sm, "SemanticModel")]:
        wj(f"{folder}/.platform", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
                                   "metadata": {"type": typ, "displayName": name}, "config": {"version": "2.0", "logicalId": tag()}})
    with open(f"{out}/.gitignore", "w") as f: f.write("**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")
    return {"measures": sum(len(t.get("measures", [])) for t in tables), "visuals": len(containers), "pages": [p[1] for p in pages]}
