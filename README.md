# MediExplain - Medical Document Understanding & Reminder Assistant (MVP)

> **"Better understanding for a healthier you."**  
> An agentic, patient-centered application designed to demystify medical jargon in lab reports, prescriptions, and discharge summaries, prevent missed medication doses, curb unnecessary panic over borderline test results, and empower patients with multilingual audio explanations, doctor visit questions, and family caregiver access.

---

## 🌟 Key Features Implemented

| Feature | Description | Implementation Details |
| :--- | :--- | :--- |
| **Plain Language Terms** | Explains complex medical jargon, lab parameters, and Latin abbreviations (`TID`, `OD`, `PRN`) in simple, clear, and reassuring everyday terms. | Rule-grounded NLP engine converting biochemical jargon into understandable physiological explanations. |
| **Multiple Languages** | Supports English, Hindi (हिन्दी), Kannada (ಕನ್ನಡ), Spanish (Español), and French (Français). | Real-time localization of the entire dashboard, explanations, speech synthesis, and alert notices. |
| **Strict Medical File Restriction** | Strict guardrail: Accepts **only** valid medical documents (Lab Reports, Prescriptions, Discharge Summaries) and firmly rejects unrelated documents (resumes, invoices, receipts, tax forms). | Dual-phase keyword and structural validation rejecting non-medical files with explicit patient-friendly warnings. |
| **Text-to-Voice (TTS)** | High-fidelity speech synthesis reading the plain-language summary aloud in the patient's selected language. | Integrated with HTML5 Web Speech API (`SpeechSynthesis`) with Play, Pause, Resume, Stop, and Speed controls (0.8x, 1.0x, 1.2x). |
| **Access to Close Members** | Enables patients to share records with trusted family members or caregivers (e.g. Spouse, Adult Child, Physician) with granular permissions and instant revocation. | Role-based sharing permissions (`Full Access`, `Lab Only`, `Prescriptions Only`, `Emergency Only`) with access audit logging. |
| **Pop-up Messages & Reminders** | Interactive pop-up alerts and audio chimes for medicine doses and doctor appointments. | Web Audio API harmonic chime synthesis, modal alerts with "Mark as Taken" adherence tracking and "Snooze 10m" options. |
| **History of Individual** | Organized archive of past uploaded reports filterable by category (`Lab Report`, `Prescription`, `Discharge Summary`) with full search. | SQLite persistent medical record storage tracking test dates, physicians, and timeline trends. |
| **Value Status & Range Gauges** | Displays extracted test values with original units, reference ranges, and color-coded status badges (`Normal`, `Slightly High`, `High`, `Critical`). | Visual horizontal position gauge showing exactly where the patient's score sits relative to healthy bounds. |
| **Medicine Explainer** | Dedicated cards for each medication explaining brand vs generic names, clinical purpose, exact dosage schedules, food precautions, and side effects. | Structured pharmaceutical dictionary providing plain-word guidance (e.g., Paracetamol, Metformin, Amoxicillin, Pantoprazole). |
| **Questions for Your Doctor** | Generates 3–5 personalized, high-yield questions based on the patient's specific abnormal lab numbers or new medications. | Interactive checklist where patients can check off questions during appointments or click "Copy Checklist" to paste into notes or print. |
| **Reading Level Selection** | 3 tailored literacy tiers: **Beginner** (5th-grade analogies, zero jargon), **Standard** (8th-grade friendly), and **Detailed** (in-depth physiological ranges). | Dynamic summary generator adapting sentence complexity and clinical granularity to the user's preference. |
| **Red Flag Alerts** | Clinically reviewed warning alerts for urgent or critical lab findings (e.g. Potassium >= 6.0 mEq/L, glucose > 300 mg/dL, post-discharge warning signs). | Prominent emergency warning banner providing clear guidance to contact medical professionals immediately. |
| **Safety & Medical Disclaimer** | Clear, persistent non-diagnostic disclaimer emphasizing that MediExplain explains information and does not replace qualified physicians. | Displayed across the footer, modals, and report headers in accordance with clinical safety guidelines. |

---

## 🚀 How to Run the Application

### Option A: Using the 1-Click Batch Script
Double-click `run.bat` inside `C:\Users\samis\.gemini\antigravity\scratch\mediexplain\`.

### Option B: Using the Command Line
```powershell
cd C:\Users\samis\.gemini\antigravity\scratch\mediexplain
python server.py
```

Then open your browser and navigate to:
```
http://localhost:8080
```

---

## 🧪 Testing the Features (Live Demo Walkthrough)

1. **Medical Guardrail Test (Strict Rejection)**:
   - On the Dashboard, under the upload box, click **`+ Non-Medical File (Test Guardrail)`** or upload a resume / invoice.
   - The system intercepts the upload and opens the **Medical Document Guardrail** modal, stating why the file was rejected and listing accepted categories.
2. **Lab Report Understanding & Value Gauges**:
   - Click on the seeded **Blood Test Report** from the recent reports list or click **`+ Lab Report`**.
   - Inspect the **Value Status** table: notice **Fasting Blood Glucose (112 mg/dL)** and **Total Cholesterol (215 mg/dL)** highlighted as `Slightly High` with reassurance that these are early lifestyle warning signs, not emergencies.
   - View the visual slider gauge showing their position relative to normal ranges.
3. **Multilingual Speech & Reading Levels**:
   - In the report modal, switch reading level between **Beginner**, **Standard**, and **Detailed** to see the explanation adapt dynamically.
   - Use the language selector at the top-right to choose **हिन्दी (Hindi)** or **ಕನ್ನಡ (Kannada)**.
   - Click **`Listen Aloud`** to hear the browser read the explanation in the target language!
4. **Interactive Dose Reminders**:
   - Click the bell icon at the top right and select **`Test Pop-up`** (or go to the **Reminders** tab).
   - An audio chime rings, and the dose reminder modal pops up with options to **Mark as Taken** or **Snooze 10m**.
5. **Medicine Explainer**:
   - Navigate to **Medicine Explainer** on the sidebar to see detailed plain-language guides for Paracetamol, Metformin, Amoxicillin, etc.
6. **Family & Caregiver Access**:
   - Navigate to **Family Access** on the sidebar to view authorized members (Rahul Patel, Dr. Anita Desai), configure scopes, or test revoking access.
7. **Doctor Questions Checklist**:
   - Open any report and click **`Copy Checklist`** to copy customized discussion questions ready for your next doctor appointment.
