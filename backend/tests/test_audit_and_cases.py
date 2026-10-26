import io
import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_db

client = TestClient(app)

def test_case_crud_and_evidence_linking():
    # 1. Create a case
    case_no = f"FIR-2026-TEST-{uuid.uuid4().hex[:6].upper()}"
    create_res = client.post("/api/v1/cases", json={
        "case_number": case_no,
        "title": "Unit Test Investigation Case",
        "description": "Verification of case-evidence linking and audit trails",
        "priority": "high",
        "category": "Image Forensics",
        "assigned_to": ["Inspector Test"],
        "organization_id": "Unit Test Org",
    })
    assert create_res.status_code == 201
    case_data = create_res.json()
    assert case_data["case_number"] == case_no

    # 2. Check case is in list
    list_res = client.get("/api/v1/cases")
    assert list_res.status_code == 200
    all_cases = list_res.json()
    assert any(c["case_number"] == case_no for c in all_cases)

    # 3. Check case evidence list is initially empty
    ev_res = client.get(f"/api/v1/cases/{case_no}/evidence")
    assert ev_res.status_code == 200
    assert len(ev_res.json()) == 0

    # 4. Upload an evidence item with case_id set to this case
    # Create a small valid 1x1 JPEG
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), color="blue").save(buf, format="JPEG")
    jpeg_bytes = buf.getvalue()

    upload_res = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("test_linked.jpg", jpeg_bytes, "image/jpeg")},
        data={"case_id": case_no},
    )
    assert upload_res.status_code == 201
    ev_item = upload_res.json()
    assert ev_item["case_id"] == case_no

    # 5. Check case evidence list now contains this evidence item
    ev_res2 = client.get(f"/api/v1/cases/{case_no}/evidence")
    assert ev_res2.status_code == 200
    items = ev_res2.json()
    assert len(items) == 1
    assert items[0]["id"] == ev_item["id"]

    # 6. Check audit log has recorded the ingest event
    audit_res = client.get("/api/v1/audit")
    assert audit_res.status_code == 200
    audits = audit_res.json()
    assert any(a["resourceId"] == ev_item["id"] for a in audits)
