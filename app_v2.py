# =============================================
#   GFM DASHBOARD - WEBPAGE
#   Now reads from sheet_data table
#   (synced from Google Sheets)
#   Opens at: http://localhost:5000
# =============================================

from flask import Flask, render_template
import mysql.connector

app = Flask(__name__)

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="YOUR_MYSQL_PASSWORD",  # <-- change this
        database="gfm_platform"
    )

def get_all_data():
    conn = get_connection()
    cursor = conn.cursor()

    # Read from sheet_data table (synced from Google Sheets)
    cursor.execute("""
        SELECT prn_number, student_name, parent_phone,
               attendance_pct, marks_pct, fee_pending, career_progress
        FROM sheet_data
        ORDER BY prn_number
    """)
    rows = cursor.fetchall()

    data = []
    for prn, name, phone, att, mrk, pending, career in rows:
        att   = float(att)
        mrk   = float(mrk)
        pending = float(pending)
        career  = float(career)

        score = round((att * 0.40) + (mrk * 0.60), 1)

        if score < 50:
            risk = "HIGH RISK"
            risk_class = "high"
        elif score < 70:
            risk = "MEDIUM"
            risk_class = "medium"
        else:
            risk = "LOW RISK"
            risk_class = "low"

        if att < 60:
            att_class = "high"
        elif att < 75:
            att_class = "medium"
        else:
            att_class = "low"

        data.append({
            "prn": prn, "name": name, "phone": phone,
            "att": att, "att_class": att_class,
            "mrk": mrk, "score": score,
            "risk": risk, "risk_class": risk_class,
            "pending": pending,
            "career_goal": "—",
            "career_avg": career,
            "badges": 1 if career >= 70 else 0
        })

    data.sort(key=lambda x: x["score"])

    summary = {
        "total": len(data),
        "high":   len([d for d in data if d["risk_class"] == "high"]),
        "medium": len([d for d in data if d["risk_class"] == "medium"]),
        "low":    len([d for d in data if d["risk_class"] == "low"]),
        "fee_pending": len([d for d in data if d["pending"] > 0]),
        "att_critical": len([d for d in data if d["att"] < 60]),
    }

    conn.close()
    return data, summary

@app.route("/")
def dashboard():
    data, summary = get_all_data()
    return render_template("dashboard.html", students=data, summary=summary)

if __name__ == "__main__":
    print("=" * 50)
    print("  GFM Dashboard starting...")
    print("  Data source: Google Sheet (synced)")
    print("  Open your browser and go to:")
    print("  http://localhost:5000")
    print("=" * 50)
    app.run(debug=True)
