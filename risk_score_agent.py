# =============================================
#   AGENT 6 — STUDENT RISK SCORE AGENT
#   Combines attendance + marks
#   Gives every student a score out of 100
#   Higher score = student is doing well
#   Lower score = student needs help
# =============================================

import mysql.connector

# --- Connect to database ---
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="222",   # <-- change this
    database="gfm_platform"
)

cursor = conn.cursor()

print("=" * 55)
print("   STUDENT RISK SCORE AGENT")
print("   Calculating score for every student...")
print("=" * 55)

# --- Get attendance % for each student ---
cursor.execute("""
    SELECT
        prn_number,
        ROUND(100.0 * SUM(status = 'present') / COUNT(*), 1) AS att_pct
    FROM attendance
    GROUP BY prn_number
""")
attendance = {row[0]: row[1] for row in cursor.fetchall()}

# --- Get average marks % for each student ---
cursor.execute("""
    SELECT
        prn_number,
        ROUND(AVG(((test1 + test2) / (max_marks * 2)) * 100), 1) AS marks_pct
    FROM marks
    GROUP BY prn_number
""")
marks = {row[0]: row[1] for row in cursor.fetchall()}

# --- Get all students ---
cursor.execute("SELECT prn_number, student_name FROM students")
students = cursor.fetchall()

# --- Calculate Risk Score ---
# Formula:
#   Attendance score = 40% of total
#   Marks score      = 60% of total
#   Final score      = out of 100

print()
print(f"  {'Student':<20} {'Attend':>7}  {'Marks':>6}  {'Score':>6}  Risk Level")
print("  " + "-" * 53)

results = []

for prn, name in students:
    att_pct   = attendance.get(prn, 0)
    marks_pct = marks.get(prn, 0)

    # Calculate final score
    score = round((att_pct * 0.40) + (marks_pct * 0.60), 1)

    # Decide risk level
    if score < 50:
        risk = "HIGH RISK  "
        icon = "🔴"
    elif score < 70:
        risk = "MEDIUM RISK"
        icon = "🟡"
    else:
        risk = "LOW RISK   "
        icon = "🟢"

    results.append((score, name, prn, att_pct, marks_pct, risk, icon))

# Sort by score — lowest first (most at risk on top)
results.sort(key=lambda x: x[0])

for score, name, prn, att, mrk, risk, icon in results:
    print(f"  {icon} {name:<20} {att:>6}%  {mrk:>5}%  {score:>5}/100  {risk}")

# --- Summary ---
high   = [r for r in results if r[0] < 50]
medium = [r for r in results if 50 <= r[0] < 70]
low    = [r for r in results if r[0] >= 70]

print()
print("=" * 55)
print("  SUMMARY")
print(f"  Total students   : {len(results)}")
print(f"  🔴 High Risk     : {len(high)}")
print(f"  🟡 Medium Risk   : {len(medium)}")
print(f"  🟢 Low Risk      : {len(low)}")
avg = round(sum(r[0] for r in results) / len(results), 1)
print(f"  Class Average    : {avg}/100")
print("=" * 55)

if high:
    print()
    print("  ⚠️  HIGH RISK students — GFM must act now:")
    for r in high:
        print(f"     → {r[1]} (Score: {r[0]}/100 | Attendance: {r[3]}% | Marks: {r[4]}%)")

conn.close()
