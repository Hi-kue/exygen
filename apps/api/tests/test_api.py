from __future__ import annotations

from fastapi.testclient import TestClient

from exygen_api.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "exygen-api"}


def test_document_profile_and_exam_workflow() -> None:
    doc_payload = {
        "id": "doc-custom-1",
        "filename": "comp251_custom.txt",
        "document_type": "exam",
        "permission_status": "synthetic_fixture",
        "course": "COMP-251",
        "pages": [
            {
                "page_number": 1,
                "content": (
                    "Section A: Graph Theory\n"
                    "Q1. Design an algorithm to find strongly connected components."
                ),
            }
        ],
    }
    upload_res = client.post("/api/documents", json=doc_payload)
    assert upload_res.status_code == 201
    extracted = upload_res.json()
    assert extracted["source_document_id"] == "doc-custom-1"

    profile_res = client.post(
        "/api/profiles",
        json={"document_ids": ["doc-custom-1"]},
    )
    assert profile_res.status_code == 201
    profile = profile_res.json()

    exam_res = client.post(
        "/api/exams",
        json={
            "profile_id": profile["id"],
            "question_count": 3,
            "total_marks": 30,
            "duration_minutes": 60,
            "target_difficulty": "medium",
        },
    )
    assert exam_res.status_code == 201
    exam = exam_res.json()
    assert len(exam["questions"]) == 3

    get_res = client.get(f"/api/exams/{exam['id']}")
    assert get_res.status_code == 200

    export_res = client.get(f"/api/exams/{exam['id']}/export")
    assert export_res.status_code == 200
    assert "# COMP-251 Practice Exam" in export_res.text
