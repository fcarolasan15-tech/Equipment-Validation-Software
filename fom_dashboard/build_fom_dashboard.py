"""Build the Cannery QA FOM (Foreign Matter) Monitoring dashboard as a Power BI Project (PBIP).

    python build_fom_dashboard.py --out <folder> [--ghp "<url or path>"] [--line "<url or path>"] [--name "FOM Dashboard"]

Two source workbooks (defaults = the team's FY27 SharePoint files):
  * GHP  - FY27 Daily FOM Inspection.xlsx           every sheet whose header row has FINDING + FOM CATEGORY
  * LINE - Line FOM Detection - Overall Dashboard.xlsx  the sheet whose name contains "HAZARD" (Phyiscal Hazard - FOM)

Pages (16:9): Topsheet, Monthly, Weekly, Details.
Design rule: keep DAX short. Cleaning lives in Power Query; Monthly / Weekly visuals use plain base measures that
follow clicks and slicers; only the Topsheet tiles use period (YTD / month / week) measures.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pbip_lib import *
import pbip_lib, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
GHP_URL = "https://delmontephinc.sharepoint.com/sites/BugoQA-QRM/Shared%20Documents/GHP/FOM%20Monitoring/FY'27/FOM%20FY27/FY27%20Daily%20FOM%20Inspection.xlsx"
LINE_URL = "https://delmontephinc.sharepoint.com/sites/BugoQA-QRM/Shared%20Documents/GHP/FOM%20Monitoring/FY'27/FOM%20FY27/Line%20FOM%20Detection%20-%20Overall%20Dashboard.xlsx"
ap = argparse.ArgumentParser()
ap.add_argument("--ghp", default=GHP_URL, help="FY27 Daily FOM Inspection workbook (URL or local path)")
ap.add_argument("--line", default=LINE_URL, help="Line FOM Detection workbook (URL or local path)")
ap.add_argument("--out", required=True)
ap.add_argument("--name", default="FOM Dashboard")
ap.add_argument("--logo", default=os.path.join(HERE, "assets", "cannery_qa_logo.png"))
ap.add_argument("--background", default=os.path.join(HERE, "assets", "delmonte_background_16x9.png"))
args = ap.parse_args()
set_header_tagline("Cannery QA  ·  FOM Monitoring: GHP inspection + line FOM detection  ·  Target 0 FOM at line, 100% GHP corrected")

# =====================================================================================  POWER QUERY
# Shared helper functions, pasted into each query that needs them (kept short on purpose).
M_FN = r'''
    // SHINE: trim, remove line breaks / non-breaking / double spaces
    CleanText = (v as any) as nullable text =>
        if v = null then null else
        let
            t1 = Text.Replace(Text.Replace(Text.From(v), Character.FromNumber(160), " "), "#(lf)", " "),
            t2 = Text.Combine(List.Select(Text.Split(Text.Clean(t1), " "), each _ <> ""), " ")
        in
            if t2 = "" then null else t2,
    Key = (v as nullable text) as text => if v = null then "" else Text.Select(Text.Upper(v), {"A".."Z", "0".."9", "&"}),
    // dates: real Excel dates, Excel serial numbers, or text typed as dd/mm/yyyy (e.g. 15/10/2026) or 12-May-26
    ToDate = (v as any) as nullable date =>
        if v = null then null
        else if v is date then v
        else if v is datetime then Date.From(v)
        else if v is number then Date.From(v)
        else
            let s = Text.Trim(Text.From(v)), p = Text.Split(s, "/") in
            try (if List.Count(p) = 3 then #date(Number.From(p{2}), Number.From(p{1}), Number.From(p{0}))
                 else Date.From(DateTime.From(s, "en-US"))) otherwise null,
    // one Department list for both files (GHP Department = Line FOM "Possible Source - Department")
    DeptMap = [PREPRECEIVING = "Prep Receiving", PREPPT = "Prep PT", PREPMTCE = "Prep Mtce", MAINTENANCEPREP = "Prep Mtce",
        PREPMAINTENANCE = "Prep Mtce", COOKROOM = "Cookroom", SPDCOOKROOM = "Cookroom", CRUSH = "Crush", CRUSHED = "Crush",
        SPDCRUSHED = "Crush", SPDCRUSH = "Crush", SPDMTCE = "SPD Mtce", TPD = "TPD", POD = "POD", CANPLANT = "Can Plant",
        CANPLANTMTCE = "Can Plant Mtce", LPD = "LPD", LPDMTCE = "LPD Mtce", #"FPDIPIC" = "FPD/IPIC", FPD = "FPD/IPIC",
        IPIC = "FPD/IPIC", TETRA = "Tetra", JNDFDM = "JnD/FDM", #"J&D" = "JnD/FDM", JND = "JnD/FDM", JD = "JnD/FDM", #"J&DFDM" = "JnD/FDM",
        GPSLMTCE = "GPSL Mtce"],
    DeptFn = (v as nullable text) as nullable text =>
        if v = null then null else Record.FieldOrDefault(DeptMap, Text.Remove(Key(v), {"&"}), Record.FieldOrDefault(DeptMap, Key(v), Text.Upper(v))),
    // one FOM Category list for both files
    CatMap = [METAL = "Metal", GLASS = "Glass", HAIR = "Hair", INSECT = "Insect", INSECTS = "Insect", PAINTFLAKE = "Paint Flake",
        PAINTFLAKES = "Paint Flake", RUBBER = "Rubber", THREAD = "Thread", THREADS = "Thread", WOOD = "Wood", PLASTIC = "Plastic",
        STONE = "Stone", GREASE = "Grease", PAPER = "Paper", PERSONNEL = "Personnel", CONVEYORSTRIP = "Conveyor Strip",
        OTHER = "Other", OTHERS = "Other"],
    CatFn = (v as nullable text) as nullable text => if v = null then null else Record.FieldOrDefault(CatMap, Key(v), Text.Upper(v)),'''

M_GHP = r'''
let''' + M_FN + r'''
    // SORT: every sheet whose header row (within the first 10 rows) contains FOM CATEGORY - one sheet or one per month
    HeaderPos = (t as table) as number =>
        List.PositionOf(List.Transform(Table.ToRows(Table.FirstN(t, 10)),
            (r) => List.Contains(List.Transform(r, each try Text.Upper(Text.Trim(Text.From(_))) otherwise ""), "FOM CATEGORY")), true),
    Sheets = Table.AddColumn(Table.SelectRows(GhpWorkbook, each [Kind] = "Sheet"), "Hdr", each HeaderPos([Data]), Int64.Type),
    LogSheets = Table.SelectRows(Sheets, each [Hdr] >= 0),
    Prep = (t as table, h as number, sheet as text) as table =>
        let
            Promoted = Table.PromoteHeaders(Table.Skip(t, h), [PromoteAllScalars = true]),
            Names = Table.TransformColumnNames(Promoted, each Text.Upper(Text.Combine(List.Select(Text.SplitAny(_, " #(lf)#(cr)#(tab)"), each _ <> ""), " "))),
            WithRow = Table.AddIndexColumn(Names, "EXCEL ROW", h + 2, 1, Int64.Type),
            // Excel error cells (#VALUE!, #N/A) would stop the refresh: load them as blank
            NoErr = Table.ReplaceErrorValues(WithRow, List.Transform(Table.ColumnNames(WithRow), each {_, null})),
            Kept = Table.SelectColumns(NoErr, {"EXCEL ROW", "DATE", "INSPECTION", "DEPARTMENT", "FINDING", "FOM CATEGORY", "STATUS",
                "TIME CORRECTED", "REMARKS (IF UNCORRECTED)"}, MissingField.UseNull)
        in
            Table.AddColumn(Kept, "Sheet", each sheet, type text),
    Combined = Table.Combine(Table.AddColumn(LogSheets, "T", each Prep([Data], [Hdr], [Name]))[T]),
    // drop empty rows (no date, no finding, no category) - e.g. the dropdown-list area
    NonEmpty = Table.SelectRows(Combined, each [DATE] <> null or CleanText([FINDING]) <> null),
    // SET IN ORDER + STANDARDISE
    T = Table.FromRecords(Table.TransformRows(NonEmpty, (r) =>
        let st = Key(CleanText(r[STATUS])) in [
            #"Excel Row" = r[EXCEL ROW],
            Sheet = r[Sheet],
            Date = ToDate(r[DATE]),
            Inspection = let i = CleanText(r[INSPECTION]) in if i = null then "Not recorded" else Text.Upper(i),
            Department = let d = DeptFn(CleanText(r[DEPARTMENT])) in if d = null then "Not recorded" else d,
            Finding = CleanText(r[FINDING]),
            #"FOM Category" = let c = CatFn(CleanText(r[FOM CATEGORY])) in if c = null then "Not recorded" else c,
            Status = if st = "CORRECTED" then "Corrected" else if st = "UNCORRECTED" then "Uncorrected" else "Not stated",
            #"Status As Typed" = CleanText(r[STATUS]),
            #"Time Corrected" = CleanText(r[TIME CORRECTED]),
            Remarks = CleanText(r[#"REMARKS (IF UNCORRECTED)"])]),
        type table [#"Excel Row" = Int64.Type, Sheet = text, Date = date, Inspection = text, Department = text, Finding = text,
            #"FOM Category" = text, Status = text, #"Status As Typed" = text, #"Time Corrected" = text, Remarks = text])
in
    T
'''

M_LINE = r'''
let''' + M_FN + r'''
    // SORT: the log sheet ("Phyiscal Hazard - FOM"); Sheet3 is an October copy and is ignored
    Sheet = Table.SelectRows(LineWorkbook, each [Kind] = "Sheet" and Text.Contains(Text.Upper([Name]), "HAZARD")){0}[Data],
    Promoted = Table.PromoteHeaders(Sheet, [PromoteAllScalars = true]),
    Names = Table.TransformColumnNames(Promoted, each Text.Upper(Text.Combine(List.Select(Text.SplitAny(_, " #(lf)#(cr)#(tab)"), each _ <> ""), " "))),
    WithRow = Table.AddIndexColumn(Names, "EXCEL ROW", 2, 1, Int64.Type),
    NoErr = Table.ReplaceErrorValues(WithRow, List.Transform(Table.ColumnNames(WithRow), each {_, null})),
    Kept = Table.SelectColumns(NoErr, {"EXCEL ROW", "DATE", "DEPARTMENT", "FOM DETECTION", "FOM DETECTION LINE/AREA #", "COUNT", "FOM CODE",
        "DESCRIPTION OF FOM", "FOM TIME INTERCEPTED", "LINE #", "PRODUCT DETAILS", "POSSIBLE SOURCE - DEPARTMENT",
        "POSSIBLE SOURCE (SPECIFIC AREA)", "IMMEDIATE ACTION", "ROOT-CAUSE", "CORRECTIVE ACTION"}, MissingField.UseNull),
    NonEmpty = Table.SelectRows(Kept, each [DATE] <> null or [COUNT] <> null or [FOM CODE] <> null),
    // one spelling per detection point ("Juice line 9" / "Juice Line 9", "SUP Line 3 & 4", "Line Interceptions"...)
    PointMap = [LABELLINGLINE1 = "Labelling Line 1", LABELLINGLINE2 = "Labelling Line 2", LABELLINGLINE3 = "Labelling Line 3",
        LABELLINGLINE6 = "Labelling Line 6", LABELLINGLINE7 = "Labelling Line 7", LABELLINGLINE8 = "Labelling Line 8",
        LABELLINGLINE14 = "Labelling Line 14", #"SUPLINE3&4" = "SUP Line 3&4", SUPLINE5 = "SUP Line 5", SUPLINE6 = "SUP Line 6",
        JUICELINE9 = "Juice Line 9", PLASTICCUPLINE4 = "Plastic Cup Line 4", PLASTICCUPLINE5 = "Plastic Cup Line 5",
        CRUSHEDASEPTICLINE = "Crushed Aseptic Line", LPDASEPTICLINE = "LPD Aseptic Line", QAPRESHIPMENTSAMPLES = "QA Pre-Shipment Samples",
        QAMETALFRAGMENTSAMPLING = "QA Metal Fragment Sampling", LABAUDITSAMPLES = "Lab Audit Samples", QAGEMBAWALK = "QA Gemba Walk",
        LINEINTERCEPTION = "Line Interception", LINEINTERCEPTIONS = "Line Interception"],
    // detection groups = the rows of the team's Summary sheet ("By FOM Detection")
    GroupFn = (m as text, p as text, dept as text) as text =>
        if m = "XRAY" then (if Text.StartsWith(p, "LABELLING") then "X-Ray: Labelling" else if Text.StartsWith(p, "JUICE") then "X-Ray: J&D Juice" else "X-Ray: IPIC")
        else if m = "METALDETECTOR" then (if Text.Contains(p, "PLASTICCUP") then "Metal Detection: Plastic Cup" else if Text.Contains(p, "CRUSHED") then "Metal Detection: Aseptic Crushed"
            else if Text.StartsWith(p, "LPD") then "Metal Detection: LPD" else "Metal Detection: Other")
        else if m = "VISUALINSPECTION" then (if Text.Contains(p, "LABAUDIT") then "Visual Inspection: Lab Audits" else if Text.Contains(p, "PRESHIPMENT") then "Visual Inspection: Pre-Shipment"
            else if Text.Contains(p, "METALFRAGMENT") then "Visual Inspection: Metal Fragment" else "Visual Inspection: Line Interception")
        else "Not recorded",
    T = Table.FromRecords(Table.TransformRows(NonEmpty, (r) =>
        let
            cnt = r[COUNT],
            n = if cnt is number then cnt else try Number.From(Text.Trim(Text.From(cnt))) otherwise null,
            pt = CleanText(r[#"FOM DETECTION LINE/AREA #"]),
            meth = CleanText(r[FOM DETECTION]),
            dby = CleanText(r[DEPARTMENT])
        in [
            #"Excel Row" = r[EXCEL ROW],
            Date = ToDate(r[DATE]),
            #"Detected By" = if dby = null then "Not recorded" else dby,
            #"Detection Method" = if meth = null then "Not recorded" else meth,
            #"Detection Point" = if pt = null then "Not recorded" else Record.FieldOrDefault(PointMap, Key(pt), pt),
            #"Detection Group" = GroupFn(Key(meth), Key(pt), Key(dby)),
            // Count: 0/1/2 = line ran (pieces found), NR = not running
            #"Line Status" = if n <> null then "Running" else if Key(CleanText(cnt)) = "NR" then "Not running" else "Not recorded",
            #"FOM Count" = n,
            #"FOM Type" = CatFn(CleanText(r[FOM CODE])),
            #"FOM Description" = CleanText(r[DESCRIPTION OF FOM]),
            #"Time Intercepted" = CleanText(r[FOM TIME INTERCEPTED]),
            #"Line No" = CleanText(r[#"LINE #"]),
            #"Product Details" = CleanText(r[PRODUCT DETAILS]),
            #"Source Department" = DeptFn(CleanText(r[#"POSSIBLE SOURCE - DEPARTMENT"])),
            #"Source Area" = CleanText(r[#"POSSIBLE SOURCE (SPECIFIC AREA)"]),
            #"Immediate Action" = CleanText(r[IMMEDIATE ACTION]),
            #"Root Cause" = CleanText(r[#"ROOT-CAUSE"]),
            #"Corrective Action" = CleanText(r[CORRECTIVE ACTION])]),
        type table [#"Excel Row" = Int64.Type, Date = date, #"Detected By" = text, #"Detection Method" = text, #"Detection Point" = text,
            #"Detection Group" = text, #"Line Status" = text, #"FOM Count" = number, #"FOM Type" = text, #"FOM Description" = text,
            #"Time Intercepted" = text, #"Line No" = text, #"Product Details" = text, #"Source Department" = text, #"Source Area" = text,
            #"Immediate Action" = text, #"Root Cause" = text, #"Corrective Action" = text])
in
    T
'''

M_DATE = r'''
let
    AllDates = List.Buffer(List.RemoveNulls(GHP[Date] & LineFOM[Date])),
    MinDate = Date.StartOfMonth(List.Min(AllDates)),
    MaxData = List.Max(AllDates),
    MaxDate = Date.EndOfMonth(MaxData),
    CurFY = if Date.Month(MaxData) >= 5 then Date.Year(MaxData) + 1 else Date.Year(MaxData),
    Dates = List.Dates(MinDate, Duration.Days(MaxDate - MinDate) + 1, #duration(1, 0, 0, 0)),
    Base = Table.FromList(Dates, Splitter.SplitByNothing(), type table [Date = date]),
    AddYear = Table.AddColumn(Base, "Year", each Date.Year([Date]), Int64.Type),
    AddMonthNo = Table.AddColumn(AddYear, "Month No", each Date.Month([Date]), Int64.Type),
    AddFMonthNo = Table.AddColumn(AddMonthNo, "Fiscal Month No", each Number.Mod([Month No] + 7, 12) + 1, Int64.Type),
    AddMonth = Table.AddColumn(AddFMonthNo, "Month", each Date.ToText([Date], "MMM", "en-US"), type text),
    AddYearMonth = Table.AddColumn(AddMonth, "Year Month", each Date.ToText([Date], "MMM yyyy", "en-US"), type text),
    AddYearMonthKey = Table.AddColumn(AddYearMonth, "Year Month Key", each [Year] * 100 + [Month No], Int64.Type),
    AddFYNo = Table.AddColumn(AddYearMonthKey, "Fiscal Year No", each if [Month No] >= 5 then [Year] + 1 else [Year], Int64.Type),
    AddFY = Table.AddColumn(AddFYNo, "Fiscal Year", each "FY" & Text.End(Text.From([Fiscal Year No]), 2), type text),
    AddFYFlag = Table.AddColumn(AddFY, "FY Flag", each if [Fiscal Year No] = CurFY then "Current FY" else "Earlier FY", type text),
    AddWeekStart = Table.AddColumn(AddFYFlag, "Week Start", each Date.StartOfWeek([Date], Day.Monday), type date),
    AddWeekKey = Table.AddColumn(AddWeekStart, "Week Key", each Date.Year([Week Start]) * 10000 + Date.Month([Week Start]) * 100 + Date.Day([Week Start]), Int64.Type),
    AddDay = Table.AddColumn(AddWeekKey, "Day", each Date.ToText([Date], "ddd dd MMM yy", "en-US"), type text),
    // fiscal week: Mon-Sun, WK01 = the week containing 1 May; a week belongs to the FY of its Sunday
    AddFWYear = Table.AddColumn(AddDay, "Fiscal Week Year No", each let we = Date.AddDays([Week Start], 6) in if Date.Month(we) >= 5 then Date.Year(we) + 1 else Date.Year(we), Int64.Type),
    AddFWNo = Table.AddColumn(AddFWYear, "Fiscal Week No", each Number.IntegerDivide(Duration.Days([Week Start] - Date.StartOfWeek(#date([Fiscal Week Year No] - 1, 5, 1), Day.Monday)), 7) + 1, Int64.Type),
    AddFW = Table.AddColumn(AddFWNo, "Fiscal Week", each "WK" & Text.PadStart(Text.From([Fiscal Week No]), 2, "0") & " FY" & Text.End(Text.From([Fiscal Week Year No]), 2), type text),
    AddFWLabel = Table.AddColumn(AddFW, "Fiscal Week Label", each [Fiscal Week] & " (" & Date.ToText([Week Start], "d MMM", "en-US") & "–" & Date.ToText(Date.AddDays([Week Start], 6), "d MMM", "en-US") & ")", type text)
in
    AddFWLabel
'''

M_DEPT = r'''
let
    // one Department list (keys already standardised in GHP / LineFOM)
    All = List.Distinct(List.RemoveNulls(GHP[Department] & LineFOM[#"Source Department"])),
    T = Table.FromList(List.Sort(All), Splitter.SplitByNothing(), type table [Department = text])
in
    T
'''

M_CAT = r'''
let
    All = List.Distinct(List.RemoveNulls(GHP[#"FOM Category"] & LineFOM[#"FOM Type"])),
    T = Table.FromList(List.Sort(All), Splitter.SplitByNothing(), type table [#"FOM Category" = text])
in
    T
'''

M_MEASURES = r'''
let
    Source = #table(type table [Placeholder = text], {})
in
    Source
'''

# =====================================================================================  MEASURES
PCT, NUM, RATE = "0.0%", "#,0", "0.00"
F1, F2, F3, F4, F5 = "1 Base", "2 Dates & labels", "3 Topsheet", "4 Colours", "5 Details"
# ---- 1 Base (every page; follow slicers and clicked bars)
meas("GHP Findings", "COUNTROWS ( GHP )", NUM, F1, "GHP inspection findings (rows in the Daily FOM Inspection log)")
meas("GHP Corrected", "CALCULATE ( [GHP Findings], GHP[Status] = \"Corrected\" )", NUM, F1)
meas("GHP Uncorrected", "CALCULATE ( [GHP Findings], GHP[Status] = \"Uncorrected\" )", NUM, F1)
meas("GHP Not Stated", "CALCULATE ( [GHP Findings], GHP[Status] = \"Not stated\" )", NUM, F1, "Status blank, or Minor / Critical typed in the Status column")
meas("GHP % Corrected", "DIVIDE ( [GHP Corrected], [GHP Corrected] + [GHP Uncorrected] )", PCT, F1,
     "Corrected ÷ (Corrected + Uncorrected); findings with no status are left out")
meas("FOM Pieces", "VAR _n = SUM ( LineFOM[FOM Count] ) RETURN IF ( _n > 0, _n )", NUM, F1,
     "FOM pieces detected at the lines (sum of Count). Blank when none, so empty bars/rows disappear")
meas("FOM Incidents", "CALCULATE ( COUNTROWS ( LineFOM ), LineFOM[FOM Count] > 0 )", NUM, F1, "Log rows with at least one FOM piece")
meas("Running Line-Days", """
CALCULATE (
    COUNTROWS ( LineFOM ),
    LineFOM[Line Status] = "Running",
    REMOVEFILTERS ( Department ),
    REMOVEFILTERS ( 'FOM Category' )
)""", NUM, F1, "Line-days with a Count of 0/1/2 (NR = not running is excluded). Ignores the department / category slicers")
meas("FOM per 100 Line-Days", "DIVIDE ( COALESCE ( [FOM Pieces], 0 ) * 100, [Running Line-Days] )", RATE, F1,
     "FOM pieces per 100 running line-days")
for b in ["GHP Findings", "GHP Uncorrected", "FOM Pieces", "FOM Incidents"]:   # card versions: 0 instead of (Blank)
    meas(f"{b} (0)", f"COALESCE ( [{b}], 0 )", NUM, F1)

# ---- 2 Dates & labels
meas("Report Date", """
MAX (
    CALCULATE ( MAX ( GHP[Date] ), REMOVEFILTERS () ),
    CALCULATE ( MAX ( LineFOM[Date] ), REMOVEFILTERS () )
)""", "dd mmm yyyy", F2, "Latest date in either file - the Topsheet tiles run to this date")
meas("FY Start", "VAR _d = [Report Date] RETURN DATE ( YEAR ( _d ) - IF ( MONTH ( _d ) < 5, 1, 0 ), 5, 1 )", "dd mmm yyyy", F2, "1 May of the fiscal year")
meas("Month Start", "VAR _d = [Report Date] RETURN DATE ( YEAR ( _d ), MONTH ( _d ), 1 )", "dd mmm yyyy", F2)
meas("Report Week Start", "VAR _d = [Report Date] RETURN _d - WEEKDAY ( _d, 2 ) + 1", "dd mmm yyyy", F2, "Monday of the report week")
meas("Report Week Label", "LOOKUPVALUE ( 'Date'[Fiscal Week Label], 'Date'[Date], [Report Date] )", None, F2)
meas("Header Subtitle", """
"Data through " & FORMAT ( [Report Date], "ddd d mmm yyyy" ) & " · " & LOOKUPVALUE ( 'Date'[Fiscal Week], 'Date'[Date], [Report Date] )""", None, F2)
meas("YTD Label", """
"FY" & RIGHT ( YEAR ( [FY Start] ) + 1, 2 ) & " · " & FORMAT ( [FY Start], "d mmm" ) & " – " & FORMAT ( [Report Date], "d mmm yyyy" )""", None, F2)
meas("MTD Label", """FORMAT ( [Report Date], "mmmm yyyy" ) & " · to " & FORMAT ( [Report Date], "d mmm" )""", None, F2)
meas("Selection Label", """
VAR _s = MIN ( 'Date'[Date] )
VAR _e = MIN ( MAX ( 'Date'[Date] ), [Report Date] )
RETURN "Showing " & FORMAT ( _s, "d mmm" ) & " – " & FORMAT ( _e, "d mmm yyyy" )""", None, F2,
     "Dates the Monthly / Weekly tiles cover (all, or the clicked bar / slicer)")

# ---- 3 Topsheet: the only period measures. Pattern = base measure, Date filters replaced by the period window.
PER = {"YTD": ("[FY Start]", "[Report Date]"), "MTD": ("[Month Start]", "[Report Date]"), "WTD": ("[Report Week Start]", "[Report Date]"),
       "PM": ("EDATE ( [Month Start], -1 )", "[Month Start] - 1"), "PW": ("[Report Week Start] - 7", "[Report Week Start] - 1")}
def per(base, p, fmt=NUM, zero=True):
    s, e = PER[p]
    x = f"CALCULATE ( [{base}], REMOVEFILTERS ( 'Date' ), DATESBETWEEN ( 'Date'[Date], {s}, {e} ) )"
    meas(f"{base} {p}", f"COALESCE ( {x}, 0 )" if zero else x, fmt, F3)
for p in ["YTD", "MTD", "WTD", "PM", "PW"]:
    per("GHP Findings", p); per("FOM Pieces", p)
per("GHP Uncorrected", "YTD"); per("GHP Not Stated", "YTD"); per("FOM Incidents", "YTD"); per("Running Line-Days", "YTD")
per("GHP % Corrected", "YTD", PCT, zero=False); per("FOM per 100 Line-Days", "YTD", RATE); per("FOM per 100 Line-Days", "MTD", RATE)

def top_text(name, dim, col_, by, what):
    meas(name, f"""
VAR _t = TOPN ( 1, FILTER ( VALUES ( {dim}[{col_}] ), [{by}] > 0 ), [{by}], DESC )
RETURN IF ( ISEMPTY ( _t ), "None", CONCATENATEX ( _t, {dim}[{col_}] & " (" & FORMAT ( [{by}], "#,0" ) & ")", ", " ) )""", None, F3, f"{what} with the most, this FY to date")
top_text("Top GHP Category YTD", "'FOM Category'", "FOM Category", "GHP Findings YTD", "GHP FOM category")
top_text("Top GHP Department YTD", "Department", "Department", "GHP Findings YTD", "GHP department")
top_text("Top FOM Type YTD", "'FOM Category'", "FOM Category", "FOM Pieces YTD", "Line FOM type")
top_text("Top FOM Source YTD", "Department", "Department", "FOM Pieces YTD", "Possible source department")
top_text("Top FOM Detection YTD", "LineFOM", "Detection Group", "FOM Pieces YTD", "Detection point")
meas("GHP YTD Text", """FORMAT ( [GHP % Corrected YTD], "0.0%" ) & " corrected · " & [GHP Uncorrected YTD] & " uncorrected\"""", None, F3)
meas("GHP PM Text", """ "Last month (" & FORMAT ( EDATE ( [Month Start], -1 ), "mmm" ) & "): " & [GHP Findings PM] """.strip(), None, F3)
meas("GHP PW Text", """ "Last week: " & [GHP Findings PW] """.strip(), None, F3)
meas("FOM PM Text", """ "Last month (" & FORMAT ( EDATE ( [Month Start], -1 ), "mmm" ) & "): " & [FOM Pieces PM] """.strip(), None, F3)
meas("FOM PW Text", """ "Last week: " & [FOM Pieces PW] """.strip(), None, F3)
meas("FOM YTD Text", """[FOM Incidents YTD] & " incidents · " & FORMAT ( [Running Line-Days YTD], "#,0" ) & " running line-days\"""", None, F3)
meas("FOM Rate Text", """ "This month: " & FORMAT ( [FOM per 100 Line-Days MTD], "0.00" ) """.strip(), None, F3)
meas("Undated FOM Text", """
VAR _rows = CALCULATETABLE ( VALUES ( LineFOM[Excel Row] ), ISBLANK ( LineFOM[Date] ), LineFOM[FOM Count] > 0, REMOVEFILTERS ( 'Date' ) )
VAR _n = CALCULATE ( SUM ( LineFOM[FOM Count] ), ISBLANK ( LineFOM[Date] ), REMOVEFILTERS ( 'Date' ) )
RETURN
    IF ( _n > 0, "+" & _n & " piece(s) with no date – Excel row " & CONCATENATEX ( _rows, LineFOM[Excel Row], ", " ), [YTD Label] )""", None, F3,
     "FOM rows with no date cannot fall in a month or week: fix the date in Excel")

# ---- 4 Colours (hex text used by tiles)
RED_, GREEN_, AMBER_ = f'"{RED}"', f'"{GREEN}"', f'"{AMBER}"'
def fom_color(name, m): meas(name, f"IF ( COALESCE ( [{m}], 0 ) > 0, {RED_}, {GREEN_} )", None, F4, "Red when any FOM piece (target 0)")
def ghp_color(name, m): meas(name, f"VAR _p = [{m}] RETURN SWITCH ( TRUE (), ISBLANK ( _p ), \"{INK}\", _p >= 1, {GREEN_}, _p >= 0.95, {AMBER_}, {RED_} )",
                             None, F4, "Green 100%, amber 95–99.9%, red below 95%")
fom_color("FOM Color", "FOM Pieces"); fom_color("FOM Color YTD", "FOM Pieces YTD"); fom_color("FOM Color MTD", "FOM Pieces MTD"); fom_color("FOM Color WTD", "FOM Pieces WTD")
ghp_color("GHP Corrected Color", "GHP % Corrected"); ghp_color("GHP Corrected Color YTD", "GHP % Corrected YTD")
meas("Uncorrected Color", f"IF ( [GHP Uncorrected (0)] > 0, {RED_}, {GREEN_} )", None, F4)
meas("Uncorrected Color YTD", f"IF ( [GHP Uncorrected YTD] > 0, {RED_}, {GREEN_} )", None, F4)

# ---- 5 Details
meas("GHP Open Items", "CALCULATE ( [GHP Findings], GHP[Status] <> \"Corrected\" )", NUM, F5, "Uncorrected + not stated (rows to follow up)")

# =====================================================================================  TABLES
S_ = "string"
tables = [
    table("GHP", [col("Excel Row", "int64", desc="Row number in the Excel sheet - use it to find and fix the source row"), col("Sheet", S_),
                  col("Date", "dateTime"), col("Inspection", S_), col("Department", S_), col("Finding", S_), col("FOM Category", S_),
                  col("Status", S_), col("Status As Typed", S_), col("Time Corrected", S_), col("Remarks", S_)], M_GHP,
          extra={"description": "FY27 Daily FOM Inspection (GHP) - one row per finding"}),
    table("LineFOM", [col("Excel Row", "int64", desc="Row number in the Excel sheet"), col("Date", "dateTime"), col("Detected By", S_),
                      col("Detection Method", S_), col("Detection Point", S_), col("Detection Group", S_), col("Line Status", S_),
                      col("FOM Count", "double", fmt="#,0", summarize="sum"), col("FOM Type", S_), col("FOM Description", S_),
                      col("Time Intercepted", S_), col("Line No", S_), col("Product Details", S_), col("Source Department", S_),
                      col("Source Area", S_), col("Immediate Action", S_), col("Root Cause", S_), col("Corrective Action", S_)], M_LINE,
          extra={"description": "Line FOM Detection log - one row per line per day (+ extra interception rows)"}),
    table("Date", [
        col("Date", "dateTime", key=True), col("Year", "int64"), col("Month No", "int64", hidden=True), col("Fiscal Month No", "int64", hidden=True),
        col("Month", S_, sort_by="Fiscal Month No"), col("Year Month", S_, sort_by="Year Month Key"), col("Year Month Key", "int64", hidden=True),
        col("Fiscal Year No", "int64", hidden=True), col("Fiscal Year", S_, sort_by="Fiscal Year No"), col("FY Flag", S_),
        col("Week Start", "dateTime"), col("Week Key", "int64", hidden=True), col("Day", S_, sort_by="Date"),
        col("Fiscal Week Year No", "int64", hidden=True), col("Fiscal Week No", "int64", hidden=True),
        col("Fiscal Week", S_, sort_by="Week Key"), col("Fiscal Week Label", S_, sort_by="Week Key")], M_DATE, extra={"dataCategory": "Time"}),
    table("Department", [col("Department", S_)], M_DEPT, extra={"description": "Shared list: GHP Department + Line FOM possible source department"}),
    table("FOM Category", [col("FOM Category", S_)], M_CAT, extra={"description": "Shared list: GHP FOM category + Line FOM code"}),
    table(MT, [col("Placeholder", S_, hidden=True)], M_MEASURES),
]
tables[-1]["measures"] = finalize_measures()
relationships = [
    rel("GHP", "Date", "Date", "Date"), rel("LineFOM", "Date", "Date", "Date"),
    rel("GHP", "Department", "Department", "Department"), rel("LineFOM", "Source Department", "Department", "Department"),
    rel("GHP", "FOM Category", "FOM Category", "FOM Category"), rel("LineFOM", "FOM Type", "FOM Category", "FOM Category"),
]

# =====================================================================================  LAYOUT (16:9, 1280 x 720)
PW, PH = CONFIG["page_w"], CONFIG["page_h"]
M_, G = 12, 8
X0, FULL = M_, PW - 2 * M_            # 12, 1256
FY_, FH = 58, 50
Y0 = FY_ + FH + G                     # 116
YE = PH - M_                          # 708
HALF = (FULL - G) // 2                # 624
XR = X0 + HALF + G                    # right half x
FOMC = "#E65100"                      # Line FOM accent (deep orange), GHP accent = green

def F_FY(): return ([("Date", "Fiscal Year")], "Fiscal year", 120, {"sync": "FY"})
def F_MON(): return ([("Date", "Year Month")], "Month", 140, {"sync": "Month"})
def F_DEPT(): return ([("Department", "Department")], "Department (GHP + FOM source)", 210, {"sync": "Dept"})
def F_CAT(): return ([("FOM Category", "FOM Category")], "FOM category", 160, {"sync": "Cat"})

def eq_filter(ent, prop, val):
    return [{"name": hashlib.md5(f"eq{ent}{prop}{val}".encode()).hexdigest()[:20],
             "expression": {"Column": {"Expression": {"SourceRef": {"Entity": ent}}, "Property": prop}},
             "filter": {"Version": 2, "From": [{"Name": "d", "Entity": ent, "Type": 0}],
                        "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": prop}}],
                                                        "Values": [[S(val)["expr"]]]}}}]},
             "type": "Categorical", "howCreated": 1}]

def note(page, x, text):
    textbox(page, x + 4, FY_ + 4, PW - M_ - 6 - x - 4, FH - 8, [[(text, st(8, SUB))]])

def ren(*pairs): return {"columnProperties": {f"{MT}.{m}": {"displayName": d} for m, d in pairs}}

# ---------------------------------------------------------------- PAGE 1: TOPSHEET
P1 = "topsheet"
header(P1, "FOM MONITORING  |  TOPSHEET")
x = filter_bar(P1, FY_, [F_DEPT(), F_CAT()], FH)
note(P1, x, "Tiles: this FY to date, this month and this week, up to the latest date in either file (no date filter needed). "
            "Tables below: this FY by month. Department and category filter both GHP and Line FOM.")
TW = (FULL - 4 * G) // 5
def tiles_row(page, y, h, tiles):
    for i, (lab, v, vc_, l1, l1c, l2, acc) in enumerate(tiles):
        w = TW if i < 4 else FULL - 4 * (TW + G)
        kpi_tile(page, X0 + i * (TW + G), y, w, h, lab, v, vc_, l1, l1c, l2, accent=acc, value_size=20)
tiles_row(P1, Y0, 96, [
    ("GHP FINDINGS · FY TO DATE", "GHP Findings YTD", None, "GHP YTD Text", "GHP Corrected Color YTD", "YTD Label", GREEN),
    ("GHP FINDINGS · THIS MONTH", "GHP Findings MTD", None, "GHP PM Text", None, "MTD Label", GREEN),
    ("GHP FINDINGS · THIS WEEK", "GHP Findings WTD", None, "GHP PW Text", None, "Report Week Label", GREEN),
    ("GHP UNCORRECTED · FY TO DATE", "GHP Uncorrected YTD", "Uncorrected Color YTD", "GHP Not Stated YTD", None, "YTD Label", GREEN),
    ("GHP TOP CATEGORY · FY TO DATE", "Top GHP Category YTD", None, "Top GHP Department YTD", None, "YTD Label", GREEN)])
Y2 = Y0 + 96 + G
tiles_row(P1, Y2, 96, [
    ("LINE FOM PIECES · FY TO DATE", "FOM Pieces YTD", "FOM Color YTD", "FOM YTD Text", None, "Undated FOM Text", FOMC),
    ("LINE FOM PIECES · THIS MONTH", "FOM Pieces MTD", "FOM Color MTD", "FOM PM Text", None, "MTD Label", FOMC),
    ("LINE FOM PIECES · THIS WEEK", "FOM Pieces WTD", "FOM Color WTD", "FOM PW Text", None, "Report Week Label", FOMC),
    ("FOM PER 100 LINE-DAYS · FY TO DATE", "FOM per 100 Line-Days YTD", None, "FOM Rate Text", None, "YTD Label", FOMC),
    ("LINE FOM TOP TYPE · FY TO DATE", "Top FOM Type YTD", None, "Top FOM Source YTD", None, "Top FOM Detection YTD", FOMC)])
Y3 = Y2 + 96 + G
MW = (FULL - 2 * G) // 3
def matrix(page, x, y, w, h, rows, measure, title, sub):
    q = Q().add("Rows", *rows).add("Columns", "Date", "Month").m("Values", measure)
    o = table_style()
    o["rowHeaders"] = [{"properties": {"fontSize": N(9), "fontFamily": S(FONT), "fontColor": color(INK), "wordWrap": B(True)}}]
    o["subTotals"] = [{"properties": {"rowSubtotals": B(True), "columnSubtotals": B(True)}}]
    visual(page, "pivotTable", x, y, w, h, q, o, title=title, subtitle=sub, filters=eq_filter("Date", "FY Flag", "Current FY"))
matrix(P1, X0, Y3, MW, YE - Y3, ("FOM Category", "FOM Category"), "GHP Findings", "GHP FINDINGS BY FOM CATEGORY", "This FY · count of findings")
matrix(P1, X0 + MW + G, Y3, MW, YE - Y3, ("FOM Category", "FOM Category"), "FOM Pieces", "LINE FOM BY TYPE", "This FY · FOM pieces (sum of Count)")
matrix(P1, X0 + 2 * (MW + G), Y3, FULL - 2 * (MW + G), YE - Y3, ("LineFOM", "Detection Group"), "FOM Pieces", "LINE FOM BY DETECTION POINT",
       "This FY · FOM pieces · groups as in the team's Summary sheet")

# ---------------------------------------------------------------- PAGES 2/3: MONTHLY, WEEKLY (same layout, different axis)
def trend_page(page, title, axis_col, kind):
    header(page, title)
    items = [F_FY()] + ([F_MON()] if kind == "Weekly" else []) + [F_DEPT(), F_CAT()]
    x = filter_bar(page, FY_, items, FH)
    note(page, x, f"Click a {'month' if kind == 'Monthly' else 'week'} bar to filter the whole page (both sides); click it again to clear. "
                  "Left = GHP inspection findings · right = FOM detected at the lines.")
    tw = (HALF - 2 * G) // 3
    for i, (lab, v, vcol, acc) in enumerate([("GHP FINDINGS", "GHP Findings (0)", None, GREEN), ("GHP % CORRECTED", "GHP % Corrected", "GHP Corrected Color", GREEN),
                                             ("GHP UNCORRECTED", "GHP Uncorrected (0)", "Uncorrected Color", GREEN)]):
        kpi_tile(page, X0 + i * (tw + G), Y0, tw if i < 2 else HALF - 2 * (tw + G), 84, lab, v, vcol, "Selection Label", None, accent=acc, value_size=20)
    for i, (lab, v, vcol) in enumerate([("LINE FOM PIECES", "FOM Pieces (0)", "FOM Color"), ("FOM INCIDENTS", "FOM Incidents (0)", None),
                                        ("FOM PER 100 LINE-DAYS", "FOM per 100 Line-Days", None)]):
        kpi_tile(page, XR + i * (tw + G), Y0, tw if i < 2 else HALF - 2 * (tw + G), 84, lab, v, vcol, "Selection Label", None, accent=FOMC, value_size=20)
    R2 = Y0 + 84 + G; RH = 236
    per_ = "MONTH" if kind == "Monthly" else "WEEK"
    # GHP trend: findings (columns) + % corrected (line)
    q = Q().add("Category", "Date", axis_col).m("Y", "GHP Findings").m("Y2", "GHP % Corrected").sort("Date", axis_col)
    o = axis(start=0, sec={"show": True, "start": 0, "end": 1}, legend=True)
    series_color(o, "GHP Findings", GREEN); series_color(o, "GHP % Corrected", DARK)
    visual(page, "lineClusteredColumnComboChart", X0, R2, HALF, RH, q, o, title=f"GHP FINDINGS PER {per_}",
           subtitle="Columns = findings · line = % corrected (right axis) · click a bar to filter", extra=ren(("GHP Findings", "Findings"), ("GHP % Corrected", "% corrected")))
    # FOM trend: pieces (columns) + rate (line)
    q = Q().add("Category", "Date", axis_col).m("Y", "FOM Pieces").m("Y2", "FOM per 100 Line-Days").sort("Date", axis_col)
    o = axis(start=0, sec={"show": True, "start": 0}, legend=True)
    series_color(o, "FOM Pieces", RED); series_color(o, "FOM per 100 Line-Days", DARK)
    visual(page, "lineClusteredColumnComboChart", XR, R2, HALF, RH, q, o, title=f"LINE FOM DETECTED PER {per_}",
           subtitle="Columns = FOM pieces (target 0) · line = per 100 running line-days (right axis)", extra=ren(("FOM Pieces", "FOM pieces"), ("FOM per 100 Line-Days", "Per 100 line-days")))
    # breakdowns (Pareto-style: sorted, top 10)
    R3 = R2 + RH + G; H3 = YE - R3; BW = (HALF - G) // 2
    def bars(x, w, ent, prop, m_, title, sub, colr):
        q = Q().add("Category", ent, prop).m("Y", m_).sort(MT, m_, "m", desc=True)
        o = axis(legend=False); series_color(o, m_, colr)
        visual(page, "clusteredBarChart", x, R3, w, H3, q, o, title=title, subtitle=sub, filters=topn(ent, prop, m_, 10))
    bars(X0, BW, "FOM Category", "FOM Category", "GHP Findings", "GHP · BY FOM CATEGORY", "Top 10 · findings", GREEN)
    bars(X0 + BW + G, HALF - BW - G, "Department", "Department", "GHP Findings", "GHP · BY DEPARTMENT", "Top 10 · findings", GREEN)
    bars(XR, BW, "FOM Category", "FOM Category", "FOM Pieces", "LINE FOM · BY TYPE", "FOM pieces", RED)
    bars(XR + BW + G, HALF - BW - G, "Department", "Department", "FOM Pieces", "LINE FOM · BY POSSIBLE SOURCE", "FOM pieces · source department", RED)

P2, P3, P4 = "monthly", "weekly", "details"
trend_page(P2, "FOM MONITORING  |  MONTHLY", "Year Month", "Monthly")
trend_page(P3, "FOM MONITORING  |  WEEKLY", "Fiscal Week Label", "Weekly")

# ---------------------------------------------------------------- PAGE 4: DETAILS
header(P4, "FOM MONITORING  |  DETAILS")
x = filter_bar(P4, FY_, [F_FY(), F_MON(), F_DEPT(), F_CAT()], FH)
note(P4, x, "Excel Row = row in the source sheet, to find and fix an entry. Only rows with FOM pieces / open GHP items are listed in the first two tables.")
RH = 250
q = Q()
for p_ in ["Excel Row", "Date", "Detection Group", "Detection Point", "FOM Type", "FOM Description", "Source Department", "Source Area", "Root Cause", "Corrective Action"]:
    q.add("Values", "LineFOM", p_)
q.m("Values", "FOM Pieces").sort("LineFOM", "Date", desc=True)
visual(P4, "tableEx", X0, Y0, FULL, RH, q, table_style(), title="LINE FOM INCIDENTS (newest first)", extra=ren(("FOM Pieces", "Pieces")))
R2 = Y0 + RH + G
LW = 760
q = Q()
for p_ in ["Excel Row", "Date", "Inspection", "Department", "FOM Category", "Status", "Finding"]:
    q.add("Values", "GHP", p_)
q.m("Values", "GHP Findings").sort("GHP", "Date", desc=True)
visual(P4, "tableEx", X0, R2, LW, YE - R2, q, table_style(), title="GHP FINDINGS LOG (newest first)", extra=ren(("GHP Findings", "#")))
q = Q()
for p_ in ["Excel Row", "Date", "Department", "Status As Typed", "Remarks", "Finding"]:
    q.add("Values", "GHP", p_)
q.m("Values", "GHP Open Items").sort("GHP", "Date", desc=True)
visual(P4, "tableEx", X0 + LW + G, R2, FULL - LW - G, YE - R2, q, table_style(), title="GHP OPEN ITEMS (uncorrected / no status)",
       extra=ren(("GHP Open Items", "#")))

# =====================================================================================  WRITE
stats = write_project(args.out, args.name, tables, relationships,
                      [(P1, "Topsheet", PH), (P2, "Monthly", PH), (P3, "Weekly", PH), (P4, "Details", PH)],
                      [("GhpFilePath", "GhpWorkbook", args.ghp), ("LineFilePath", "LineWorkbook", args.line)],
                      args.logo, args.background or None)
print(stats)
