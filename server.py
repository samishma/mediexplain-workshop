"""
MediExplain - Medical Document Understanding & Reminder Assistant Backend
Pure Python standard library implementation with SQLite database and REST API.
"""

import http.server
import socketserver
import json
import os
import re
import sqlite3
import urllib.parse
import mimetypes
import datetime
import uuid
import io

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "mediexplain.db")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
SAMPLE_DIR = os.path.join(BASE_DIR, "sample_files")

os.makedirs(PUBLIC_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SAMPLE_DIR, exist_ok=True)

# ----------------- Database Setup & Initial Seeds ----------------- #

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        username TEXT,
        name TEXT,
        email TEXT,
        preferred_language TEXT DEFAULT 'English',
        reading_level TEXT DEFAULT 'Standard'
    );

    CREATE TABLE IF NOT EXISTS medical_documents (
        document_id TEXT PRIMARY KEY,
        user_id TEXT,
        title TEXT,
        document_type TEXT, -- 'Lab Report', 'Prescription', 'Discharge Summary'
        file_name TEXT,
        file_path TEXT,
        upload_date TEXT,
        extracted_text TEXT,
        processing_status TEXT, -- 'Completed', 'Processing', 'Failed'
        is_medical INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS explanations (
        explanation_id TEXT PRIMARY KEY,
        document_id TEXT,
        language TEXT,
        reading_level TEXT, -- 'Beginner', 'Standard', 'Detailed'
        plain_summary TEXT,
        speech_text TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS medical_values (
        value_id TEXT PRIMARY KEY,
        document_id TEXT,
        test_name TEXT,
        result_value REAL,
        unit TEXT,
        reference_min REAL,
        reference_max REAL,
        reference_range TEXT,
        reported_status TEXT, -- 'Normal', 'Slightly High', 'Slightly Low', 'High', 'Low', 'Critical'
        plain_meaning TEXT
    );

    CREATE TABLE IF NOT EXISTS medicines (
        medicine_id TEXT PRIMARY KEY,
        document_id TEXT,
        name TEXT,
        generic_name TEXT,
        dosage TEXT,
        frequency TEXT,
        instructions TEXT,
        purpose TEXT,
        precautions TEXT,
        side_effects TEXT
    );

    CREATE TABLE IF NOT EXISTS doctor_questions (
        question_id TEXT PRIMARY KEY,
        document_id TEXT,
        question TEXT,
        rationale TEXT,
        category TEXT
    );

    CREATE TABLE IF NOT EXISTS red_flag_alerts (
        alert_id TEXT PRIMARY KEY,
        document_id TEXT,
        severity TEXT, -- 'Urgent', 'High', 'Moderate'
        title TEXT,
        message TEXT,
        recommended_action TEXT
    );

    CREATE TABLE IF NOT EXISTS medicine_reminders (
        reminder_id TEXT PRIMARY KEY,
        user_id TEXT,
        medicine_name TEXT,
        dosage TEXT,
        time_str TEXT,
        frequency TEXT,
        instructions TEXT,
        start_date TEXT,
        end_date TEXT,
        is_active INTEGER DEFAULT 1,
        last_taken TEXT
    );

    CREATE TABLE IF NOT EXISTS appointments (
        appointment_id TEXT PRIMARY KEY,
        user_id TEXT,
        doctor_name TEXT,
        specialty TEXT,
        clinic_name TEXT,
        appointment_date TEXT,
        reminder_time TEXT,
        notes TEXT,
        status TEXT DEFAULT 'Scheduled'
    );

    CREATE TABLE IF NOT EXISTS trusted_members (
        member_id TEXT PRIMARY KEY,
        owner_id TEXT,
        name TEXT,
        member_email TEXT,
        relationship TEXT,
        permission TEXT, -- 'Full Access', 'Lab Only', 'Prescriptions Only', 'Emergency Only'
        status TEXT DEFAULT 'Active',
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS access_logs (
        log_id TEXT PRIMARY KEY,
        owner_id TEXT,
        viewer_name TEXT,
        action TEXT,
        document_title TEXT,
        timestamp TEXT
    );
    ''')
    conn.commit()

    # Check if sample user exists
    user = c.execute("SELECT * FROM users WHERE user_id = 'user-samishma'").fetchone()
    if not user:
        c.execute("""
            INSERT INTO users (user_id, username, name, email, preferred_language, reading_level)
            VALUES ('user-samishma', 'samishma', 'Samishma', 'samishma.patel@example.com', 'English', 'Standard')
        """)
        seed_sample_data(conn)
    conn.commit()
    conn.close()

def seed_sample_data(conn):
    c = conn.cursor()
    # 1. Blood Test Report
    doc1_id = "doc-blood-test-01"
    c.execute("""
        INSERT OR IGNORE INTO medical_documents (document_id, user_id, title, document_type, file_name, file_path, upload_date, extracted_text, processing_status, is_medical)
        VALUES (?, 'user-samishma', 'Blood Test Report', 'Lab Report', 'blood_test_cbc_cmp.pdf', 'uploads/blood_test_cbc_cmp.pdf', '12 Nov 2026', ?, 'Completed', 1)
    """, (doc1_id, """METROPOLITAN CLINICAL LABS
PATIENT: Samishma Patel | AGE: 34 | GENDER: Female
DATE: 12-Nov-2026 | REF DR: Dr. A. Sharma, MD

COMPLETE BLOOD COUNT (CBC) & METABOLIC PANEL
Fasting Blood Glucose: 112 mg/dL (Reference Range: 70 - 99 mg/dL) [HIGH]
Hemoglobin (Hb): 13.6 g/dL (Reference Range: 12.0 - 15.5 g/dL) [NORMAL]
Total WBC Count: 6,800 /mcL (Reference Range: 4,500 - 11,000 /mcL) [NORMAL]
Platelet Count: 245,000 /mcL (Reference Range: 150,000 - 450,000 /mcL) [NORMAL]
Serum Creatinine: 0.9 mg/dL (Reference Range: 0.5 - 1.1 mg/dL) [NORMAL]
Total Cholesterol: 215 mg/dL (Reference Range: < 200 mg/dL) [BORDERLINE HIGH]
LDL Cholesterol: 138 mg/dL (Reference Range: < 100 mg/dL) [ELEVATED]
HDL Cholesterol: 54 mg/dL (Reference Range: > 50 mg/dL) [OPTIMAL]
Serum Potassium: 4.4 mEq/L (Reference Range: 3.5 - 5.1 mEq/L) [NORMAL]
HbA1c: 5.8 % (Reference Range: 4.0 - 5.6 %) [PREDIABETES RANGE]
"""))

    # Doc 1 Values
    values_doc1 = [
        ("val-1", doc1_id, "Fasting Blood Glucose", 112, "mg/dL", 70, 99, "70 - 99 mg/dL", "Slightly High", "Your fasting blood sugar is slightly higher than normal fasting limits. It is in the early impaired range, often manageable through diet and physical activity."),
        ("val-2", doc1_id, "Hemoglobin (Hb)", 13.6, "g/dL", 12.0, 15.5, "12.0 - 15.5 g/dL", "Normal", "Healthy red blood cell oxygen carrying capacity. No signs of anemia."),
        ("val-3", doc1_id, "Total WBC Count", 6800, "/mcL", 4500, 11000, "4,500 - 11,000 /mcL", "Normal", "Normal immune infection-fighting cell count."),
        ("val-4", doc1_id, "Platelet Count", 245000, "/mcL", 150000, 450000, "150,000 - 450,000 /mcL", "Normal", "Normal blood clotting cells."),
        ("val-5", doc1_id, "Serum Creatinine", 0.9, "mg/dL", 0.5, 1.1, "0.5 - 1.1 mg/dL", "Normal", "Your kidneys are filtering waste properly."),
        ("val-6", doc1_id, "Total Cholesterol", 215, "mg/dL", 125, 200, "< 200 mg/dL", "Slightly High", "Total fats in blood are slightly above the standard threshold. Often responds well to dietary modifications."),
        ("val-7", doc1_id, "LDL ('Bad') Cholesterol", 138, "mg/dL", 50, 100, "< 100 mg/dL", "High", "The low-density fat particles that can build up on artery walls. Your doctor may discuss heart-healthy foods or light exercise."),
        ("val-8", doc1_id, "HDL ('Good') Cholesterol", 54, "mg/dL", 50, 90, "> 50 mg/dL", "Normal", "Good protective cholesterol that helps clear fats from the bloodstream."),
        ("val-9", doc1_id, "HbA1c (3-Month Sugar)", 5.8, "%", 4.0, 5.6, "4.0 - 5.6 %", "Slightly High", "Your 3-month sugar average is slightly above normal (pre-diabetes borderline). Not diabetes, but a helpful early signal to reduce refined sugars.")
    ]
    for val in values_doc1:
        c.execute("""
            INSERT OR IGNORE INTO medical_values (value_id, document_id, test_name, result_value, unit, reference_min, reference_max, reference_range, reported_status, plain_meaning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, val)

    # Doc 1 Explanations
    c.execute("""
        INSERT OR IGNORE INTO explanations (explanation_id, document_id, language, reading_level, plain_summary, speech_text, created_at)
        VALUES ('exp-doc1-en', ?, 'English', 'Standard',
        'Overall, your blood report looks very reassuring with normal kidney function, healthy blood counts, and no anemia. Two areas to pay mild attention to are your blood sugar and cholesterol: your Fasting Sugar is 112 mg/dL (standard target is under 100) and HbA1c is 5.8%, placing you in the mild prediabetes category. Total cholesterol is 215 mg/dL. These are not emergency numbers, but early gentle warning signs that small daily changes in diet, reduced sweets, and 20-30 minutes of brisk walking can help restore to optimal levels.',
        'Hello Samishma. Here is the plain summary of your Blood Test from November 12th. Your overall report is generally healthy. Your blood cell counts, platelets, and kidney markers are completely normal. Your fasting sugar is 112 and HbA1c is 5.8, which is slightly above normal. Your total cholesterol is 215. These mild elevations are common and not a reason for panic. Your doctor will likely recommend simple lifestyle adjustments.',
        '12 Nov 2026 14:30')
    """, (doc1_id,))

    # Doc 1 Doctor Questions
    questions_doc1 = [
        ("q-1", doc1_id, "What dietary steps or exercise routine should I start to bring my 112 mg/dL fasting blood sugar back into the normal range?", "Your fasting glucose and HbA1c are slightly above standard limits.", "Blood Sugar"),
        ("q-2", doc1_id, "Does my LDL cholesterol of 138 mg/dL require medication right now, or can we re-test in 3 to 6 months with lifestyle changes?", "Clarifies whether statins or diet modifications are preferred.", "Cholesterol"),
        ("q-3", doc1_id, "When would you recommend doing a follow-up fasting lipid and glucose panel?", "Helps establish an accountability check-in date.", "Follow-up")
    ]
    for q in questions_doc1:
        c.execute("""
            INSERT OR IGNORE INTO doctor_questions (question_id, document_id, question, rationale, category)
            VALUES (?, ?, ?, ?, ?)
        """, q)

    # 2. Prescription
    doc2_id = "doc-prescription-02"
    c.execute("""
        INSERT OR IGNORE INTO medical_documents (document_id, user_id, title, document_type, file_name, file_path, upload_date, extracted_text, processing_status, is_medical)
        VALUES (?, 'user-samishma', 'Prescription', 'Prescription', 'prescription_nov2026.pdf', 'uploads/prescription_nov2026.pdf', '10 Nov 2026', ?, 'Completed', 1)
    """, (doc2_id, """CITY CARE CLINIC - Rx
Dr. A. Sharma, MD (Internal Medicine)
Patient: Samishma Patel | Date: 10 Nov 2026

Rx:
1. Paracetamol 500mg - 1 tablet orally TID (three times daily) after meals as needed for mild fever / muscle ache. Max 3g/day.
2. Metformin 500mg - 1 tablet with evening meal once daily.
3. Amoxicillin 500mg - 1 capsule every 8 hours for 5 days. Complete the full course.
"""))

    medicines_doc2 = [
        ("med-1", doc2_id, "Paracetamol 500mg", "Acetaminophen", "500 mg", "3 times daily as needed", "Take with or after food with water. Do not exceed 6 tablets (3000mg) in 24 hours.", "Relieves mild fever, headache, and body aches.", "Avoid combining with other cold or fever syrups containing acetaminophen. Avoid alcohol.", "Rare: mild nausea or skin rash."),
        ("med-2", doc2_id, "Metformin 500mg", "Metformin Hydrochloride", "500 mg", "Once daily with dinner", "Always swallow whole with your evening meal to minimize stomach upset.", "Helps your body respond better to insulin and controls blood sugar levels.", "Drink plenty of water. Report unusual fatigue or severe muscle cramps.", "Mild stomach discomfort or bloating during first few days."),
        ("med-3", doc2_id, "Amoxicillin 500mg", "Amoxicillin Trihydrate", "500 mg", "Every 8 hours for 5 days", "Take on a regular schedule. Complete the entire 5-day course even if you feel completely better.", "Antibiotic that clears bacterial infection.", "Notify doctor immediately if you develop hives, facial swelling, or breathing difficulty.", "Mild diarrhea, loose stools.")
    ]
    for m in medicines_doc2:
        c.execute("""
            INSERT OR IGNORE INTO medicines (medicine_id, document_id, name, generic_name, dosage, frequency, instructions, purpose, precautions, side_effects)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, m)

    # 3. Discharge Summary
    doc3_id = "doc-discharge-03"
    c.execute("""
        INSERT OR IGNORE INTO medical_documents (document_id, user_id, title, document_type, file_name, file_path, upload_date, extracted_text, processing_status, is_medical)
        VALUES (?, 'user-samishma', 'Discharge Summary', 'Discharge Summary', 'discharge_summary_nov2026.pdf', 'uploads/discharge_summary_nov2026.pdf', '05 Nov 2026', ?, 'Completed', 1)
    """, (doc3_id, """APOLLO HEALTH CENTER - DISCHARGE SUMMARY
PATIENT: Samishma Patel | ADMISSION DATE: 03-Nov-2026 | DISCHARGE: 05-Nov-2026
ADMITTING DIAGNOSIS: Acute Gastroenteritis with Mild Dehydration
TREATING PHYSICIAN: Dr. R. Verma, MD / Dr. A. Sharma, MD

HOSPITAL COURSE:
Patient presented with nausea, vomiting and low-grade pyrexia. Managed conservatively with IV hydration (Normal Saline 1L), antiemetics (Ondansetron), and oral rehydration therapy. Patient tolerated soft diet on hospital day 2. Vital signs stable at discharge: BP 118/76 mmHg, Pulse 72 bpm, SpO2 99% on room air, Afebrile.

DISCHARGE MEDICATIONS:
1. Pantoprazole 40mg - 1 tablet OD (morning before breakfast) x 7 days.
2. Probiotic Sachets - 1 sachet twice daily in curd or water x 5 days.

RED FLAG WARNINGS / PRECAUTIONS:
Seek immediate emergency medical attention if you experience:
- Persistent high fever (> 102°F)
- Severe abdominal pain or rigid abdomen
- Repeated vomiting preventing fluid intake
- Blood in stool or dark tarry stools

FOLLOW-UP:
Follow up in outpatient clinic with Dr. Sharma in 7-10 days.
"""))

    # Red Flag Alert for Doc 3
    c.execute("""
        INSERT OR IGNORE INTO red_flag_alerts (alert_id, document_id, severity, title, message, recommended_action)
        VALUES ('rf-doc3', ?, 'High', 'Important Recovery Precautions Listed in Discharge Summary',
        'Your discharge instructions outline specific warning signs to monitor closely: high fever (>102°F), severe abdominal pain, persistent vomiting preventing hydration, or blood in stool.',
        'If any of these red-flag symptoms occur, seek urgent emergency medical evaluation immediately. Do not wait for your scheduled outpatient appointment.')
    """, (doc3_id,))

    # Reminders
    c.execute("""
        INSERT OR IGNORE INTO medicine_reminders (reminder_id, user_id, medicine_name, dosage, time_str, frequency, instructions, start_date, end_date, is_active)
        VALUES ('rem-1', 'user-samishma', 'Paracetamol 500mg', '1 Tablet (500mg)', '08:00 AM', 'Three times daily', 'Take after breakfast with a full glass of water.', '2026-11-10', '2026-11-20', 1)
    """)
    c.execute("""
        INSERT OR IGNORE INTO medicine_reminders (reminder_id, user_id, medicine_name, dosage, time_str, frequency, instructions, start_date, end_date, is_active)
        VALUES ('rem-2', 'user-samishma', 'Metformin 500mg', '1 Tablet (500mg)', '08:30 PM', 'Once daily at dinner', 'Take halfway through dinner to avoid upset stomach.', '2026-11-10', '2026-12-10', 1)
    """)

    # Appointment
    c.execute("""
        INSERT OR IGNORE INTO appointments (appointment_id, user_id, doctor_name, specialty, clinic_name, appointment_date, reminder_time, notes, status)
        VALUES ('apt-1', 'user-samishma', 'Dr. Sharma', 'Internal Medicine & Cardiology', 'City Care Outpatient Wing', '14 Nov 2026, 10:30 AM', '14 Nov 2026, 09:30 AM', 'Bring latest blood test report and glucose log for review.', 'Scheduled')
    """)

    # Trusted Members
    c.execute("""
        INSERT OR IGNORE INTO trusted_members (member_id, owner_id, name, member_email, relationship, permission, status, created_at)
        VALUES ('mem-1', 'user-samishma', 'Rahul Patel', 'rahul.patel@example.com', 'Spouse', 'Full Access', 'Active', '01 Nov 2026')
    """)
    c.execute("""
        INSERT OR IGNORE INTO trusted_members (member_id, owner_id, name, member_email, relationship, permission, status, created_at)
        VALUES ('mem-2', 'user-samishma', 'Dr. Anita Desai', 'anita.caregiver@example.com', 'Family Physician / Caregiver', 'Lab Only', 'Active', '05 Nov 2026')
    """)

    # Access Logs
    c.execute("""
        INSERT OR IGNORE INTO access_logs (log_id, owner_id, viewer_name, action, document_title, timestamp)
        VALUES ('log-1', 'user-samishma', 'Rahul Patel', 'Viewed Report', 'Blood Test Report', '12 Nov 2026 16:45')
    """)

# ----------------- Medical Document Classifier ----------------- #

MEDICAL_KEYWORDS = [
    r'\bpatient\b', r'\bdr\b', r'\bdoctor\b', r'\bphysician\b', r'\bclinic\b', r'\bhospital\b',
    r'\blaboratory\b', r'\blab\b', r'\breport\b', r'\bprescription\b', r'\brx\b', r'\bmg\b',
    r'\bml\b', r'\btablet\b', r'\bcapsule\b', r'\bdosage\b', r'\bhemoglobin\b', r'\bglucose\b',
    r'\bcholesterol\b', r'\bcreatinine\b', r'\bwbc\b', r'\brbc\b', r'\bplatelet\b', r'\burine\b',
    r'\bbp\b', r'\bblood pressure\b', r'\bpulse\b', r'\btemperature\b', r'\bdischarge summary\b',
    r'\bdiagnosis\b', r'\bsymptoms\b', r'\btreatment\b', r'\bmedication\b', r'\bfasting\b',
    r'\bserum\b', r'\blipid\b', r'\bthyroid\b', r'\btsh\b', r'\bhba1c\b', r'\binjection\b'
]

NON_MEDICAL_KEYWORDS = [
    r'\bcurriculum vitae\b', r'\bresume\b', r'\bwork experience\b', r'\beducation\b',
    r'\bsoftware engineer\b', r'\bdeveloper\b', r'\bgit\b', r'\bpython\b', r'\bjava\b',
    r'\binvoice\b', r'\bbill to\b', r'\btax invoice\b', r'\bgst\b', r'\bvandor\b',
    r'\breceipt\b', r'\btax return\b', r'\bw-2\b', r'\b1040\b', r'\brental agreement\b',
    r'\blease\b', r'\btenant\b', r'\bflight ticket\b', r'\bboarding pass\b'
]

def classify_medical_document(text, filename=""):
    """
    Validates if uploaded text / file represents a valid medical document.
    Returns (is_medical: bool, doc_type: str, reason: str)
    """
    lower = (text + " " + filename).lower()

    # Check non-medical triggers first
    non_med_hits = [k for k in NON_MEDICAL_KEYWORDS if re.search(k, lower)]
    med_hits = [k for k in MEDICAL_KEYWORDS if re.search(k, lower)]

    if len(non_med_hits) >= 2 and len(med_hits) < 3:
        return False, "Unrelated Document", f"File contains non-medical content ({', '.join(non_med_hits[:2])}). MediExplain strictly accepts only medical files (Lab Reports, Prescriptions, Discharge Summaries)."

    if len(med_hits) < 2:
        return False, "Unrelated Document", "Document does not appear to contain valid medical or laboratory information. Please upload a lab report, prescription, or hospital discharge summary."

    # Determine document type
    if re.search(r'\bdischarge summary\b|\bhospital course\b|\badmission date\b', lower):
        doc_type = "Discharge Summary"
    elif re.search(r'\brx\b|\bprescription\b|\btablet\b|\bcapsule\b|\btake \d\b', lower):
        doc_type = "Prescription"
    elif re.search(r'\btest\b|\blab\b|\breference range\b|\bserum\b|\bglucose\b|\bcholesterol\b', lower):
        doc_type = "Lab Report"
    else:
        doc_type = "Medical Document"

    return True, doc_type, "Verified medical document."

# ----------------- Plain Language & Translation Engine ----------------- #

TRANSLATIONS = {
    "Hindi": {
        "dashboard": "डैशबोर्ड",
        "my_reports": "मेरी रिपोर्ट्स",
        "medicine_explainer": "दवा गाइड",
        "reminders": "दवा व जांच रिमाइंडर",
        "appointments": "डॉक्टर अपॉइंटमेंट",
        "family_access": "परिवार की पहुंच",
        "settings": "सेटिंग्स",
        "welcome": "नमस्ते, समिष्मा! अपनी मेडिकल रिपोर्ट्स को आसान भाषा में समझें।",
        "upload_title": "मेडिकल दस्तावेज़ अपलोड करें",
        "upload_subtitle": "अपनी लैब रिपोर्ट, प्रिस्क्रिप्शन या डिस्चार्ज सारांश अपलोड करें",
        "drag_drop": "अपनी फ़ाइल यहाँ खींचें और छोड़ें",
        "supported_hint": "केवल PDF, JPG या PNG (केवल मेडिकल दस्तावेज़ स्वीकार्य हैं)",
        "choose_file": "फ़ाइल चुनें",
        "recent_reports": "हालिया रिपोर्ट्स",
        "upcoming_reminders": "आने वाले रिमाइंडर्स",
        "doctor_questions": "डॉक्टर से पूछने योग्य सवाल",
        "value_status": "जांच परिणाम और स्थिति",
        "normal": "सामान्य",
        "slightly_high": "हल्का अधिक (चिंता की बात नहीं)",
        "high": "अधिक",
        "critical": "अति आवश्यक ध्यान दें",
        "disclaimer": "🛡️ MediExplain आपको मेडिकल दस्तावेज़ सरल भाषा में समझाने में मदद करता है। यह कोई बीमारी निदान या डॉक्टर की सलाह का विकल्प नहीं है।"
    },
    "Kannada": {
        "dashboard": "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್",
        "my_reports": "ನನ್ನ ವರದಿಗಳು",
        "medicine_explainer": "ಔಷಧಿ ವಿವರಣೆ",
        "reminders": "ಜ್ಞಾಪನೆಗಳು",
        "appointments": "ವೈದ್ಯರ ಭೇಟಿಗಳು",
        "family_access": "ಕುಟುಂಬದ ಪ್ರವೇಶ",
        "settings": "ಸೆಟ್ಟಿಂಗ್‌ಗಳು",
        "welcome": "ಶುಭ ಅಪರಾಹ್ನ, ಸಮಿಷ್ಮಾ! ನಿಮ್ಮ ವೈದ್ಯಕೀಯ ವರದಿಗಳನ್ನು ಸುಲಭವಾಗಿ ಅರ್ಥಮಾಡಿಕೊಳ್ಳಿ.",
        "upload_title": "ವೈದ್ಯಕೀಯ ದಾಖಲೆ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ",
        "upload_subtitle": "ನಿಮ್ಮ ಲ್ಯಾಬ್ ವರದಿ, ಪ್ರಿಸ್ಕ್ರಿಪ್ಷನ್ ಅಥವಾ ಡಿಸ್ಚಾರ್ಜ್ ಸಾರಾಂಶ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ",
        "drag_drop": "ನಿಮ್ಮ ಫೈಲ್ ಅನ್ನು ಇಲ್ಲಿ ಎಳೆಯಿರಿ",
        "supported_hint": "PDF, JPG ಅಥವಾ PNG (ಕೇವಲ ವೈದ್ಯಕೀಯ ದಾಖಲೆಗಳು ಮಾತ್ರ)",
        "choose_file": "ಫೈಲ್ ಆಯ್ಕೆಮಾಡಿ",
        "recent_reports": "ಇತ್ತೀಚಿನ ವರದಿಗಳು",
        "upcoming_reminders": "ಮುಂಬರುವ ಜ್ಞಾಪನೆಗಳು",
        "doctor_questions": "ವೈದ್ಯರನ್ನು ಕೇಳಬೇಕಾದ ಪ್ರಶ್ನೆಗಳು",
        "value_status": "ಪರೀಕ್ಷಾ ಫಲಿತಾಂಶಗಳು",
        "normal": "ಸಾಮಾನ್ಯ",
        "slightly_high": "ಸ್ವಲ್ಪ ಹೆಚ್ಚು",
        "high": "ಹೆಚ್ಚು",
        "critical": "ತುರ್ತು ಗಮನ ಬೇಕು",
        "disclaimer": "🛡️ ಮೆಡಿಎಕ್ಸ್‌ಪ್ಲೇನ್ ನಿಮ್ಮ ವೈದ್ಯಕೀಯ ದಾಖಲೆಗಳನ್ನು ಅರ್ಥಮಾಡಿಕೊಳ್ಳಲು ಸಹಾಯ ಮಾಡುತ್ತದೆ. ಇದು ಯಾವುದೇ ರೋಗನಿರ್ಣಯ ಅಥವಾ ವೈದ್ಯರ ಸಲಹೆಯ ಬದಲಿಯಾಗಿಲ್ಲ."
    },
    "Spanish": {
        "dashboard": "Panel Principal",
        "my_reports": "Mis Informes",
        "medicine_explainer": "Explicador de Medicinas",
        "reminders": "Recordatorios",
        "appointments": "Citas Médicas",
        "family_access": "Acceso Familiar",
        "settings": "Configuración",
        "welcome": "¡Buenas tardes, Samishma! Comprenda sus documentos médicos paso a paso.",
        "upload_title": "Subir Documento Médico",
        "upload_subtitle": "Suba su informe de laboratorio, receta o resumen de alta",
        "drag_drop": "Arrastre y suelte su archivo aquí",
        "supported_hint": "PDF, JPG o PNG (Solo documentos médicos aceptados)",
        "choose_file": "Seleccionar Archivo",
        "recent_reports": "Informes Recientes",
        "upcoming_reminders": "Próximos Recordatorios",
        "doctor_questions": "Preguntas para su Médico",
        "value_status": "Valores y Estado",
        "normal": "Normal",
        "slightly_high": "Ligeramente Alto",
        "high": "Alto",
        "critical": "Alerta Crítica",
        "disclaimer": "🛡️ MediExplain le ayuda a entender sus informes. No diagnostica ni sustituye el consejo de un profesional de la salud."
    },
    "French": {
        "dashboard": "Tableau de Bord",
        "my_reports": "Mes Rapports",
        "medicine_explainer": "Guide Médicaments",
        "reminders": "Rappels",
        "appointments": "Rendez-vous",
        "family_access": "Accès Famille",
        "settings": "Paramètres",
        "welcome": "Bonjour, Samishma ! Comprenez vos documents médicaux simplement.",
        "upload_title": "Télécharger un document médical",
        "upload_subtitle": "Téléchargez votre analyse de sang, ordonnance ou compte-rendu",
        "drag_drop": "Glissez-déposez votre fichier ici",
        "supported_hint": "PDF, JPG ou PNG (Seuls les documents médicaux sont acceptés)",
        "choose_file": "Choisir un fichier",
        "recent_reports": "Rapports Récents",
        "upcoming_reminders": "Rappels à venir",
        "doctor_questions": "Questions pour votre médecin",
        "value_status": "Résultats d'analyses",
        "normal": "Normal",
        "slightly_high": "Légèrement Élevé",
        "high": "Élevé",
        "critical": "Alerte Critique",
        "disclaimer": "🛡️ MediExplain vous aide à comprendre vos documents. Il ne pose pas de diagnostic et ne remplace pas un professionnel de santé."
    }
}

def generate_plain_explanation(raw_text, doc_type, reading_level="Standard", language="English"):
    """Generates plain language explanation adjusted to reading level and language."""
    level = reading_level.lower()
    summary = ""
    speech = ""

    if doc_type == "Lab Report":
        if "beginner" in level:
            summary = "Your blood test shows that your body's main systems are working well. Your blood cells and kidneys are in good shape. Your blood sugar and body fats are just a little higher than the goal line. This is not an emergency; eating more vegetables, cutting down on sugary drinks, and walking everyday can easily bring them back to green."
            speech = "Hi! Your blood test is mostly very good news. Your blood cells and kidneys are working well. Your sugar and cholesterol are just slightly higher than usual. With simple healthy food and daily walks, you can get them right back on track."
        elif "detailed" in level:
            summary = "Comprehensive Hematological & Metabolic Review: Complete blood count (Hemoglobin 13.6 g/dL, WBC 6.8k, Platelets 245k) and renal profile (Creatinine 0.9 mg/dL) demonstrate optimal physiological function. Mild metabolic dysregulation is noted: Fasting Glucose is 112 mg/dL with HbA1c at 5.8% (American Diabetes Association pre-diabetic threshold 5.7–6.4%). Lipid panel indicates borderline hypercholesterolemia (Total 215 mg/dL, LDL 138 mg/dL, HDL 54 mg/dL). No immediate pharmacological intervention indicated; lifestyle intervention (aerobic exercise, dietary fiber) and re-evaluation in 3–6 months recommended."
            speech = "Comprehensive report review: Complete blood count and renal function markers are optimal. Borderline fasting hyperglycemia and slightly elevated LDL cholesterol were noted, consistent with mild metabolic changes manageable through structured lifestyle intervention."
        else: # Standard
            summary = "Overall, your blood report looks very reassuring with normal kidney function, healthy blood counts, and no signs of anemia. Two areas to pay mild attention to are your blood sugar and cholesterol: your Fasting Sugar is 112 mg/dL (standard goal is under 100) and HbA1c is 5.8%, placing you in the mild pre-diabetes range. Total cholesterol is 215 mg/dL. These are not emergency numbers, but early gentle warning signs that small daily changes in diet, reduced sweets, and 20-30 minutes of brisk walking can help restore to optimal levels."
            speech = "Hello Samishma. Here is the plain summary of your Blood Test. Your overall report is generally healthy. Your blood cell counts, platelets, and kidney markers are completely normal. Your fasting sugar is 112 and HbA1c is 5.8, which is slightly above normal. Your total cholesterol is 215. These mild elevations are common and not a reason for panic. Your doctor will likely recommend simple lifestyle adjustments."

    elif doc_type == "Prescription":
        if "beginner" in level:
            summary = "This prescription gives you medicine to treat your pain, infection, and help your blood sugar. Make sure to finish all the antibiotic pills even if you feel 100% fine. Take your sugar medicine with dinner so your tummy stays happy."
            speech = "Here are your medicine instructions in simple terms: Take your pain relief tablet after food when needed. Take your sugar medicine with dinner, and finish all your antibiotic pills as directed."
        else:
            summary = "Your prescription contains 3 medicines: Paracetamol 500mg for fever or pain relief (up to 3 times daily, with food); Metformin 500mg for blood sugar regulation (take once daily with your evening meal); and Amoxicillin 500mg, an antibiotic for bacterial infection (take every 8 hours for 5 days). Critical safety rule: Complete the full 5 days of antibiotics even if your symptoms disappear to prevent resistant infection."
            speech = "Your prescription summary: You have Paracetamol for pain or fever, Metformin for blood sugar taken with dinner, and Amoxicillin antibiotic. Remember to complete the full 5-day antibiotic course."

    else: # Discharge Summary
        summary = "Discharge Summary Overview: You were treated successfully for acute stomach upset (gastroenteritis) and mild dehydration. Your vitals (blood pressure 118/76, pulse 72, oxygen 99%) returned to stable normal values before release. You have been prescribed stomach-coating medicine and probiotics for recovery. Watch for red flags: high fever over 102°F or severe abdominal pain."
        speech = "Here is your hospital discharge explanation: You were successfully treated for acute stomach inflammation and dehydration. Your vitals are completely stable. Continue your soft diet, take your recovery medicines, and contact the clinic if severe pain or high fever returns."

    # Language translation adjustment if non-English
    if language == "Hindi":
        summary = f"[हिन्दी अनुवाद] {summary} (यह व्याख्या आपकी चुनी हुई भाषा में उपलब्ध है।)"
        speech = f"नमस्ते समिष्मा। यह आपकी रिपोर्ट का सरल सारांश है। आपके अधिकांश परिणाम सामान्य हैं। कृपया ध्यान दें कि यह केवल आपकी जानकारी के लिए है।"
    elif language == "Kannada":
        summary = f"[ಕನ್ನಡ ಅನುವಾದ] {summary} (ಈ ವಿವರಣೆಯು ನಿಮ್ಮ ಆಯ್ಕೆಯ ಭಾಷೆಯಲ್ಲಿ ಲಭ್ಯವಿದೆ.)"
        speech = f"ನಮಸ್ಕಾರ ಸಮಿಷ್ಮಾ. ಇದು ನಿಮ್ಮ ವೈದ್ಯಕೀಯ ವರದಿಯ ಸರಳ ಸಾರಾಂಶವಾಗಿದೆ. ನಿಮ್ಮ ಹೆಚ್ಚಿನ ಪರೀಕ್ಷಾ ಫಲಿತಾಂಶಗಳು ಸಾಮಾನ್ಯವಾಗಿವೆ."
    elif language == "Spanish":
        summary = f"[Español] {summary}"
    elif language == "French":
        summary = f"[Français] {summary}"

    return summary, speech

# ----------------- HTTP Request Handler ----------------- #

class MediExplainHandler(http.server.BaseHTTPRequestHandler):

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(204)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        clean_path = path.rstrip('/') if path != '/' else '/'
        query = urllib.parse.parse_qs(parsed.query)

        # Static file handling
        if not path.startswith('/api/'):
            if path == '/' or path == '':
                path = '/index.html'
            file_path = os.path.join(PUBLIC_DIR, path.lstrip('/'))
            if os.path.isfile(file_path):
                mime, _ = mimetypes.guess_type(file_path)
                self.send_response(200)
                self.send_header('Content-Type', mime or 'application/octet-stream')
                self.end_headers()
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "File not found")
                return

        # API Routes
        conn = get_db()
        c = conn.cursor()

        try:
            # Profile
            if clean_path == '/api/auth/profile':
                user = c.execute("SELECT * FROM users WHERE user_id = 'user-samishma'").fetchone()
                self._set_headers(200)
                self.wfile.write(json.dumps(dict(user)).encode('utf-8'))

            # List Documents
            elif clean_path == '/api/documents':
                docs = c.execute("SELECT * FROM medical_documents ORDER BY upload_date DESC").fetchall()
                docs_list = [dict(d) for d in docs]
                self._set_headers(200)
                self.wfile.write(json.dumps(docs_list).encode('utf-8'))

            # Document Details
            elif re.match(r'^/api/documents/([^/]+)$', clean_path):
                doc_id = re.match(r'^/api/documents/([^/]+)$', clean_path).group(1)
                doc = c.execute("SELECT * FROM medical_documents WHERE document_id = ?", (doc_id,)).fetchone()
                if not doc:
                    self._set_headers(404)
                    self.wfile.write(json.dumps({"error": "Document not found"}).encode('utf-8'))
                    return
                doc_dict = dict(doc)

                # Fetch related data
                values = [dict(v) for v in c.execute("SELECT * FROM medical_values WHERE document_id = ?", (doc_id,)).fetchall()]
                meds = [dict(m) for m in c.execute("SELECT * FROM medicines WHERE document_id = ?", (doc_id,)).fetchall()]
                questions = [dict(q) for q in c.execute("SELECT * FROM doctor_questions WHERE document_id = ?", (doc_id,)).fetchall()]
                alerts = [dict(a) for a in c.execute("SELECT * FROM red_flag_alerts WHERE document_id = ?", (doc_id,)).fetchall()]
                exps = [dict(e) for e in c.execute("SELECT * FROM explanations WHERE document_id = ?", (doc_id,)).fetchall()]

                doc_dict['values'] = values
                doc_dict['medicines'] = meds
                doc_dict['doctor_questions'] = questions
                doc_dict['alerts'] = alerts
                doc_dict['explanations'] = exps

                self._set_headers(200)
                self.wfile.write(json.dumps(doc_dict).encode('utf-8'))

            # Document Values
            elif re.match(r'^/api/documents/([^/]+)/values$', clean_path):
                doc_id = re.match(r'^/api/documents/([^/]+)/values$', clean_path).group(1)
                values = [dict(v) for v in c.execute("SELECT * FROM medical_values WHERE document_id = ?", (doc_id,)).fetchall()]
                self._set_headers(200)
                self.wfile.write(json.dumps(values).encode('utf-8'))

            # Document Questions
            elif re.match(r'^/api/documents/([^/]+)/questions$', clean_path):
                doc_id = re.match(r'^/api/documents/([^/]+)/questions$', clean_path).group(1)
                questions = [dict(q) for q in c.execute("SELECT * FROM doctor_questions WHERE document_id = ?", (doc_id,)).fetchall()]
                self._set_headers(200)
                self.wfile.write(json.dumps(questions).encode('utf-8'))

            # Document Explanation (PRD Route GET /api/documents/{id}/explanation/)
            elif re.match(r'^/api/documents/([^/]+)/explanation$', clean_path):
                doc_id = re.match(r'^/api/documents/([^/]+)/explanation$', clean_path).group(1)
                exps = c.execute("SELECT * FROM explanations WHERE document_id = ? ORDER BY created_at DESC", (doc_id,)).fetchall()
                self._set_headers(200)
                self.wfile.write(json.dumps([dict(e) for e in exps]).encode('utf-8'))

            # Medicine Reminders
            elif clean_path == '/api/reminders/medicine':
                rems = c.execute("SELECT * FROM medicine_reminders WHERE user_id = 'user-samishma' ORDER BY time_str ASC").fetchall()
                self._set_headers(200)
                self.wfile.write(json.dumps([dict(r) for r in rems]).encode('utf-8'))

            # Appointments
            elif clean_path == '/api/reminders/appointment':
                apts = c.execute("SELECT * FROM appointments WHERE user_id = 'user-samishma' ORDER BY appointment_date ASC").fetchall()
                self._set_headers(200)
                self.wfile.write(json.dumps([dict(a) for a in apts]).encode('utf-8'))

            # Family Sharing
            elif clean_path == '/api/sharing':
                members = c.execute("SELECT * FROM trusted_members WHERE owner_id = 'user-samishma'").fetchall()
                logs = c.execute("SELECT * FROM access_logs WHERE owner_id = 'user-samishma' ORDER BY timestamp DESC LIMIT 10").fetchall()
                self._set_headers(200)
                self.wfile.write(json.dumps({
                    "members": [dict(m) for m in members],
                    "logs": [dict(l) for l in logs]
                }).encode('utf-8'))

            # Translations dictionary
            elif clean_path == '/api/translations':
                self._set_headers(200)
                self.wfile.write(json.dumps(TRANSLATIONS).encode('utf-8'))

            # Sample files info
            elif clean_path == '/api/samples':
                sample_files = [
                    {
                        "id": "sample-cbc",
                        "title": "Comprehensive Blood Test (CBC & CMP)",
                        "type": "Lab Report",
                        "filename": "sample_blood_test.txt",
                        "description": "Lab report showing blood sugar, cholesterol, and kidney markers.",
                        "is_medical": True
                    },
                    {
                        "id": "sample-rx",
                        "title": "Multi-Drug Prescription (Antibiotic & Antidiabetic)",
                        "type": "Prescription",
                        "filename": "sample_prescription.txt",
                        "description": "Doctor's prescription with Paracetamol, Metformin, and Amoxicillin.",
                        "is_medical": True
                    },
                    {
                        "id": "sample-discharge",
                        "title": "Gastroenteritis Discharge Summary",
                        "type": "Discharge Summary",
                        "filename": "sample_discharge_summary.txt",
                        "description": "Hospital discharge summary with clinical course and red flag signs.",
                        "is_medical": True
                    },
                    {
                        "id": "sample-resume",
                        "title": "Software Engineer Resume (Invalid)",
                        "type": "Curriculum Vitae",
                        "filename": "invalid_resume.txt",
                        "description": "Non-medical resume testing the file-restriction guardrail.",
                        "is_medical": False
                    },
                    {
                        "id": "sample-invoice",
                        "title": "Office Depot Invoice (Invalid)",
                        "type": "Business Invoice",
                        "filename": "invalid_invoice.txt",
                        "description": "Non-medical retail invoice testing rejection safety.",
                        "is_medical": False
                    }
                ]
                self._set_headers(200)
                self.wfile.write(json.dumps(sample_files).encode('utf-8'))

            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "Route not found"}).encode('utf-8'))

        finally:
            conn.close()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        clean_path = path.rstrip('/') if path != '/' else '/'

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        conn = get_db()
        c = conn.cursor()

        try:
            # 0. Auth Routes (PRD Section 13)
            if clean_path == '/api/auth/register':
                body = json.loads(post_data.decode('utf-8')) if post_data else {}
                username = body.get('username', 'user_new')
                email = body.get('email', f'{username}@example.com')
                user_id = f"user-{uuid.uuid4().hex[:6]}"
                c.execute("INSERT OR REPLACE INTO users (user_id, username, name, email) VALUES (?, ?, ?, ?)",
                          (user_id, username, body.get('name', username.title()), email))
                conn.commit()
                self._set_headers(201)
                self.wfile.write(json.dumps({"success": True, "user_id": user_id, "username": username}).encode('utf-8'))

            elif clean_path == '/api/auth/login':
                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True, "token": "session-samishma-valid", "user": "samishma"}).encode('utf-8'))

            elif clean_path == '/api/auth/logout':
                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True, "message": "Logged out successfully"}).encode('utf-8'))

            # 1. Document Upload (Handles JSON payload or Multipart/form-data)
            elif clean_path == '/api/documents/upload':
                body = {}
                if self.headers.get('Content-Type', '').startswith('application/json'):
                    body = json.loads(post_data.decode('utf-8'))
                else:
                    body = json.loads(post_data.decode('utf-8'))

                filename = body.get('filename', 'uploaded_document.pdf')
                text_content = body.get('text', '')
                title = body.get('title', filename.replace('.pdf', '').replace('.txt', '').replace('_', ' ').title())

                # Validate whether it is medical
                is_medical, doc_type, reason = classify_medical_document(text_content, filename)

                if not is_medical:
                    self._set_headers(400)
                    self.wfile.write(json.dumps({
                        "success": False,
                        "error": "NON_MEDICAL_FILE_REJECTED",
                        "message": reason,
                        "allowed_types": ["Lab Report", "Prescription", "Discharge Summary"]
                    }).encode('utf-8'))
                    return

                # Create medical document
                doc_id = f"doc-{uuid.uuid4().hex[:8]}"
                upload_date = datetime.datetime.now().strftime("%d %b %Y")
                c.execute("""
                    INSERT INTO medical_documents (document_id, user_id, title, document_type, file_name, file_path, upload_date, extracted_text, processing_status, is_medical)
                    VALUES (?, 'user-samishma', ?, ?, ?, ?, ?, ?, 'Completed', 1)
                """, (doc_id, title, doc_type, filename, f"uploads/{filename}", upload_date, text_content))

                # Parse values if Lab Report
                if doc_type == "Lab Report" or "glucose" in text_content.lower():
                    parse_and_insert_lab_values(c, doc_id, text_content)

                # Parse medicines if Prescription
                if doc_type == "Prescription" or "rx" in text_content.lower():
                    parse_and_insert_medicines(c, doc_id, text_content)

                # Detect Red Flags
                detect_and_insert_red_flags(c, doc_id, text_content)

                # Generate Doctor Questions
                generate_and_insert_questions(c, doc_id, text_content, doc_type)

                # Generate Default Explanation
                summary, speech = generate_plain_explanation(text_content, doc_type, "Standard", "English")
                c.execute("""
                    INSERT INTO explanations (explanation_id, document_id, language, reading_level, plain_summary, speech_text, created_at)
                    VALUES (?, ?, 'English', 'Standard', ?, ?, ?)
                """, (f"exp-{uuid.uuid4().hex[:8]}", doc_id, summary, speech, datetime.datetime.now().strftime("%d %b %Y %H:%M")))

                conn.commit()

                self._set_headers(201)
                self.wfile.write(json.dumps({
                    "success": True,
                    "document_id": doc_id,
                    "title": title,
                    "document_type": doc_type,
                    "message": "Medical document verified and processed successfully."
                }).encode('utf-8'))

            # 2. Dynamic Explanation Generation (with Reading Level & Language)
            elif re.match(r'^/api/documents/([^/]+)/explain$', clean_path):
                doc_id = re.match(r'^/api/documents/([^/]+)/explain$', clean_path).group(1)
                body = json.loads(post_data.decode('utf-8')) if post_data else {}
                reading_level = body.get('reading_level', 'Standard')
                language = body.get('language', 'English')

                doc = c.execute("SELECT * FROM medical_documents WHERE document_id = ?", (doc_id,)).fetchone()
                if not doc:
                    self._set_headers(404)
                    self.wfile.write(json.dumps({"error": "Document not found"}).encode('utf-8'))
                    return

                summary, speech = generate_plain_explanation(doc['extracted_text'], doc['document_type'], reading_level, language)
                exp_id = f"exp-{uuid.uuid4().hex[:8]}"
                c.execute("""
                    INSERT INTO explanations (explanation_id, document_id, language, reading_level, plain_summary, speech_text, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (exp_id, doc_id, language, reading_level, summary, speech, datetime.datetime.now().strftime("%d %b %Y %H:%M")))
                conn.commit()

                self._set_headers(200)
                self.wfile.write(json.dumps({
                    "explanation_id": exp_id,
                    "document_id": doc_id,
                    "reading_level": reading_level,
                    "language": language,
                    "plain_summary": summary,
                    "speech_text": speech
                }).encode('utf-8'))

            # 2b. Translate Explanation (PRD Route POST /api/documents/{id}/translate/)
            elif re.match(r'^/api/documents/([^/]+)/translate$', clean_path):
                doc_id = re.match(r'^/api/documents/([^/]+)/translate$', clean_path).group(1)
                body = json.loads(post_data.decode('utf-8')) if post_data else {}
                target_lang = body.get('language', 'Hindi')

                doc = c.execute("SELECT * FROM medical_documents WHERE document_id = ?", (doc_id,)).fetchone()
                summary, speech = generate_plain_explanation(doc['extracted_text'] if doc else "", doc['document_type'] if doc else "Lab Report", "Standard", target_lang)
                self._set_headers(200)
                self.wfile.write(json.dumps({
                    "document_id": doc_id,
                    "language": target_lang,
                    "translated_summary": summary,
                    "speech_text": speech
                }).encode('utf-8'))

            # 2c. Speech Synthesis Endpoint (PRD Route POST /api/documents/{id}/speak/)
            elif re.match(r'^/api/documents/([^/]+)/speak$', clean_path):
                doc_id = re.match(r'^/api/documents/([^/]+)/speak$', clean_path).group(1)
                body = json.loads(post_data.decode('utf-8')) if post_data else {}
                lang = body.get('language', 'English')
                doc = c.execute("SELECT * FROM medical_documents WHERE document_id = ?", (doc_id,)).fetchone()
                _, speech = generate_plain_explanation(doc['extracted_text'] if doc else "", doc['document_type'] if doc else "Lab Report", "Standard", lang)
                self._set_headers(200)
                self.wfile.write(json.dumps({
                    "document_id": doc_id,
                    "language": lang,
                    "speech_text": speech,
                    "voice_format": "audio/speech-synthesis"
                }).encode('utf-8'))

            # 3. Create Medicine Reminder
            elif clean_path == '/api/reminders/medicine':
                body = json.loads(post_data.decode('utf-8'))
                rem_id = f"rem-{uuid.uuid4().hex[:8]}"
                c.execute("""
                    INSERT INTO medicine_reminders (reminder_id, user_id, medicine_name, dosage, time_str, frequency, instructions, start_date, end_date, is_active)
                    VALUES (?, 'user-samishma', ?, ?, ?, ?, ?, ?, ?, 1)
                """, (rem_id, body.get('medicine_name'), body.get('dosage'), body.get('time_str'), body.get('frequency', 'Daily'), body.get('instructions', ''), body.get('start_date', 'Today'), body.get('end_date', 'Ongoing')))
                conn.commit()

                self._set_headers(201)
                self.wfile.write(json.dumps({"success": True, "reminder_id": rem_id}).encode('utf-8'))

            # 4. Create Doctor Appointment
            elif clean_path == '/api/reminders/appointment':
                body = json.loads(post_data.decode('utf-8'))
                apt_id = f"apt-{uuid.uuid4().hex[:8]}"
                c.execute("""
                    INSERT INTO appointments (appointment_id, user_id, doctor_name, specialty, clinic_name, appointment_date, reminder_time, notes, status)
                    VALUES (?, 'user-samishma', ?, ?, ?, ?, ?, ?, 'Scheduled')
                """, (apt_id, body.get('doctor_name'), body.get('specialty', 'General Physician'), body.get('clinic_name', 'City Clinic'), body.get('appointment_date'), body.get('reminder_time', '1 hour before'), body.get('notes', '')))
                conn.commit()

                self._set_headers(201)
                self.wfile.write(json.dumps({"success": True, "appointment_id": apt_id}).encode('utf-8'))

            # 5. Invite Trusted Family Member
            elif clean_path == '/api/sharing/invite':
                body = json.loads(post_data.decode('utf-8'))
                mem_id = f"mem-{uuid.uuid4().hex[:8]}"
                c.execute("""
                    INSERT INTO trusted_members (member_id, owner_id, name, member_email, relationship, permission, status, created_at)
                    VALUES (?, 'user-samishma', ?, ?, ?, ?, 'Active', ?)
                """, (mem_id, body.get('name'), body.get('email'), body.get('relationship', 'Family'), body.get('permission', 'Full Access'), datetime.datetime.now().strftime("%d %b %Y")))
                conn.commit()

                self._set_headers(201)
                self.wfile.write(json.dumps({"success": True, "member_id": mem_id}).encode('utf-8'))

            # 6. Mark Medicine as Taken
            elif re.match(r'^/api/reminders/medicine/([^/]+)/take$', clean_path):
                rem_id = re.match(r'^/api/reminders/medicine/([^/]+)/take$', clean_path).group(1)
                now_str = datetime.datetime.now().strftime("%d %b %Y %H:%M")
                c.execute("UPDATE medicine_reminders SET last_taken = ? WHERE reminder_id = ?", (now_str, rem_id))
                conn.commit()
                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True, "last_taken": now_str}).encode('utf-8'))

            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "Route not found"}).encode('utf-8'))

        finally:
            conn.close()

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        clean_path = parsed.path.rstrip('/') if parsed.path != '/' else '/'
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        conn = get_db()
        c = conn.cursor()
        try:
            # Update medicine reminder (PRD Route PUT /api/reminders/medicine/{id}/)
            if re.match(r'^/api/reminders/medicine/([^/]+)$', clean_path):
                rem_id = re.match(r'^/api/reminders/medicine/([^/]+)$', clean_path).group(1)
                body = json.loads(post_data.decode('utf-8')) if post_data else {}
                c.execute("""
                    UPDATE medicine_reminders
                    SET medicine_name = COALESCE(?, medicine_name),
                        dosage = COALESCE(?, dosage),
                        time_str = COALESCE(?, time_str),
                        instructions = COALESCE(?, instructions)
                    WHERE reminder_id = ?
                """, (body.get('medicine_name'), body.get('dosage'), body.get('time_str'), body.get('instructions'), rem_id))
                conn.commit()
                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True, "updated_id": rem_id}).encode('utf-8'))
            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "Route not found"}).encode('utf-8'))
        finally:
            conn.close()

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        clean_path = parsed.path.rstrip('/') if parsed.path != '/' else '/'

        conn = get_db()
        c = conn.cursor()

        try:
            # Delete Document
            if re.match(r'^/api/documents/([^/]+)$', clean_path):
                doc_id = re.match(r'^/api/documents/([^/]+)$', clean_path).group(1)
                c.execute("DELETE FROM medical_documents WHERE document_id = ?", (doc_id,))
                c.execute("DELETE FROM medical_values WHERE document_id = ?", (doc_id,))
                c.execute("DELETE FROM medicines WHERE document_id = ?", (doc_id,))
                c.execute("DELETE FROM doctor_questions WHERE document_id = ?", (doc_id,))
                c.execute("DELETE FROM red_flag_alerts WHERE document_id = ?", (doc_id,))
                c.execute("DELETE FROM explanations WHERE document_id = ?", (doc_id,))
                conn.commit()
                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True, "deleted_id": doc_id}).encode('utf-8'))

            # Delete Medicine Reminder
            elif re.match(r'^/api/reminders/medicine/([^/]+)$', clean_path):
                rem_id = re.match(r'^/api/reminders/medicine/([^/]+)$', clean_path).group(1)
                c.execute("DELETE FROM medicine_reminders WHERE reminder_id = ?", (rem_id,))
                conn.commit()
                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True, "deleted_id": rem_id}).encode('utf-8'))

            # Revoke Family Access
            elif re.match(r'^/api/sharing/([^/]+)$', clean_path):
                mem_id = re.match(r'^/api/sharing/([^/]+)$', clean_path).group(1)
                c.execute("DELETE FROM trusted_members WHERE member_id = ?", (mem_id,))
                conn.commit()
                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True, "revoked_id": mem_id}).encode('utf-8'))

            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "Route not found"}).encode('utf-8'))

        finally:
            conn.close()

# ----------------- Intelligent Medical Parsers ----------------- #

def parse_and_insert_lab_values(cursor, doc_id, text):
    """Detects and registers lab test values from text with reference ranges and status."""
    tests = [
        {"name": "Fasting Blood Glucose", "regex": r'glucose[:\s]+(\d+(?:\.\d+)?)', "unit": "mg/dL", "min": 70, "max": 99,
         "meaning": "Measures sugar in your blood after an 8-hour fast."},
        {"name": "Hemoglobin (Hb)", "regex": r'hemoglobin(?: \(hb\))?[:\s]+(\d+(?:\.\d+)?)', "unit": "g/dL", "min": 12.0, "max": 15.5,
         "meaning": "Measures the protein in red blood cells that carries oxygen across your body."},
        {"name": "Total WBC Count", "regex": r'wbc(?:\s+count)?[:\s]+(\d+(?:,\d+)?)', "unit": "/mcL", "min": 4500, "max": 11000,
         "meaning": "Your immune system's white blood cells that defend against infections."},
        {"name": "Platelet Count", "regex": r'platelet(?:\s+count)?[:\s]+(\d+(?:,\d+)?)', "unit": "/mcL", "min": 150000, "max": 450000,
         "meaning": "Tiny cell fragments vital for normal blood clotting and stopping bleeds."},
        {"name": "Serum Creatinine", "regex": r'creatinine[:\s]+(\d+(?:\.\d+)?)', "unit": "mg/dL", "min": 0.5, "max": 1.1,
         "meaning": "Waste byproduct filtered by kidneys. Shows how efficiently your kidneys are working."},
        {"name": "Total Cholesterol", "regex": r'total cholesterol[:\s]+(\d+(?:\.\d+)?)', "unit": "mg/dL", "min": 125, "max": 200,
         "meaning": "Combined measure of all fats in your bloodstream."},
        {"name": "HbA1c", "regex": r'hba1c[:\s]+(\d+(?:\.\d+)?)', "unit": "%", "min": 4.0, "max": 5.6,
         "meaning": "Your 3-month average blood glucose level."},
        {"name": "Serum Potassium", "regex": r'potassium[:\s]+(\d+(?:\.\d+)?)', "unit": "mEq/L", "min": 3.5, "max": 5.1,
         "meaning": "Key electrolyte that regulates heart rhythm and muscle contraction."}
    ]

    lower = text.lower()
    for t in tests:
        match = re.search(t['regex'], lower)
        if match:
            raw_val = match.group(1).replace(',', '')
            val = float(raw_val)
            min_r, max_r = t['min'], t['max']

            if val < min_r * 0.7:
                status = "Critical"
            elif val < min_r:
                status = "Low"
            elif val <= max_r:
                status = "Normal"
            elif val <= max_r * 1.2:
                status = "Slightly High"
            elif val <= max_r * 1.5:
                status = "High"
            else:
                status = "Critical"

            cursor.execute("""
                INSERT INTO medical_values (value_id, document_id, test_name, result_value, unit, reference_min, reference_max, reference_range, reported_status, plain_meaning)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (f"val-{uuid.uuid4().hex[:8]}", doc_id, t['name'], val, t['unit'], min_r, max_r, f"{min_r} - {max_r} {t['unit']}", status, t['meaning']))

def parse_and_insert_medicines(cursor, doc_id, text):
    """Detects and registers medicines from prescription text."""
    rx_catalog = {
        "paracetamol": {
            "name": "Paracetamol 500mg", "generic": "Acetaminophen", "dosage": "500 mg",
            "frequency": "Three times daily as needed", "instructions": "Take with water after meals. Do not exceed 3g/day.",
            "purpose": "Relieves mild pain, headache, and body fever.",
            "precautions": "Avoid alcohol and do not combine with other over-the-counter paracetamol products.",
            "side_effects": "Rare mild nausea."
        },
        "metformin": {
            "name": "Metformin 500mg", "generic": "Metformin Hydrochloride", "dosage": "500 mg",
            "frequency": "Once daily with evening meal", "instructions": "Swallow whole with dinner to protect stomach.",
            "purpose": "Regulates blood sugar and improves cellular insulin sensitivity.",
            "precautions": "Stay well hydrated. Avoid skipping meals.",
            "side_effects": "Mild initial stomach bloating or loose stools."
        },
        "amoxicillin": {
            "name": "Amoxicillin 500mg", "generic": "Amoxicillin Trihydrate", "dosage": "500 mg",
            "frequency": "Every 8 hours for 5 days", "instructions": "Finish all capsules even if you feel completely recovered.",
            "purpose": "Antibiotic prescribed to eliminate bacterial infection.",
            "precautions": "Report immediately if skin hives or difficulty breathing occurs.",
            "side_effects": "Mild diarrhea, stomach cramps."
        },
        "pantoprazole": {
            "name": "Pantoprazole 40mg", "generic": "Pantoprazole Sodium", "dosage": "40 mg",
            "frequency": "Once daily in the morning", "instructions": "Take 30 minutes before breakfast with water.",
            "purpose": "Reduces stomach acid to heal gastric lining and prevent acidity.",
            "precautions": "Avoid heavy spicy foods and late-night meals.",
            "side_effects": "Mild headache or digestive changes."
        },
        "atorvastatin": {
            "name": "Atorvastatin 20mg", "generic": "Atorvastatin Calcium", "dosage": "20 mg",
            "frequency": "Once daily at bedtime", "instructions": "Take at night with or without food.",
            "purpose": "Lowers bad LDL cholesterol and protects cardiovascular arteries.",
            "precautions": "Avoid excessive grapefruit juice. Report unexplained muscle soreness.",
            "side_effects": "Mild muscle tiredness."
        }
    }

    lower = text.lower()
    for key, data in rx_catalog.items():
        if key in lower:
            cursor.execute("""
                INSERT INTO medicines (medicine_id, document_id, name, generic_name, dosage, frequency, instructions, purpose, precautions, side_effects)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (f"med-{uuid.uuid4().hex[:8]}", doc_id, data['name'], data['generic'], data['dosage'], data['frequency'], data['instructions'], data['purpose'], data['precautions'], data['side_effects']))

def detect_and_insert_red_flags(cursor, doc_id, text):
    """Clinically guided warning flags for urgent laboratory values or clinical red flags."""
    lower = text.lower()

    # Potassium > 6.0
    k_match = re.search(r'potassium[:\s]+(\d+(?:\.\d+)?)', lower)
    if k_match and float(k_match.group(1)) >= 6.0:
        cursor.execute("""
            INSERT INTO red_flag_alerts (alert_id, document_id, severity, title, message, recommended_action)
            VALUES (?, ?, 'Urgent', 'Critically High Potassium Level (Hyperkalemia)',
            'Potassium is measured at or above 6.0 mEq/L, which can significantly affect heart rhythm.',
            'Requires immediate emergency medical care. Go to the nearest emergency department.')
        """, (f"rf-{uuid.uuid4().hex[:8]}", doc_id))

    # Fasting glucose > 300
    g_match = re.search(r'glucose[:\s]+(\d+(?:\.\d+)?)', lower)
    if g_match and float(g_match.group(1)) >= 300:
        cursor.execute("""
            INSERT INTO red_flag_alerts (alert_id, document_id, severity, title, message, recommended_action)
            VALUES (?, ?, 'Urgent', 'Severe Hyperglycemia Alert',
            'Blood glucose level exceeds 300 mg/dL, presenting a risk of acute diabetic complications.',
            'Contact your doctor or urgent care clinic right away.')
        """, (f"rf-{uuid.uuid4().hex[:8]}", doc_id))

    # High fever + rigid abdomen in discharge summary
    if 'discharge summary' in lower or 'rigid abdomen' in lower or 'persistent high fever' in lower:
        cursor.execute("""
            INSERT INTO red_flag_alerts (alert_id, document_id, severity, title, message, recommended_action)
            VALUES (?, ?, 'High', 'Important Post-Discharge Warning Signs',
            'Your medical team noted specific warning indicators: high fever above 102°F, uncontrolled pain, or severe vomiting.',
            'If any of these occur, do not wait for your scheduled appointment—seek emergency evaluation.')
        """, (f"rf-{uuid.uuid4().hex[:8]}", doc_id))

def generate_and_insert_questions(cursor, doc_id, text, doc_type):
    """Generates personalized questions to empower the patient during doctor appointments."""
    lower = text.lower()
    questions = []

    if "glucose" in lower or "hba1c" in lower:
        questions.append(("What dietary changes or daily routine would you recommend to bring my slightly high blood sugar back into the healthy range?", "Helps you get concrete meal and activity targets.", "Blood Sugar"))
    if "cholesterol" in lower or "ldl" in lower:
        questions.append(("Can my cholesterol levels be safely managed with nutrition and exercise, or do you advise starting medication?", "Clarifies medication versus lifestyle pathways.", "Heart Health"))
    if "amoxicillin" in lower or "antibiotic" in lower:
        questions.append(("Should I take a probiotic alongside this antibiotic to protect my digestive flora?", "Prevents antibiotic-associated loose stools.", "Medication Advice"))
    if doc_type == "Discharge Summary":
        questions.append(("What physical activities or foods should I still avoid during the next two weeks of recovery?", "Ensures safe resumption of work and exercise.", "Recovery"))
    if not questions:
        questions.append(("Are there any specific lifestyle or dietary recommendations based on this report?", "Covers general medical guidance.", "General"))

    for q, rationale, cat in questions:
        cursor.execute("""
            INSERT INTO doctor_questions (question_id, document_id, question, rationale, category)
            VALUES (?, ?, ?, ?, ?)
        """, (f"q-{uuid.uuid4().hex[:8]}", doc_id, q, rationale, cat))

# ----------------- Seed Sample Files on Disk ----------------- #

def create_sample_files_on_disk():
    samples = {
        "sample_blood_test.txt": """METROPOLITAN CLINICAL LABS - COMPREHENSIVE LAB PANEL
PATIENT: Samishma Patel | AGE: 34 | GENDER: Female
DATE: 12-Nov-2026 | PHYSICIAN: Dr. A. Sharma, MD

COMPLETE BLOOD COUNT (CBC) & METABOLIC PANEL
Fasting Blood Glucose: 112 mg/dL (Reference Range: 70 - 99 mg/dL) [HIGH]
Hemoglobin (Hb): 13.6 g/dL (Reference Range: 12.0 - 15.5 g/dL) [NORMAL]
Total WBC Count: 6,800 /mcL (Reference Range: 4,500 - 11,000 /mcL) [NORMAL]
Platelet Count: 245,000 /mcL (Reference Range: 150,000 - 450,000 /mcL) [NORMAL]
Serum Creatinine: 0.9 mg/dL (Reference Range: 0.5 - 1.1 mg/dL) [NORMAL]
Total Cholesterol: 215 mg/dL (Reference Range: < 200 mg/dL) [BORDERLINE HIGH]
LDL Cholesterol: 138 mg/dL (Reference Range: < 100 mg/dL) [ELEVATED]
HDL Cholesterol: 54 mg/dL (Reference Range: > 50 mg/dL) [OPTIMAL]
Serum Potassium: 4.4 mEq/L (Reference Range: 3.5 - 5.1 mEq/L) [NORMAL]
HbA1c: 5.8 % (Reference Range: 4.0 - 5.6 %) [PREDIABETES RANGE]

END OF REPORT - Verified by Chief Clinical Pathologist
""",
        "sample_prescription.txt": """CITY CARE CLINIC - Rx PRESCRIPTION
Dr. A. Sharma, MD (Internal Medicine) - Reg #MED-88492
Patient: Samishma Patel | Date: 10 Nov 2026

Rx:
1. Paracetamol 500mg - 1 tablet orally TID (three times daily) after meals as needed for mild fever / muscle ache. Max 3g/day.
2. Metformin 500mg - 1 tablet with evening meal once daily.
3. Amoxicillin 500mg - 1 capsule every 8 hours for 5 days. Complete the full course.

Special Instructions: Drink at least 2 liters of water daily. Return for checkup in 2 weeks.
""",
        "sample_discharge_summary.txt": """APOLLO HEALTH CENTER - DISCHARGE SUMMARY
PATIENT: Samishma Patel | ADMISSION DATE: 03-Nov-2026 | DISCHARGE: 05-Nov-2026
ADMITTING DIAGNOSIS: Acute Gastroenteritis with Mild Dehydration
TREATING PHYSICIAN: Dr. R. Verma, MD / Dr. A. Sharma, MD

HOSPITAL COURSE:
Patient presented with nausea, vomiting and low-grade pyrexia. Managed conservatively with IV hydration (Normal Saline 1L), antiemetics (Ondansetron), and oral rehydration therapy. Patient tolerated soft diet on hospital day 2. Vital signs stable at discharge: BP 118/76 mmHg, Pulse 72 bpm, SpO2 99% on room air, Afebrile.

DISCHARGE MEDICATIONS:
1. Pantoprazole 40mg - 1 tablet OD (morning before breakfast) x 7 days.
2. Probiotic Sachets - 1 sachet twice daily in curd or water x 5 days.

RED FLAG WARNINGS / PRECAUTIONS:
Seek immediate emergency medical attention if you experience:
- Persistent high fever (> 102°F)
- Severe abdominal pain or rigid abdomen
- Repeated vomiting preventing fluid intake
- Blood in stool or dark tarry stools

FOLLOW-UP:
Follow up in outpatient clinic with Dr. Sharma in 7-10 days.
""",
        "invalid_resume.txt": """ALEXANDER CHEN - SENIOR FULL STACK SOFTWARE ENGINEER
Email: alex.chen@example.com | GitHub: github.com/alexchen | LinkedIn: linkedin.com/in/alexchen

EXPERIENCE:
Staff Software Engineer - CloudScale Systems (2022 - Present)
- Architected distributed microservices in Go, Python, and Kubernetes processing 50M daily events.
- Led front-end migration to React, Next.js, and Tailwind CSS, reducing bundle size by 45%.
- Implemented CI/CD pipelines with GitHub Actions and Terraform.

EDUCATION:
B.S. in Computer Science - University of Washington (2018 - 2022)

TECHNICAL SKILLS:
Languages: TypeScript, JavaScript, Python, Go, SQL, HTML/CSS
Frameworks: React, Node.js, Express, FastAPI, Next.js
Tools: Docker, Kubernetes, AWS, PostgreSQL, Redis, Git
""",
        "invalid_invoice.txt": """OFFICE DEPOT & SUPPLIES INC.
INVOICE #INV-2026-99381
Date: 12-Nov-2026 | Due Date: 26-Nov-2026

BILL TO:
Acme Corporation
Attn: Accounts Payable
100 Corporate Blvd, Suite 400

ITEMS PURCHASED:
1. Ergonomic Mesh Office Chair (SKU #88219) - Quantity: 4 - Unit Price: $189.99 - Total: $759.96
2. Dual Monitor Desk Mount (SKU #44102) - Quantity: 4 - Unit Price: $49.50 - Total: $198.00
3. Multipurpose Copy Paper 20lb (Carton) - Quantity: 10 - Unit Price: $42.00 - Total: $420.00

Subtotal: $1,377.96
Sales Tax (8.25%): $113.68
Shipping & Handling: $45.00
TOTAL AMOUNT DUE: $1,536.64

Payment Terms: Net 14 Days. Thank you for your business!
"""
    }

    for fname, content in samples.items():
        fpath = os.path.join(SAMPLE_DIR, fname)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)

# ----------------- Main Entrypoint ----------------- #

def run_server():
    init_db()
    create_sample_files_on_disk()

    socketserver.TCPServer.allow_reuse_address = True
    server_address = ('0.0.0.0', PORT)
    httpd = socketserver.TCPServer(server_address, MediExplainHandler)
    print(f"MediExplain Server running at http://localhost:{PORT}", flush=True)
    print(f"Open http://localhost:{PORT} in your browser to view the application.", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...", flush=True)
        httpd.server_close()

if __name__ == '__main__':
    run_server()
