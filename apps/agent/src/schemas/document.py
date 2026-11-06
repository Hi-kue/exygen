"""Document Schemas

This file contains the types that describe an uploaded source document and its pages.
They record what a document is and whether it may be used, so the pipeline can trace
every extracted question back to a page. Parsing itself is done by the Docling client,
whose own result types live in 'src.schemas.clients'.

Holds:
    - 'DocumentType': What kind of material a document is (exam, syllabus or notes).
    - 'PermissionStatus': Why the document may be used (authorized or synthetic fixture).
    - 'DocumentPage': The text of one page, with its page number.
    - 'SourceDocument': A document with its course, permission status and pages.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DocumentType = Literal["exam", "syllabus", "notes"]
PermissionStatus = Literal["authorized", "synthetic_fixture"]


class DocumentPage(BaseModel):
    page_number: int = Field(ge=1)
    content: str = Field(min_length=1)


class SourceDocument(BaseModel):
    id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    document_type: DocumentType = "exam"
    permission_status: PermissionStatus = "synthetic_fixture"
    course: str = Field(min_length=1)
    pages: list[DocumentPage] = Field(min_length=1)
