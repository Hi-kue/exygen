from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from jinja2 import Environment, DictLoader, select_autoescape
from weasyprint import HTML

from exygen_agent.contracts import (
    AssembledExam,
    ExamBlueprint,
    GeneratedQuestion,
    ValidationReport,
)

logger = logging.getLogger(__name__)

# Professional CSS for Academic Exams
EXAM_CSS = """
@page {
    size: A4;
    margin: 2cm;
}
body {
    font-family: "Times New Roman", Times, serif;
    line-height: 1.5;
    color: #000;
    background: white;
}
.header {
    text-align: center;
    margin-bottom: 30px;
    border-bottom: 2px solid #000;
    padding-bottom: 10px;
}
.course-info {
    display: flex;
    justify-content: space-between;
    font-weight: bold;
    margin-bottom: 10px;
}
.section-header {
    font-size: 1.4em;
    font-weight: bold;
    margin-top: 20px;
    margin-bottom: 15px;
    text-decoration: underline;
    border-bottom: 1px solid #ccc;
}
.question-container {
    margin-bottom: 25px;
    page-break-inside: avoid;
}
.question-meta {
    font-weight: bold;
    margin-bottom: 5px;
}
.question-text {
    margin-bottom: 10px;
    text-align: justify;
}
.mcq-option {
    margin-left: 20px;
    margin-bottom: 5px;
}
.answer-box {
    border: 1px solid #000;
    height: 150px;
    margin-top: 10px;
    width: 100%;
}
.instructor-solution {
    margin-top: 10px;
    padding: 10px;
    background-color: #f0f7ff;
    border-left: 4px solid #0056b3;
    font-style: italic;
    font-size: 0.9em;
}
.solution-label {
    font-weight: bold;
    color: #0056b3;
}
"""

STUDENT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><style>{{ css }}</style></head>
<body>
    <div class="header">
        <h1>{{ course }} Practice Exam</h1>
        <div class="course-info">
            <span>Duration: {{ blueprint.duration_minutes }} Minutes</span>
            <span>Total Marks: {{ blueprint.total_marks }}</span>
        </div>
    </div>

    {% for section, questions in sections.items() %}
        <div class="section-header">{{ section }}</div>
        {% for q in questions %}
            <div class="question-container">
                <div class="question-meta">Question {{ loop.index }} ({{ q.marks }} marks) - {{ q.topic }}</div>
                <div class="question-text">{{ q.prompt }}</div>

                {% if q.format == 'multiple_choice' and q.mcq_options %}
                    {% for opt, text in q.mcq_options.items() %}
                        <div class="mcq-option">({{ opt }}) {{ text }}</div>
                    {% endfor %}
                {% endif %}

                <div class="answer-box"></div>
            </div>
        {% endfor %}
    {% endfor %}
</body>
</html>
"""

INSTRUCTOR_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><style>{{ css }}</style></head>
<body>
    <div class="header">
        <h1>{{ course }} Answer Key</h1>
        <div class="course-info">
            <span>Course: {{ course }}</span>
            <span>Total Marks: {{ blueprint.total_marks }}</span>
        </div>
    </div>

    {% for section, questions in sections.items() %}
        <div class="section-header">{{ section }}</div>
        {% for q in questions %}
            <div class="question-container">
                <div class="question-meta">Question {{ loop.index }} ({{ q.marks }} marks) - {{ q.topic }}</div>
                <div class="question-text">{{ q.prompt }}</div>

                {% if q.format == 'multiple_choice' and q.mcq_options %}
                    {% for opt, text in q.mcq_options.items() %}
                        <div class="mcq-option">({{ opt }}) {{ text }}</div>
                    {% endfor %}
                {% endif %}

                <div class="instructor-solution">
                    <span class="solution-label">Correct Solution:</span> {{ q.solution }}<br>
                    <span class="solution-label">Explanation:</span> {{ q.explanation }}
                </div>
            </div>
        {% endfor %}
    {% endfor %}
</body>
</html>
"""

class AssemblyAgent:
    """
    The AssemblyAgent transforms validated generated questions into
    professionally formatted PDF documents for students and instructors.
    """

    def __init__(self, output_dir: str = "exports/exams"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Jinja2 environment
        self.env = Environment(
            loader=DictLoader({
                "student": STUDENT_TEMPLATE,
                "instructor": INSTRUCTOR_TEMPLATE
            }),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def assemble(
        self,
        exam_id: str,
        course: str,
        profile_id: str,
        blueprint: ExamBlueprint,
        questions: list[GeneratedQuestion],
        reports: list[ValidationReport],
    ) -> AssembledExam:
        """
        Filters, sorts, and renders the final exam and answer key.
        """
        logger.info("Assembling final exam: %s", exam_id)

        # 1. Filter and Group questions by section
        accepted_questions = []
        for q in questions:
            report = next((r for r in reports if r.question_id == q.id), None)
            if report and report.accepted:
                accepted_questions.append(q)

        # Grouping
        sections_map: dict[str, list[GeneratedQuestion]] = {}
        for section in blueprint.sections:
            section_qs = [q for q in accepted_questions if q.section == section]
            if section_qs:
                sections_map[section] = section_qs

        # 2. Generate Markdown Export (Quick view)
        markdown_export = self._generate_markdown(course, sections_map)

        # 3. Generate PDFs via WeasyPrint
        student_path = self._render_pdf(
            exam_id, course, blueprint, sections_map, "student"
        )
        instructor_path = self._render_pdf(
            exam_id, course, blueprint, sections_map, "instructor"
        )

        # 4. Calculate Alignment Summary
        accepted_reports = [r for r in reports if r.accepted]
        avg_score = sum(r.style_alignment_score for r in accepted_reports) / max(len(accepted_reports), 1)
        alignment_summary = (
            f"Course {course}: {len(accepted_questions)}/{len(questions)} "
            f"questions verified. Mean style alignment: {avg_score:.2f}."
        )

        return AssembledExam(
            id=exam_id,
            course=course,
            profile_id=profile_id,
            blueprint=blueprint,
            questions=accepted_questions,
            validation_reports=reports,
            alignment_summary=alignment_summary,
            markdown_export=markdown_export,
            student_pdf_path=str(student_path),
            instructor_pdf_path=str(instructor_path),
        )

    def _generate_markdown(self, course: str, sections: dict[str, list[GeneratedQuestion]]) -> str:
        lines = [f"# {course} Practice Exam\n"]
        for section, qs in sections.items():
            lines.append(f"## {section}")
            for i, q in enumerate(qs, 1):
                lines.append(f"{i}. {q.prompt} ({q.marks} marks)")
        return "\n".join(lines)

    def _render_pdf(
        self, exam_id: str, course: str, blueprint: ExamBlueprint,
        sections: dict[str, list[GeneratedQuestion]], template_name: str
    ) -> Path:
        template = self.env.get_template(template_name)
        html_content = template.render(
            course=course,
            blueprint=blueprint,
            sections=sections,
            css=EXAM_CSS
        )

        filename = f"{exam_id}_{template_name}.pdf"
        output_path = self.output_dir / filename

        try:
            HTML(string=html_content).write_pdf(output_path)
            logger.info("Successfully rendered %s PDF to %s", template_name, output_path)
        except Exception as e:
            logger.error("Failed to render %s PDF: %s", template_name, e)
            # Fallback: create an empty file so the system doesn't crash
            output_path.write_text("PDF Rendering Error. Check logs.")

        return output_path
