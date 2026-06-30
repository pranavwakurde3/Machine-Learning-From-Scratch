# =============================================
#   WEEKLY SUMMARY EMAIL AGENT
#   Sends a summary email to GFM every Monday
#   Run manually: python email_agent.py
#   Or schedule it to run automatically
# =============================================

import mysql.connector
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ── Email Config ─────────────────────────────
SENDER_EMAIL    = "pranavwakurde3@gmail.com"
SENDER_PASSWORD = "gpbt kdkq byxm cghg"
GFM_EMAIL       = "pranavwakurde3@gmail.com"  # GFM receives the email

# ── Database Config ──────────────────────────
DB_PASSWORD = "222"   # <-- your MySQL password

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=DB_PASSWORD,
        database="gfm_platform"
    )

def get_student_summary():
    conn = get_connection()
    cursor = conn.cursor()

    # Try sheet_data first
    cursor.execute("SELECT COUNT(*) FROM sheet_data")
    count = cursor.fetchone()[0]

    if count > 0:
        cursor.execute("""
            SELECT prn_number, student_name,
                   attendance_pct, marks_pct,
                   ROUND((attendance_pct*0.40)+(marks_pct*0.60),1) AS score,
                   fee_pending
            FROM sheet_data ORDER BY score ASC
        """)
    else:
        cursor.execute("""
            SELECT s.prn_number, s.student_name,
                   ROUND(100.0*SUM(a.status='present')/COUNT(a.id),1) AS att,
                   ROUND(AVG(((m.test1+m.test2)/(m.max_marks*2))*100),1) AS mrk,
                   ROUND((ROUND(100.0*SUM(a.status='present')/COUNT(a.id),1)*0.40)+
                         (ROUND(AVG(((m.test1+m.test2)/(m.max_marks*2))*100),1)*0.60),1) AS score,
                   COALESCE(f.amount_due-f.amount_paid,0) AS pending
            FROM students s
            LEFT JOIN attendance a ON s.prn_number=a.prn_number
            LEFT JOIN marks m ON s.prn_number=m.prn_number
            LEFT JOIN fees f ON s.prn_number=f.prn_number
            GROUP BY s.prn_number, s.student_name
            ORDER BY score ASC
        """)

    students = cursor.fetchall()
    conn.close()
    return students

def build_email_html(students):
    now = datetime.now().strftime("%d %B %Y")
    high   = [s for s in students if s[4] < 50]
    medium = [s for s in students if 50 <= s[4] < 70]
    low    = [s for s in students if s[4] >= 70]
    fee_pending = [s for s in students if float(s[5]) > 0]

    # Build student rows
    rows = ""
    for s in students:
        prn, name, att, mrk, score, pending = s
        if score < 50:   color = "#fee2e2"; badge = "🔴 HIGH RISK"; badge_color = "#dc2626"
        elif score < 70: color = "#fef3c7"; badge = "🟡 MEDIUM";    badge_color = "#d97706"
        else:            color = "#f0fdf4"; badge = "🟢 LOW RISK";  badge_color = "#16a34a"

        rows += f"""
        <tr style="background:{color}">
          <td style="padding:10px 14px;font-size:13px;font-weight:600;color:#0f172a">{name}</td>
          <td style="padding:10px 14px;font-size:13px;color:#64748b">{prn}</td>
          <td style="padding:10px 14px;font-size:13px;font-weight:600;color:{'#dc2626' if float(att)<60 else '#16a34a'}">{att}%</td>
          <td style="padding:10px 14px;font-size:13px">{mrk}%</td>
          <td style="padding:10px 14px;font-size:14px;font-weight:800;color:#6366f1">{score}/100</td>
          <td style="padding:10px 14px"><span style="background:{badge_color};color:white;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600">{badge}</span></td>
          <td style="padding:10px 14px;font-size:13px;color:{'#dc2626' if float(pending)>0 else '#16a34a'}">{'₹{:,.0f}'.format(float(pending)) if float(pending)>0 else '✓ Paid'}</td>
        </tr>"""

    # Critical students list
    critical_list = ""
    for s in high:
        critical_list += f"""
        <div style="background:#fee2e2;border-left:4px solid #dc2626;padding:10px 14px;border-radius:0 8px 8px 0;margin-bottom:8px">
          <strong style="color:#dc2626">{s[1]}</strong>
          <span style="color:#64748b;font-size:12px"> — Attendance: {s[2]}% | Marks: {s[3]}% | Score: {s[4]}/100</span>
        </div>"""

    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:'Segoe UI',Arial,sans-serif;background:#f0f4ff;margin:0;padding:20px">
<div style="max-width:700px;margin:0 auto">

  <!-- HEADER -->
  <div style="background:linear-gradient(135deg,#4f46e5,#7c3aed,#a855f7);border-radius:16px;padding:30px;margin-bottom:20px;text-align:center">
    <div style="font-size:36px;margin-bottom:10px">⚡</div>
    <h1 style="color:#fff;margin:0;font-size:22px">MentorSphere Weekly Report</h1>
    <p style="color:rgba(255,255,255,0.85);margin:6px 0 0;font-size:14px">GFM: Mr. Aniket Magdum · {now}</p>
  </div>

  <!-- SUMMARY CARDS -->
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px">
    <div style="background:#fff;border-radius:12px;padding:16px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.06)">
      <div style="font-size:28px;font-weight:800;color:#6366f1">{len(students)}</div>
      <div style="font-size:12px;color:#64748b;margin-top:4px">Total Students</div>
    </div>
    <div style="background:#fff;border-radius:12px;padding:16px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.06)">
      <div style="font-size:28px;font-weight:800;color:#ef4444">{len(high)}</div>
      <div style="font-size:12px;color:#64748b;margin-top:4px">High Risk</div>
    </div>
    <div style="background:#fff;border-radius:12px;padding:16px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.06)">
      <div style="font-size:28px;font-weight:800;color:#22c55e">{len(low)}</div>
      <div style="font-size:12px;color:#64748b;margin-top:4px">Low Risk</div>
    </div>
    <div style="background:#fff;border-radius:12px;padding:16px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.06)">
      <div style="font-size:28px;font-weight:800;color:#f59e0b">{len(fee_pending)}</div>
      <div style="font-size:12px;color:#64748b;margin-top:4px">Fee Pending</div>
    </div>
  </div>

  <!-- CRITICAL STUDENTS -->
  {'<div style="background:#fff;border-radius:12px;padding:20px;margin-bottom:20px;box-shadow:0 2px 8px rgba(0,0,0,0.06)"><h3 style="color:#dc2626;margin:0 0 14px;font-size:15px">🚨 Students Requiring Immediate Action</h3>' + critical_list + '</div>' if high else ''}

  <!-- FULL TABLE -->
  <div style="background:#fff;border-radius:12px;overflow:hidden;margin-bottom:20px;box-shadow:0 2px 8px rgba(0,0,0,0.06)">
    <div style="padding:16px 20px;border-bottom:1px solid #f1f5f9">
      <h3 style="margin:0;font-size:15px;color:#0f172a">📋 Complete Student Report</h3>
    </div>
    <table style="width:100%;border-collapse:collapse">
      <thead>
        <tr style="background:#f8fafc">
          <th style="padding:11px 14px;text-align:left;font-size:11px;color:#94a3b8;letter-spacing:.6px;text-transform:uppercase;border-bottom:1px solid #f1f5f9">Name</th>
          <th style="padding:11px 14px;text-align:left;font-size:11px;color:#94a3b8;letter-spacing:.6px;text-transform:uppercase;border-bottom:1px solid #f1f5f9">PRN</th>
          <th style="padding:11px 14px;text-align:left;font-size:11px;color:#94a3b8;letter-spacing:.6px;text-transform:uppercase;border-bottom:1px solid #f1f5f9">Attendance</th>
          <th style="padding:11px 14px;text-align:left;font-size:11px;color:#94a3b8;letter-spacing:.6px;text-transform:uppercase;border-bottom:1px solid #f1f5f9">Marks</th>
          <th style="padding:11px 14px;text-align:left;font-size:11px;color:#94a3b8;letter-spacing:.6px;text-transform:uppercase;border-bottom:1px solid #f1f5f9">Score</th>
          <th style="padding:11px 14px;text-align:left;font-size:11px;color:#94a3b8;letter-spacing:.6px;text-transform:uppercase;border-bottom:1px solid #f1f5f9">Risk</th>
          <th style="padding:11px 14px;text-align:left;font-size:11px;color:#94a3b8;letter-spacing:.6px;text-transform:uppercase;border-bottom:1px solid #f1f5f9">Fee</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>

  <!-- FOOTER -->
  <div style="text-align:center;padding:16px;color:#94a3b8;font-size:12px">
    MentorSphere AI Platform · Auto-generated weekly report · {now}
  </div>

</div>
</body>
</html>"""
    return html

def send_email():
    print("=" * 50)
    print("  WEEKLY EMAIL AGENT — Sending Summary...")
    print("=" * 50)

    students = get_student_summary()
    html_content = build_email_html(students)
    now = datetime.now().strftime("%d %B %Y")

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"📊 MentorSphere Weekly Report — {now}"
    msg['From']    = SENDER_EMAIL
    msg['To']      = GFM_EMAIL

    msg.attach(MIMEText(html_content, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, GFM_EMAIL, msg.as_string())
        server.quit()
        print(f"✅ Weekly summary email sent to {GFM_EMAIL}!")
        print(f"   {len(students)} students included in report")
    except Exception as e:
        print(f"❌ Error sending email: {e}")

if __name__ == "__main__":
    send_email()
