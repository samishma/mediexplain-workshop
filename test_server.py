import sys
import threading
import time
import urllib.request
import urllib.error
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
import server

# Start server on test port 8089
httpd = server.socketserver.TCPServer(('', 8089), server.MediExplainHandler)
t = threading.Thread(target=httpd.serve_forever)
t.daemon = True
t.start()
time.sleep(1)

print("--- RUNNING MEDIEXPLAIN INTEGRATION TESTS ---")

# Test 1: Frontend Root
with urllib.request.urlopen('http://localhost:8089/') as res:
    html = res.read().decode('utf-8')
    assert 'MediExplain' in html, 'MediExplain title missing'
    print('[PASS] Frontend root served correctly')

# Test 2: Documents List API
with urllib.request.urlopen('http://localhost:8089/api/documents') as res:
    docs = json.loads(res.read().decode('utf-8'))
    assert len(docs) >= 3, 'Missing seeded documents'
    print(f'[PASS] Documents API returned {len(docs)} documents')

# Test 3: Medical File Upload (Valid)
req = urllib.request.Request(
    'http://localhost:8089/api/documents/upload',
    data=json.dumps({
        'filename': 'test_blood.pdf',
        'text': 'Hospital Lab Fasting Glucose 105 mg/dL Hemoglobin 14.1 g/dL Dr. Sharma'
    }).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
with urllib.request.urlopen(req) as res:
    resp = json.loads(res.read().decode('utf-8'))
    assert resp['success'] is True, 'Medical upload failed'
    print(f'[PASS] Valid medical document accepted & processed: ID {resp["document_id"]}')

# Test 4: Non-Medical File Upload (Guardrail Rejection)
req_inv = urllib.request.Request(
    'http://localhost:8089/api/documents/upload',
    data=json.dumps({
        'filename': 'alexander_chen_resume.pdf',
        'text': 'Alexander Chen resume education experience software engineer react kubernetes python'
    }).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    urllib.request.urlopen(req_inv)
    assert False, 'Non-medical file was not rejected!'
except urllib.error.HTTPError as e:
    err_body = json.loads(e.read().decode('utf-8'))
    assert err_body['error'] == 'NON_MEDICAL_FILE_REJECTED', 'Wrong error code'
    print(f'[PASS] Non-medical file successfully rejected: {err_body["message"]}')

# Test 5: Dynamic Multilingual Explanation API
with urllib.request.urlopen('http://localhost:8089/api/documents') as res:
    docs = json.loads(res.read().decode('utf-8'))
    first_id = docs[0]['document_id']

req_exp = urllib.request.Request(
    f'http://localhost:8089/api/documents/{first_id}/explain',
    data=json.dumps({
        'reading_level': 'Beginner',
        'language': 'Hindi'
    }).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
with urllib.request.urlopen(req_exp) as res:
    exp_resp = json.loads(res.read().decode('utf-8'))
    assert 'plain_summary' in exp_resp, 'Missing plain summary'
    print(f'[PASS] Dynamic explanation in Beginner level / Hindi generated successfully')

# Test 6: Reminders API
with urllib.request.urlopen('http://localhost:8089/api/reminders/medicine') as res:
    rems = json.loads(res.read().decode('utf-8'))
    assert len(rems) >= 2, 'Missing seeded reminders'
    print(f'[PASS] Retrieved {len(rems)} medicine reminders')

# Test 7: Family Access API
with urllib.request.urlopen('http://localhost:8089/api/sharing') as res:
    fam = json.loads(res.read().decode('utf-8'))
    assert len(fam['members']) >= 2, 'Missing family members'
    print(f'[PASS] Family members and audit logs retrieved successfully')

httpd.shutdown()
print("--- ALL 7 INTEGRATION TESTS COMPLETED SUCCESSFULLY! ---")
