# =============================================
#   YOUR FIRST AI AGENT
#   Attendance Monitoring Agent
#   It checks every student's attendance
#   and tells you who needs attention
# =============================================

import mysql.connector

# --- STEP 1: Connect to your MySQL database ---
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="222",   # <-- change this
    database="gfm_platform"
)

cursor = conn.cursor()

print("=" * 50)
print("   ATTENDANCE MONITORING AGENT")
print("   Checking all students...")
print("=" * 50)

# --- STEP 2: Calculate attendance for each student ---
cursor.execute("""
    SELECT
        s.student_name,
        s.prn_number,
        s.parent_phone,
        COUNT(*) AS total_days,
        SUM(a.status = 'present') AS days_present,
        ROUND(100.0 * SUM(a.status = 'present') / COUNT(*), 1) AS attendance_pct
    FROM students s
    JOIN attendance a ON s.prn_number = a.prn_number
    GROUP BY s.prn_number, s.student_name, s.parent_phone
    ORDER BY attendance_pct ASC
""")

students = cursor.fetchall()

# --- STEP 3: Check each student and flag problems ---
print()
for name, prn, phone, total, present, pct in students:

    if pct < 60:
        icon   = "🔴 CRITICAL"
        action = f"Call parent NOW → {phone}"

    elif pct < 75:
        icon   = "🟡 WARNING "
        action = "Send reminder to student"

    else:
        icon   = "🟢 OK      "
        action = "No action needed"

    print(f"{icon} | {name:<18} | {pct}% | {action}")

# --- STEP 4: Print summary ---
critical = [s for s in students if s[5] < 60]
warning  = [s for s in students if 60 <= s[5] < 75]
ok       = [s for s in students if s[5] >= 75]

print()
print("=" * 50)
print(f"  SUMMARY")
print(f"  Total students  : {len(students)}")
print(f"  🔴 Critical     : {len(critical)}")
print(f"  🟡 Warning      : {len(warning)}")
print(f"  🟢 OK           : {len(ok)}")
print("=" * 50)

if critical:
    print()
    print("  ⚠️  These students need IMMEDIATE action:")
    for s in critical:
        print(f"     → {s[0]} ({s[5]}%) — parent: {s[2]}")

conn.close()
