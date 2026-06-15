# =============================================
#   MASTER ORCHESTRATOR — FINAL VERSION
#   Runs ALL 7 agents with one command
#   Agent 4  — Attendance
#   Agent 3  — Academic Marks
#   Agent 10 — Fee Monitoring
#   Agent 6  — Risk Score
#   Agent 9  — Career Progress
#   Agent 8  — PDF Report
# =============================================

import mysql.connector
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from datetime import date

# --- Connect ---
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="YOUR_MYSQL_PASSWORD",   # <-- change this
    database="gfm_platform"
)
cursor = conn.cursor()

# ── Fetch all data once ──────────────────────
cursor.execute("""
    SELECT prn_number,
           ROUND(100.0 * SUM(status='present') / COUNT(*), 1)
    FROM attendance GROUP BY prn_number
""")
attendance = {r[0]: float(r[1]) for r in cursor.fetchall()}

cursor.execute("""
    SELECT prn_number,
           ROUND(AVG(((test1+test2)/(max_marks*2))*100), 1)
    FROM marks GROUP BY prn_number
""")
marks = {r[0]: float(r[1]) for r in cursor.fetchall()}

cursor.execute("SELECT prn_number, amount_due, amount_paid, status FROM fees")
fees = {r[0]: {"due": float(r[1]), "paid": float(r[2]), "status": r[3]}
        for r in cursor.fetchall()}

cursor.execute("""
    SELECT prn_number,
           career_goal,
           ROUND(AVG(completion_pct), 1) AS avg_pct,
           SUM(badge_earned) AS badges
    FROM career_progress
    GROUP BY prn_number, career_goal
""")
career = {r[0]: {"goal": r[1], "avg": float(r[2]), "badges": r[3]}
          for r in cursor.fetchall()}

cursor.execute("SELECT prn_number, student_name, parent_phone FROM students ORDER BY prn_number")
students = cursor.fetchall()

# ── HEADER ───────────────────────────────────
print()
print("🚀 " * 25)
print()
print("   MASTER ORCHESTRATOR — COMPLETE DAILY REPORT")
print(f"   GFM: Mr. Aniket Magdum  |  Date: {date.today()}")
print(f"   Total Students: {len(students)}")
print()
print("🚀 " * 25)

# ── AGENT 4: ATTENDANCE ──────────────────────
print()
print("=" * 65)
print("  [AGENT 4] ATTENDANCE MONITORING")
print("=" * 65)
for prn, name, phone in students:
    pct = attendance.get(prn, 0)
    if pct < 60:
        print(f"  🔴 {name:<22} {pct}%  → Call parent: {phone}")
    elif pct < 75:
        print(f"  🟡 {name:<22} {pct}%  → Send reminder")
    else:
        print(f"  🟢 {name:<22} {pct}%  → OK")

# ── AGENT 3: MARKS ───────────────────────────
print()
print("=" * 65)
print("  [AGENT 3] ACADEMIC MONITORING")
print("=" * 65)
for prn, name, phone in students:
    pct = marks.get(prn, 0)
    if pct < 40:
        print(f"  🔴 {name:<22} {pct}%  → Needs coaching")
    elif pct < 60:
        print(f"  🟡 {name:<22} {pct}%  → At risk")
    else:
        print(f"  🟢 {name:<22} {pct}%  → Good")

# ── AGENT 10: FEES ───────────────────────────
print()
print("=" * 65)
print("  [AGENT 10] FEE MONITORING")
print("=" * 65)
for prn, name, phone in students:
    f = fees.get(prn, {})
    if not f:
        continue
    pending = f["due"] - f["paid"]
    if f["status"] == "paid":
        print(f"  🟢 {name:<22} Paid in full → OK")
    elif f["paid"] == 0:
        print(f"  🔴 {name:<22} Rs.{pending:,.0f} pending → Call: {phone}")
    else:
        print(f"  🟡 {name:<22} Rs.{pending:,.0f} pending → Reminder")

# ── AGENT 9: CAREER ──────────────────────────
print()
print("=" * 65)
print("  [AGENT 9] CAREER PROGRESS")
print("=" * 65)
for prn, name, phone in students:
    c = career.get(prn, {})
    if not c:
        continue
    avg = c["avg"]
    if avg >= 70:
        print(f"  🟢 {name:<22} {c['goal']:<22} {avg}% | Badges: {c['badges']}")
    elif avg >= 40:
        print(f"  🟡 {name:<22} {c['goal']:<22} {avg}% | Needs push")
    else:
        print(f"  🔴 {name:<22} {c['goal']:<22} {avg}% | Falling behind")

# ── AGENT 6: RISK SCORE ──────────────────────
print()
print("=" * 65)
print("  [AGENT 6] STUDENT SUCCESS SCORES")
print("=" * 65)
results = []
for prn, name, phone in students:
    att   = attendance.get(prn, 0)
    mrk   = marks.get(prn, 0)
    score = round((att * 0.40) + (mrk * 0.60), 1)
    results.append((score, name, prn, phone))

results.sort(key=lambda x: x[0])
print(f"\n  {'Student':<22} {'Score':>7}  Risk")
print("  " + "-" * 40)
for score, name, prn, phone in results:
    if score < 50:
        print(f"  🔴 {name:<22} {score:>5}/100  HIGH RISK")
    elif score < 70:
        print(f"  🟡 {name:<22} {score:>5}/100  MEDIUM RISK")
    else:
        print(f"  🟢 {name:<22} {score:>5}/100  LOW RISK")

# ── AGENT 8: PDF REPORT ──────────────────────
print()
print("=" * 65)
print("  [AGENT 8] GENERATING PDF REPORT...")
print("=" * 65)

filename = f"GFM_Report_{date.today()}.pdf"
doc = SimpleDocTemplate(filename, pagesize=A4,
                        rightMargin=0.5*inch, leftMargin=0.5*inch,
                        topMargin=0.5*inch, bottomMargin=0.5*inch)
content = []

title_style = ParagraphStyle('t', fontSize=16, fontName='Helvetica-Bold', spaceAfter=4)
sub_style   = ParagraphStyle('s', fontSize=10, fontName='Helvetica', spaceAfter=4, textColor=colors.grey)
content.append(Paragraph("GFM Student Success Platform — Daily Report", title_style))
content.append(Paragraph(f"GFM: Mr. Aniket Magdum  |  Date: {date.today()}  |  Students: {len(students)}", sub_style))
content.append(Spacer(1, 0.15*inch))

high   = len([r for r in results if r[0] < 50])
medium = len([r for r in results if 50 <= r[0] < 70])
low    = len([r for r in results if r[0] >= 70])

sum_data = [["Total","High Risk","Medium","Low Risk"],
            [str(len(students)), str(high), str(medium), str(low)]]
sum_tbl = Table(sum_data, colWidths=[1.4*inch]*4)
sum_tbl.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1a1a2e')),
    ('TEXTCOLOR', (0,0),(-1,0),colors.white),
    ('FONTNAME',  (0,0),(-1,-1),'Helvetica-Bold'),
    ('FONTSIZE',  (0,0),(-1,-1),10),
    ('ALIGN',     (0,0),(-1,-1),'CENTER'),
    ('BACKGROUND',(1,1),(1,1),colors.HexColor('#e74c3c')),
    ('BACKGROUND',(2,1),(2,1),colors.HexColor('#f39c12')),
    ('BACKGROUND',(3,1),(3,1),colors.HexColor('#27ae60')),
    ('BACKGROUND',(0,1),(0,1),colors.HexColor('#4a90d9')),
    ('TEXTCOLOR', (0,1),(-1,1),colors.white),
    ('FONTSIZE',  (0,1),(-1,1),14),
    ('TOPPADDING',(0,0),(-1,-1),6),
    ('BOTTOMPADDING',(0,0),(-1,-1),6),
    ('BOX',(0,0),(-1,-1),1,colors.white),
    ('INNERGRID',(0,0),(-1,-1),0.5,colors.white),
]))
content.append(sum_tbl)
content.append(Spacer(1, 0.15*inch))

sec_style = ParagraphStyle('sec', fontSize=12, fontName='Helvetica-Bold', spaceAfter=4)
content.append(Paragraph("Student Report", sec_style))

headers = [["PRN","Name","Attend","Marks","Score","Risk","Fee Pending","Career"]]
rows_data = []
row_colors = []
for score, name, prn, phone in results:
    f = fees.get(prn, {})
    pending = f.get("due", 0) - f.get("paid", 0)
    c = career.get(prn, {})
    risk = "HIGH" if score < 50 else ("MEDIUM" if score < 70 else "LOW")
    rows_data.append([
        prn, name,
        f"{attendance.get(prn,0)}%",
        f"{marks.get(prn,0)}%",
        f"{score}/100",
        risk,
        f"Rs.{pending:,.0f}",
        f"{c.get('avg',0)}%"
    ])
    if score < 50:
        row_colors.append(colors.HexColor('#fdecea'))
    elif score < 70:
        row_colors.append(colors.HexColor('#fff8e1'))
    else:
        row_colors.append(colors.HexColor('#e8f5e9'))

tbl = Table(headers + rows_data,
            colWidths=[0.65*inch,1.6*inch,0.65*inch,0.6*inch,0.7*inch,0.6*inch,0.9*inch,0.65*inch])
cmds = [
    ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1a1a2e')),
    ('TEXTCOLOR', (0,0),(-1,0),colors.white),
    ('FONTNAME',  (0,0),(-1,0),'Helvetica-Bold'),
    ('FONTSIZE',  (0,0),(-1,-1),8),
    ('ALIGN',     (0,0),(-1,-1),'CENTER'),
    ('ALIGN',     (1,0),(1,-1),'LEFT'),
    ('BOX',       (0,0),(-1,-1),0.5,colors.grey),
    ('INNERGRID', (0,0),(-1,-1),0.25,colors.lightgrey),
    ('TOPPADDING',(0,0),(-1,-1),5),
    ('BOTTOMPADDING',(0,0),(-1,-1),5),
]
for i, bg in enumerate(row_colors):
    cmds.append(('BACKGROUND',(0,i+1),(-1,i+1),bg))
tbl.setStyle(TableStyle(cmds))
content.append(tbl)

doc.build(content)
print(f"  ✅ PDF saved: {filename}")

# ── FINAL SUMMARY ────────────────────────────
att_critical  = [s for s in students if attendance.get(s[0], 0) < 60]
marks_failing = [s for s in students if marks.get(s[0], 0) < 40]
fee_pending   = [s for s in students if fees.get(s[0], {}).get("status") != "paid"]
career_behind = [s for s in students if career.get(s[0], {}).get("avg", 100) < 40]
high_risk     = [r for r in results if r[0] < 50]

print()
print("=" * 65)
print("  MASTER SUMMARY — ACTION REQUIRED TODAY")
print("=" * 65)
print(f"  Total students monitored  : {len(students)}")
print(f"  🔴 Attendance critical    : {len(att_critical)}")
print(f"  🔴 Academically failing   : {len(marks_failing)}")
print(f"  🔴 Fees not paid          : {len(fee_pending)}")
print(f"  🔴 Career falling behind  : {len(career_behind)}")
print(f"  🔴 High risk overall      : {len(high_risk)}")
print()
if high_risk:
    print("  ⚠️  TOP PRIORITY STUDENTS:")
    for score, name, prn, phone in high_risk:
        print(f"     → {name} — Score: {score}/100 | Parent: {phone}")
print()
print("=" * 65)
print("  ✅ All 7 agents completed successfully!")
print("=" * 65)

conn.close()
