# FOM Monitoring Dashboard (Power BI) — v1.0

Combines two FY27 files from SharePoint (BugoQA-QRM › GHP › FOM Monitoring › FY'27 › FOM FY27):

| Source | File | What is read |
|---|---|---|
| GHP | `FY27 Daily FOM Inspection.xlsx` | every sheet whose header row has **Finding** and **FOM CATEGORY** |
| Line FOM | `Line FOM Detection - Overall Dashboard.xlsx` | sheet **Phyiscal Hazard - FOM** (Sheet3 and Summary are ignored) |

## Pages (16:9)
| Page | What it shows |
|---|---|
| **Topsheet** | 10 tiles: GHP findings (FY to date / this month / this week, uncorrected, top category) and Line FOM pieces (FY to date / month / week, rate per 100 running line-days, top type, source and detection point). Three month-by-month tables (this FY), replacing the hand-typed Summary sheet. |
| **Monthly** | GHP on the left, Line FOM on the right. Tiles, a bar per month (click it to filter the page) and top-10 breakdowns by category, department, FOM type and possible source. |
| **Weekly** | The same layout by fiscal week (`WK30 FY27 (16 Nov–22 Nov)`), with a Month slicer. |
| **Details** | The Line FOM incident log (with root cause and corrective action), the GHP findings log and the GHP open items. Excel Row = the row to fix in Excel. |

## Rules
- **Fiscal year** starts on 1 May. **Weeks** run Monday–Sunday; WK01 is the week containing 1 May.
- **Topsheet** tiles run up to the latest date in either file. No date to pick and no editing needed for a new month or FY.
- **GHP % corrected** = Corrected ÷ (Corrected + Uncorrected). Findings with a blank status, or "Minor"/"Critical" typed in the Status column, count as **Not stated** and are left out. Colours: green 100%, amber 95–99.9%, red below 95%.
- **Line FOM pieces** = sum of Count. An **incident** is a row with Count ≥ 1. **Running line-days** are rows with Count 0/1/2. NR (not running) is excluded.
  - **FOM per 100 line-days** = pieces × 100 ÷ running line-days. The denominator ignores the Department and Category slicers.
  - Target 0: the value is red when any piece was found.
- **Department** is one list for both files. The GHP Department and the Line FOM "Possible Source – Department" map to the same names:
  - `Prep - PT` → Prep PT
  - `SPD-Cookroom` → Cookroom
  - `SPD-Crushed` → Crush
  - `J&D` → JnD/FDM
  - `Maintenance - Prep` → Prep Mtce
  - `FPD/ IPIC` → FPD/IPIC
- **FOM category** is one list for both files: `Others` → Other, `Paint Flakes` → Paint Flake.
- **Detection point groups** follow your Summary sheet: X-Ray Labelling / IPIC / J&D Juice, Metal Detection Plastic Cup / Aseptic Crushed / LPD, and Visual Inspection Lab Audits / Pre-Shipment / Metal Fragment / Line Interception.
  - The group is decided by the FOM Detection method + line. For example, a *Visual Inspection* at SUP Line 3&4 counts as **Visual Inspection: Line Interception**.

## Data cleaning (Power Query)
- Excel error cells (`#VALUE!`, `#N/A`) load as blank, so they can't stop the refresh.
- Dates typed as text (`15/10/2026`, read as dd/mm/yyyy) are converted to real dates. In the export there are 6 of them, all in October.
- Spellings are merged: `Juice line 9`/`Juice Line 9`, `SUP Line 3 & 4`, `plastic cup line 4`, `Line Interception(s)`, and `Visual Inspection` with a trailing space.
- Empty rows and the dropdown-list columns are dropped.

## Expected values after the first refresh (files as of 18 Nov 2026)
**GHP**
| Tile | Value |
|---|---|
| Findings FY to date | **1,188** |
| % corrected | **98.6%** (1,156 corrected, 17 uncorrected, 15 not stated) |
| This month (Nov, to 18 Nov) | **61** (Oct: **160**) |
| This week (WK30, 16–18 Nov) | **4** (last week: **34**) |
| Top category | **Insect (313)** |
| Top department | **Prep PT (261)** |

**Line FOM**
| Tile | Value |
|---|---|
| Pieces FY to date | **25** (23 incidents, 1,706 running line-days), plus **1** undated piece at Excel row 1626 |
| This month | **3** (Oct: **10**) |
| This week | **1** (last week: **0**) |
| Per 100 line-days | FY to date **1.47**, this month **1.52** |
| Top type | **Metal (13)** |
| Top source | **TPD (9)** |
| Top detection point | **Visual Inspection: Lab Audits (7)** and **Visual Inspection: Line Interception (7)** (tie) |

Line FOM pieces by month: Jul 7 · Aug 4 · Sep 1 · Oct 10 · Nov 3.

Run `python -I fom_expected_values.py <GHP file> <Line FOM file>` to recompute these from new files.

## Open it (first time)
1. Right-click the zip → **Extract All…** → choose a short folder such as `C:\PowerBI`. Do **not** open the `.pbip` from inside the zip.
2. In the extracted folder, double-click **FOM Dashboard.pbip**.
3. Click **Refresh**. When asked, choose **Organizational account → Sign in** with your Del Monte account.
   - Set the level to `https://delmontephinc.sharepoint.com/sites/BugoQA-QRM`, then click **Connect**.
   - If a privacy prompt appears, choose **Organizational** for both files.
4. If asked to *"Upgrade to TMDL"*, click **Don't upgrade**.
5. To share it as one file: **File → Save as → Power BI file (.pbix)**.

**If a file name or folder changes:** open **Home → Transform data → Edit parameters** and paste the new link into **GhpFilePath** or **LineFilePath**.
- Get the link in Excel desktop: **File → Info → Copy path**, and remove `?web=1`.
- Don't use a "Share" link.

**If the load fails:** every table will say "cancelled by an error in loading a previous table". Scroll to the one table with a *different* message and send a screenshot of it.

## Rebuild from code
```bash
python build_fom_dashboard.py --out FOM_Dashboard                  # default = the two SharePoint links
python validate_pbip.py FOM_Dashboard
```
`pbip_lib.py` is the Cannery QA toolkit, extended to read more than one source file.
