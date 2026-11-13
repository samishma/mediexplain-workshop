import sys
import os
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
import server

def run_unit_tests():
    print("=== STARTING MEDIEXPLAIN UNIT TESTS ===")
    
    # Test 1: Database Initialization & Seed Integrity
    server.init_db()
    conn = server.get_db()
    c = conn.cursor()
    
    docs = c.execute("SELECT * FROM medical_documents").fetchall()
    assert len(docs) >= 3, f"Expected at least 3 documents, got {len(docs)}"
    print(f"[PASS] Seed verification: {len(docs)} documents loaded successfully")

    # Test 2: Medical Document Classifier - Valid Lab Report
    valid_text_1 = "Metropolitan Clinical Labs - Patient Samishma Patel - Fasting Blood Glucose 112 mg/dL. Dr. Sharma."
    is_med, doc_type, reason = server.classify_medical_document(valid_text_1, "blood_test.pdf")
    assert is_med is True, f"Expected medical=True, got {is_med} ({reason})"
    assert doc_type == "Lab Report", f"Expected Lab Report, got {doc_type}"
    print(f"[PASS] Classifier (Lab Report): Accepted as '{doc_type}'")

    # Test 3: Medical Document Classifier - Valid Prescription
    valid_text_2 = "City Care Clinic - Rx: Paracetamol 500mg TID. Metformin 500mg OD. Amoxicillin 500mg. Dr. Sharma."
    is_med, doc_type, reason = server.classify_medical_document(valid_text_2, "prescription.pdf")
    assert is_med is True, f"Expected medical=True, got {is_med}"
    assert doc_type == "Prescription", f"Expected Prescription, got {doc_type}"
    print(f"[PASS] Classifier (Prescription): Accepted as '{doc_type}'")

    # Test 4: Medical Document Classifier - Valid Discharge Summary
    valid_text_3 = "Apollo Hospital Discharge Summary - Admitting Diagnosis: Acute Gastroenteritis. Hospital Course: Stable."
    is_med, doc_type, reason = server.classify_medical_document(valid_text_3, "discharge.pdf")
    assert is_med is True, f"Expected medical=True, got {is_med}"
    assert doc_type == "Discharge Summary", f"Expected Discharge Summary, got {doc_type}"
    print(f"[PASS] Classifier (Discharge Summary): Accepted as '{doc_type}'")

    # Test 5: Medical Guardrail - Non-Medical File Rejection (Resume)
    resume_text = "Alexander Chen - Senior Full Stack Software Engineer. Skills: Python, React, Kubernetes, AWS, Git. Education: B.S. in Computer Science."
    is_med, doc_type, reason = server.classify_medical_document(resume_text, "alex_chen_resume.pdf")
    assert is_med is False, f"Expected rejection for resume, but was accepted!"
    print(f"[PASS] Guardrail Rejection (Resume): Successfully rejected with message: '{reason}'")

    # Test 6: Medical Guardrail - Non-Medical File Rejection (Invoice)
    invoice_text = "Office Depot Invoice #88391. Bill To: Acme Corp. Ergonomic chair, dual monitor desk mount, copy paper carton. Total: $1,536."
    is_med, doc_type, reason = server.classify_medical_document(invoice_text, "office_depot_invoice.pdf")
    assert is_med is False, f"Expected rejection for invoice, but was accepted!"
    print(f"[PASS] Guardrail Rejection (Invoice): Successfully rejected with message: '{reason}'")

    # Test 7: Plain Language Explanation & Reading Levels
    lab_text = "Fasting Blood Glucose: 112 mg/dL. Hemoglobin: 13.6 g/dL. Total Cholesterol: 215 mg/dL."
    
    summary_beg, speech_beg = server.generate_plain_explanation(lab_text, "Lab Report", "Beginner", "English")
    assert "blood test" in summary_beg.lower() or "vegetables" in summary_beg.lower()
    print("[PASS] Plain Language Generator: Beginner level generated")

    summary_std, speech_std = server.generate_plain_explanation(lab_text, "Lab Report", "Standard", "English")
    assert "112" in summary_std and "cholesterol" in summary_std.lower()
    print("[PASS] Plain Language Generator: Standard level generated")

    summary_det, speech_det = server.generate_plain_explanation(lab_text, "Lab Report", "Detailed", "English")
    assert "physiological" in summary_det.lower() or "hematological" in summary_det.lower() or "prediabetes" in summary_det.lower()
    print("[PASS] Plain Language Generator: Detailed level generated")

    # Test 8: Multilingual Translation Support
    summary_hi, speech_hi = server.generate_plain_explanation(lab_text, "Lab Report", "Standard", "Hindi")
    assert "[हिन्दी अनुवाद]" in summary_hi or "नमस्ते" in speech_hi
    print("[PASS] Multilingual Generator: Hindi translation generated")

    summary_kn, speech_kn = server.generate_plain_explanation(lab_text, "Lab Report", "Standard", "Kannada")
    assert "[ಕನ್ನಡ ಅನುವಾದ]" in summary_kn or "ನಮಸ್ಕಾರ" in speech_kn
    print("[PASS] Multilingual Generator: Kannada translation generated")

    # Test 9: Value Status & Red Flag Detection
    test_doc_id = "test-doc-critical"
    c.execute("INSERT OR REPLACE INTO medical_documents (document_id, user_id, title, document_type, upload_date, extracted_text) VALUES (?, 'user-samishma', 'Urgent Lab', 'Lab Report', '13 Nov 2026', ?)",
              (test_doc_id, "Critical Panel: Serum Potassium 6.3 mEq/L. Fasting Glucose 320 mg/dL."))
    server.detect_and_insert_red_flags(c, test_doc_id, "Critical Panel: Serum Potassium 6.3 mEq/L. Fasting Glucose 320 mg/dL.")
    server.parse_and_insert_lab_values(c, test_doc_id, "Serum Potassium: 6.3 mEq/L. Fasting Blood Glucose: 320 mg/dL.")
    
    alerts = c.execute("SELECT * FROM red_flag_alerts WHERE document_id = ?", (test_doc_id,)).fetchall()
    assert len(alerts) >= 2, f"Expected 2 red flags, got {len(alerts)}"
    print(f"[PASS] Red Flag Alert Detector: Detected {len(alerts)} critical clinical warnings (Potassium & Glucose)")

    # Test 10: Doctor Questions Generator
    server.generate_and_insert_questions(c, test_doc_id, "Serum Potassium 6.3 mEq/L. Glucose 320 mg/dL.", "Lab Report")
    questions = c.execute("SELECT * FROM doctor_questions WHERE document_id = ?", (test_doc_id,)).fetchall()
    assert len(questions) >= 1, "Expected doctor questions"
    print(f"[PASS] Doctor Questions Generator: Created {len(questions)} high-yield discussion questions")

    # Clean up test doc
    c.execute("DELETE FROM medical_documents WHERE document_id = ?", (test_doc_id,))
    c.execute("DELETE FROM red_flag_alerts WHERE document_id = ?", (test_doc_id,))
    c.execute("DELETE FROM medical_values WHERE document_id = ?", (test_doc_id,))
    c.execute("DELETE FROM doctor_questions WHERE document_id = ?", (test_doc_id,))
    conn.commit()
    conn.close()

    print("=== ALL 10 UNIT & LOGIC TESTS PASSED WITHOUT ERRORS! ===")

if __name__ == '__main__':
    run_unit_tests()
