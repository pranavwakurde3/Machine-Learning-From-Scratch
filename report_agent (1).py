# =============================================
#   AGENT 8 — REPORT GENERATOR
#   Automatically creates a PDF report
#   for the GFM with all student data
# =============================================

import mysql.connector
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from datetime import date

# --- Connect to database ---
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="YOUR_MYSQL_PASSWORD",   # <-- change this
    database="gfm_platform"
)
cursor = conn.cursor()

print("Generating GFM Report PDF...")

# --- Get all data ---
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

cursor.execute("SELECT prn_number, student_name FROM students ORDER BY prn_number")
students = cursor.fetchall()

# --- Calculate scores ---
results = []
for prn, name in students:
    att   = attendance.get(prn, 0)
    mrk   = marks.get(prn, 0)
    score = round((att * 0.40) + (mrk * 0.60), 1)
    fee   = fees.get(prn, {})
    pending = fee.get("due", 0) - fee.get("paid", 0)

    if score < 50:
        risk = "HIGH RISK"
    elif score < 70:
        risk = "MEDIUM"
    else:
        risk = "LOW RISK"

    results.append({
        "prn": prn, "name": name, "att": att,
        "mrk": mrk, "score": score, "risk": risk,
        "pending": pending
    })

results.sort(key=lambda x: x["score"])

# --- Create PDF ---
filename = f"GFM_Report_{date.today()}.pdf"
doc = SimpleDocTemplate(filename, pagesize=A4,
                        rightMargin=0.5*inch, leftMargin=0.5*inch,
                        topMargin=0.5*inch, bottomMargin=0.5*inch)

styles = getSampleStyleSheet()
content = []

# Title
title_style = ParagraphStyle('title', fontSize=18, fontName='Helvetica-Bold',
                              spaceAfter=6)
content.append(Paragraph("GFM Student Success Platform", title_style))

sub_style = ParagraphStyle('sub', fontSize=11, fontName='Helvetica',
                           spaceAfter=4, textColor=colors.grey)
content.append(Paragraph("Guardian Faculty: Mr. Aniket Magdum", sub_style))
content.append(Paragraph(f"Report Date: {date.today()}  |  Total Students: {len(students)}", sub_style))
content.append(Spacer(1, 0.2*inch))

# Summary table
high   = len([r for r in results if r["risk"] == "HIGH RISK"])
medium = len([r for r in results if r["risk"] == "MEDIUM"])
low    = len([r for r in results if r["risk"] == "LOW RISK"])

summary_data = [
    ["Total Students", "High Risk", "Medium Risk", "Low Risk"],
    [str(len(students)), str(high), str(medium), str(low)]
]
summary_table = Table(summary_data, colWidths=[1.5*inch]*4)
summary_table.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a1a2e')),
    ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
    ('FONTNAME',   (0,0), (-1,-1), 'Helvetica-Bold'),
    ('FONTSIZE',   (0,0), (-1,-1), 11),
    ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
    ('BACKGROUND', (0,1), (0,1),  colors.HexColor('#4a90d9')),
    ('BACKGROUND', (1,1), (1,1),  colors.HexColor('#e74c3c')),
    ('BACKGROUND', (2,1), (2,1),  colors.HexColor('#f39c12')),
    ('BACKGROUND', (3,1), (3,1),  colors.HexColor('#27ae60')),
    ('TEXTCOLOR',  (0,1), (-1,1), colors.white),
    ('FONTSIZE',   (0,1), (-1,1), 16),
    ('BOX',        (0,0), (-1,-1), 1, colors.white),
    ('INNERGRID',  (0,0), (-1,-1), 0.5, colors.white),
    ('TOPPADDING', (0,0), (-1,-1), 8),
    ('BOTTOMPADDING', (0,0), (-1,-1), 8),
]))
content.append(summary_table)
content.append(Spacer(1, 0.2*inch))

# Section title
section_style = ParagraphStyle('section', fontSize=13, fontName='Helvetica-Bold', spaceAfter=6)
content.append(Paragraph("Student-wise Report", section_style))

# Main table — build with row colors baked in
headers = [["PRN", "Student Name", "Attendance", "Marks", "Score", "Risk", "Fee Pending"]]
table_rows = []
row_bg_colors = []

for i, r in enumerate(results):
    row = [
        r["prn"], r["name"], f"{r['att']}%",
        f"{r['mrk']}%", f"{r['score']}/100",
        r["risk"], f"Rs.{r['pending']:,.0f}"
    ]
    table_rows.append(row)
    if r["risk"] == "HIGH RISK":
        row_bg_colors.append(colors.HexColor('#fdecea'))
    elif r["risk"] == "MEDIUM":
        row_bg_colors.append(colors.HexColor('#fff8e1'))
    else:
        row_bg_colors.append(colors.HexColor('#e8f5e9'))

table_data = headers + table_rows
main_table = Table(table_data, colWidths=[0.7*inch, 1.8*inch, 0.9*inch,
                                           0.7*inch, 0.8*inch, 1.0*inch, 1.0*inch])

table_style_cmds = [
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a1a2e')),
    ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
    ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
    ('FONTSIZE',   (0,0), (-1,-1), 9),
    ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
    ('ALIGN',      (1,0), (1,-1), 'LEFT'),
    ('BOX',        (0,0), (-1,-1), 0.5, colors.grey),
    ('INNERGRID',  (0,0), (-1,-1), 0.25, colors.lightgrey),
    ('TOPPADDING', (0,0), (-1,-1), 6),
    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
]

for i, bg in enumerate(row_bg_colors):
    table_style_cmds.append(('BACKGROUND', (0, i+1), (-1, i+1), bg))

main_table.setStyle(TableStyle(table_style_cmds))
content.append(main_table)
content.append(Spacer(1, 0.3*inch))

note_style = ParagraphStyle('note', fontSize=9, fontName='Helvetica', textColor=colors.grey)
content.append(Paragraph("* Score = Attendance (40%) + Academic Marks (60%)", note_style))
content.append(Paragraph("* High Risk: below 50  |  Medium: 50-70  |  Low Risk: above 70", note_style))

doc.build(content)
conn.close()

print(f"✅ PDF Report created: {filename}")
print(f"   Find it in the same folder where you ran this script.")
