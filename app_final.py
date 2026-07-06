# =============================================
#   MENTORSPHERE - Complete Platform
#   Login + GFM Dashboard + Student Dashboard
#   + AI Report with Ollama
#   Run: python app.py
#   Open: http://localhost:5000
# =============================================

from flask import Flask, render_template, request, redirect, session, jsonify
import mysql.connector
import pandas as pd
import ollama

app = Flask(__name__)
app.secret_key = "mentorsphere_secret_key_2026"

DB_PASSWORD = "222"   # <-- your MySQL password

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=DB_PASSWORD,
        database="gfm_platform"
    )

# =============================================
#   LOGIN / LOGOUT
# =============================================

@app.route("/")
def home():
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", error=None)
    role     = request.form.get("role")
    username = request.form.get("username").strip()
    password = request.form.get("password").strip()
    conn = get_connection()
    cursor = conn.cursor()
    if role == "gfm":
        cursor.execute("SELECT gfm_id, full_name FROM gfm_login WHERE username=%s AND password=%s", (username, password))
        result = cursor.fetchone()
        if result:
            session["role"] = "gfm"
            session["gfm_id"] = result[0]
            session["user_name"] = result[1]
            conn.close()
            return redirect("/gfm/dashboard")
        conn.close()
        return render_template("login.html", error="Invalid username or password")
    else:
        cursor.execute("""
            SELECT sl.prn_number, s.student_name FROM student_login sl
            JOIN students s ON sl.prn_number = s.prn_number
            WHERE sl.prn_number=%s AND sl.password=%s
        """, (username, password))
        result = cursor.fetchone()
        if result:
            session["role"] = "student"
            session["prn"] = result[0]
            session["user_name"] = result[1]
            conn.close()
            return redirect("/student/dashboard")
        conn.close()
        return render_template("login.html", error="Invalid PRN or password")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

def require_login(role_needed):
    return session.get("role") == role_needed

# =============================================
#   SHARED DATA
# =============================================

def get_all_students_data():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT prn_number, ROUND(100.0*SUM(status='present')/COUNT(*),1) FROM attendance GROUP BY prn_number")
    attendance = {r[0]: float(r[1]) for r in cursor.fetchall()}
    cursor.execute("SELECT prn_number, ROUND(AVG(((test1+test2)/(max_marks*2))*100),1) FROM marks GROUP BY prn_number")
    marks = {r[0]: float(r[1]) for r in cursor.fetchall()}
    cursor.execute("SELECT prn_number, amount_due, amount_paid, status FROM fees")
    fees = {r[0]: {"due": float(r[1]), "paid": float(r[2]), "status": r[3]} for r in cursor.fetchall()}
    cursor.execute("SELECT prn_number, career_goal, ROUND(AVG(completion_pct),1), SUM(badge_earned) FROM career_progress GROUP BY prn_number, career_goal")
    career = {r[0]: {"goal": r[1], "avg": float(r[2]), "badges": r[3]} for r in cursor.fetchall()}
    cursor.execute("SELECT prn_number, student_name, parent_phone FROM students ORDER BY prn_number")
    students = cursor.fetchall()
    data = []
    for prn, name, phone in students:
        att = attendance.get(prn, 0)
        mrk = marks.get(prn, 0)
        score = round((att*0.40)+(mrk*0.60), 1)
        fee = fees.get(prn, {})
        pending = fee.get("due", 0) - fee.get("paid", 0)
        c = career.get(prn, {})
        risk_class = "high" if score<50 else ("medium" if score<70 else "low")
        risk = "HIGH RISK" if score<50 else ("MEDIUM" if score<70 else "LOW RISK")
        att_class = "high" if att<60 else ("medium" if att<75 else "low")
        data.append({
            "prn": prn, "name": name, "phone": phone,
            "att": att, "att_class": att_class, "mrk": mrk,
            "score": score, "risk": risk, "risk_class": risk_class,
            "pending": pending, "fee_status": fee.get("status", ""),
            "career_goal": c.get("goal", "—"), "career_avg": c.get("avg", 0),
            "badges": c.get("badges", 0)
        })
    data.sort(key=lambda x: x["score"])
    conn.close()
    return data

def get_summary(data):
    return {
        "total": len(data),
        "high": len([d for d in data if d["risk_class"]=="high"]),
        "medium": len([d for d in data if d["risk_class"]=="medium"]),
        "low": len([d for d in data if d["risk_class"]=="low"]),
        "fee_pending": len([d for d in data if d["pending"]>0]),
        "att_critical": len([d for d in data if d["att"]<60]),
        "avg_attendance": round(sum(d["att"] for d in data)/len(data), 2) if data else 0,
        "total_fees_collected": sum(85000 for d in data if d.get("fee_status")=="paid"),
    }

# =============================================
#   GFM ROUTES
# =============================================

@app.route("/gfm/dashboard")
def gfm_dashboard():
    if not require_login("gfm"): return redirect("/login")
    data = get_all_students_data()
    summary = get_summary(data)
    topper = max(data, key=lambda x: x["mrk"]) if data else None
    return render_template("gfm_dashboard.html", role="gfm", page="dashboard",
                           user_name=session["user_name"], students=data, summary=summary, topper=topper)

@app.route("/gfm/students")
def gfm_students():
    if not require_login("gfm"): return redirect("/login")
    data = get_all_students_data()
    summary = get_summary(data)
    return render_template("gfm_students.html", role="gfm", page="students",
                           user_name=session["user_name"], students=data, summary=summary)

@app.route("/gfm/attendance")
def gfm_attendance():
    if not require_login("gfm"): return redirect("/login")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.student_name, s.prn_number, a.date, a.status
        FROM attendance a JOIN students s ON a.prn_number = s.prn_number
        ORDER BY a.date DESC LIMIT 200
    """)
    records = cursor.fetchall()
    cursor.execute("SELECT COUNT(*), SUM(status='present'), SUM(status='absent') FROM attendance")
    total, present, absent = cursor.fetchone()
    conn.close()
    pct = round(100*present/total, 1) if total else 0
    return render_template("gfm_attendance.html", role="gfm", page="attendance",
                           user_name=session["user_name"], records=records,
                           total=total, present=present, absent=absent, pct=pct)

@app.route("/gfm/fees")
def gfm_fees():
    if not require_login("gfm"): return redirect("/login")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.student_name, s.prn_number, f.amount_due, f.amount_paid, f.status
        FROM fees f JOIN students s ON f.prn_number = s.prn_number
        ORDER BY (f.amount_due - f.amount_paid) DESC
    """)
    records = cursor.fetchall()
    conn.close()
    return render_template("gfm_fees.html", role="gfm", page="fees",
                           user_name=session["user_name"], records=records)

@app.route("/gfm/results")
def gfm_results():
    if not require_login("gfm"): return redirect("/login")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.student_name, s.prn_number, m.subject_name, m.test1, m.test2, m.max_marks,
               ROUND(((m.test1+m.test2)/(m.max_marks*2))*100,1) as pct
        FROM marks m JOIN students s ON m.prn_number = s.prn_number
        ORDER BY pct ASC
    """)
    records = cursor.fetchall()
    cursor.execute("""
        SELECT ROUND(AVG(((test1+test2)/(max_marks*2))*100),1),
               MAX(ROUND(((test1+test2)/(max_marks*2))*100,1)),
               SUM(CASE WHEN ((test1+test2)/(max_marks*2))*100 < 40 THEN 1 ELSE 0 END)
        FROM marks
    """)
    avg_pct, highest_pct, failed = cursor.fetchone()
    conn.close()
    return render_template("gfm_results.html", role="gfm", page="results",
                           user_name=session["user_name"], records=records,
                           avg_pct=avg_pct, highest_pct=highest_pct, failed=failed, total=len(records))

# =============================================
#   STUDENT ROUTES
# =============================================

@app.route("/student/dashboard")
def student_dashboard():
    if not require_login("student"): return redirect("/login")
    prn = session["prn"]
    data = get_all_students_data()
    me = next((d for d in data if d["prn"] == prn), None)
    rank = data.index(me) + 1 if me else None
    return render_template("student_dashboard.html", role="student", page="dashboard",
                           user_name=session["user_name"], me=me, rank=rank, total=len(data))

@app.route("/student/attendance")
def student_attendance():
    if not require_login("student"): return redirect("/login")
    prn = session["prn"]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT date, status FROM attendance WHERE prn_number=%s ORDER BY date DESC", (prn,))
    records = cursor.fetchall()
    cursor.execute("SELECT COUNT(*), SUM(status='present') FROM attendance WHERE prn_number=%s", (prn,))
    total, present = cursor.fetchone()
    conn.close()
    pct = round(100*present/total, 1) if total else 0
    return render_template("student_attendance.html", role="student", page="attendance",
                           user_name=session["user_name"], records=records,
                           total=total, present=present, absent=total-present if total else 0, pct=pct)

@app.route("/student/results")
def student_results():
    if not require_login("student"): return redirect("/login")
    prn = session["prn"]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT subject_name, test1, test2, max_marks,
               ROUND(((test1+test2)/(max_marks*2))*100,1) as pct
        FROM marks WHERE prn_number=%s
    """, (prn,))
    records = cursor.fetchall()
    conn.close()
    avg = round(sum(r[4] for r in records)/len(records), 1) if records else 0
    return render_template("student_results.html", role="student", page="results",
                           user_name=session["user_name"], records=records, avg=avg)

@app.route("/student/fees")
def student_fees():
    if not require_login("student"): return redirect("/login")
    prn = session["prn"]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT fee_type, amount_due, amount_paid, status, due_date FROM fees WHERE prn_number=%s", (prn,))
    records = cursor.fetchall()
    conn.close()
    return render_template("student_fees.html", role="student", page="fees",
                           user_name=session["user_name"], records=records)

@app.route("/student/career")
def student_career():
    if not require_login("student"): return redirect("/login")
    prn = session["prn"]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT career_goal, skill_name, completion_pct, badge_earned FROM career_progress WHERE prn_number=%s", (prn,))
    records = cursor.fetchall()
    conn.close()
    goal = records[0][0] if records else "Not set"
    avg = round(sum(r[2] for r in records)/len(records), 1) if records else 0
    return render_template("student_career.html", role="student", page="career",
                           user_name=session["user_name"], records=records, goal=goal, avg=avg)

# =============================================
#   AI REPORT ROUTE - Ollama
# =============================================

@app.route("/ai_report", methods=["POST"])
def ai_report():
    if not session.get("role"):
        return jsonify({"error": "Not logged in"}), 401
    data = request.get_json()
    prompt = data.get("prompt", "")
    try:
        response = ollama.chat(
            model="llama3.2",
            messages=[{"role": "user", "content": prompt}]
        )
        report = response['message']['content']
        return jsonify({"report": report})
    except Exception as e:
        return jsonify({"report": f"Error: {str(e)}\n\nMake sure Ollama is running.\nRun: ollama pull llama3.2"})

# =============================================
#   RUN
# =============================================

if __name__ == "__main__":
    print("="*50)
    print("  MentorSphere starting...")
    print("  Open: http://localhost:5000")
    print("="*50)
    app.run(debug=True)
