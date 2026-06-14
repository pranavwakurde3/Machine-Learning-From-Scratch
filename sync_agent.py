# =============================================
#   SYNC AGENT
#   Pulls data from Google Sheet -> MySQL
#   Run this anytime the sheet is updated
#   Then refresh the dashboard to see changes
# =============================================

import pandas as pd
import mysql.connector

# --- STEP 1: Your Google Sheet ID ---
SHEET_ID = "1vpRazpAADb6JELbw2rOI6yEoe_SE2Iks43g6POTmEik"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

print("=" * 55)
print("   SYNC AGENT -- Google Sheet -> MySQL")
print("=" * 55)

# --- STEP 2: Read Google Sheet ---
try:
    df = pd.read_csv(SHEET_URL)
    print(f"Read {len(df)} rows from Google Sheet")
except Exception as e:
    print(f"ERROR: Could not read sheet: {e}")
    exit()

# --- STEP 3: Connect to MySQL ---
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="222",   # <-- change this
    database="gfm_platform"
)
cursor = conn.cursor()

# --- STEP 4: Clean and insert/update each row ---
updated = 0
skipped = 0

for index, row in df.iterrows():
    try:
        prn   = str(row['prn_number']).strip()
        name  = str(row['student_name']).strip()
        phone = str(row['parent_phone']).strip()

        # Skip empty rows
        if prn == '' or prn.lower() == 'nan':
            skipped += 1
            continue

        # Attendance
        att = float(row['attendance_pct'])

        # Marks
        marks = float(row['marks_pct'])

        # Fee pending -- handle text values
        fee_raw = str(row['fee_pending']).strip().lower()
        if fee_raw in ['paid', '0', 'nan', '']:
            fee = 0.0
        elif fee_raw == 'pending':
            fee = 85000.0
        else:
            try:
                fee = float(row['fee_pending'])
            except:
                fee = 0.0

        # Career progress -- handle text values (career goal names)
        career_raw = str(row['career_progress']).strip()
        try:
            career = float(career_raw)
        except:
            career = 50.0   # default if text like "AI Engineer"

        cursor.execute("""
            INSERT INTO sheet_data
                (prn_number, student_name, parent_phone,
                 attendance_pct, marks_pct, fee_pending, career_progress)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                student_name = VALUES(student_name),
                parent_phone = VALUES(parent_phone),
                attendance_pct = VALUES(attendance_pct),
                marks_pct = VALUES(marks_pct),
                fee_pending = VALUES(fee_pending),
                career_progress = VALUES(career_progress),
                last_synced = NOW()
        """, (prn, name, phone, att, marks, fee, career))

        updated += 1

    except Exception as row_error:
        print(f"  Skipped row {index+2} (PRN: {row.get('prn_number','?')}) -- {row_error}")
        skipped += 1
        continue

conn.commit()
cursor.close()
conn.close()

print()
print(f"Synced {updated} students into MySQL!")
if skipped > 0:
    print(f"Skipped {skipped} rows (empty or bad data)")
print()
print("Now refresh your dashboard at http://localhost:5000")
print("to see the updated data.")
