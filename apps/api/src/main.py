from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from exygen_agent import (
    AssembledExam,
    ExamGenerationRequest,
    ExamPipelineOrchestrator,
    ExtractedExam,
    SourceDocument,
    StyleProfile,
    default_synthetic_documents,
)


class CreateProfileRequest(BaseModel):
    document_ids: list[str] = Field(min_length=1)


class InMemoryStore:
    def __init__(self, orchestrator: ExamPipelineOrchestrator) -> None:
        self.orchestrator = orchestrator
        self.documents: dict[str, SourceDocument] = {}
        self.extracted_exams: dict[str, ExtractedExam] = {}
        self.profiles: dict[str, StyleProfile] = {}
        self.exams: dict[str, AssembledExam] = {}
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        for doc in default_synthetic_documents():
            self.documents[doc.id] = doc
            self.extracted_exams[doc.id] = self.orchestrator.extract_document(doc)

        default_profile = self.orchestrator.build_profile(
            profile_id="profile-comp251-default",
            exams=list(self.extracted_exams.values()),
        )
        self.profiles[default_profile.id] = default_profile

        default_exam = self.orchestrator.generate_exam(
            exam_id="exam-comp251-demo",
            profile=default_profile,
            request=ExamGenerationRequest(
                profile_id=default_profile.id,
                question_count=4,
                total_marks=40,
                duration_minutes=90,
                target_difficulty="medium",
            ),
            source_exams=list(self.extracted_exams.values()),
        )
        self.exams[default_exam.id] = default_exam


orchestrator = ExamPipelineOrchestrator()
store = InMemoryStore(orchestrator=orchestrator)

app = FastAPI(
    title="Exygen API",
    version="0.1.0",
    description="FastAPI service for CS exam style analysis and practice exam generation.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "exygen-api"}


@app.get("/api/documents", response_model=list[ExtractedExam])
def list_documents() -> list[ExtractedExam]:
    return list(store.extracted_exams.values())


@app.post("/api/documents", response_model=ExtractedExam, status_code=201)
def upload_document(document: SourceDocument) -> ExtractedExam:
    extracted = orchestrator.extract_document(document)
    store.documents[document.id] = document
    store.extracted_exams[document.id] = extracted
    return extracted


@app.get("/api/profiles", response_model=list[StyleProfile])
def list_profiles() -> list[StyleProfile]:
    return list(store.profiles.values())


@app.post("/api/profiles", response_model=StyleProfile, status_code=201)
def create_profile(payload: CreateProfileRequest) -> StyleProfile:
    selected_exams: list[ExtractedExam] = []
    for doc_id in payload.document_ids:
        exam = store.extracted_exams.get(doc_id)
        if exam is None:
            raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
        selected_exams.append(exam)

    profile_id = f"profile-{uuid4().hex[:8]}"
    profile = orchestrator.build_profile(profile_id=profile_id, exams=selected_exams)
    store.profiles[profile.id] = profile
    return profile


@app.get("/api/exams", response_model=list[AssembledExam])
def list_exams() -> list[AssembledExam]:
    return list(store.exams.values())


@app.post("/api/exams", response_model=AssembledExam, status_code=201)
def create_exam(request: ExamGenerationRequest) -> AssembledExam:
    profile = store.profiles.get(request.profile_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"Style profile '{request.profile_id}' not found.",
        )

    source_exams = [
        store.extracted_exams[doc_id]
        for doc_id in profile.source_document_ids
        if doc_id in store.extracted_exams
    ]
    exam_id = f"exam-{uuid4().hex[:8]}"
    assembled = orchestrator.generate_exam(
        exam_id=exam_id,
        profile=profile,
        request=request,
        source_exams=source_exams,
    )
    store.exams[assembled.id] = assembled
    return assembled


@app.get("/api/exams/{exam_id}", response_model=AssembledExam)
def get_exam(exam_id: str) -> AssembledExam:
    exam = store.exams.get(exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail=f"Exam '{exam_id}' not found.")
    return exam


@app.get("/api/exams/{exam_id}/export", response_class=PlainTextResponse)
def export_exam(exam_id: str) -> PlainTextResponse:
    exam = store.exams.get(exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail=f"Exam '{exam_id}' not found.")
    return PlainTextResponse(content=exam.markdown_export, media_type="text/markdown")
