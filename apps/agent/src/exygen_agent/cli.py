from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List, Optional, Union

from exygen_agent.contracts import ExamGenerationRequest
from exygen_agent.models.generated_question_payload import MCQ
from exygen_agent.orchestrator import ExamPipelineOrchestrator, default_synthetic_documents


def default_agent3_mcq_payload() -> MCQ:
    """Returns a small in-code MCQ mock used by the Agent 3 demo workflow."""
    return MCQ(**{
        "question_id": "3",
        "professor_id": "1",
        "question_type": "MCQ",
        "question_context_id": "1",
        "mcq_options": {
            "A": "Droid",
            "B": "Bwoop whirr beep!",
            "C": "Droid Bwoop whirr beep!",
            "D": "Error"
        },
        "prompt": "Assume that these classes are defined in the same package:\n\n```java\npublic class Cast {\n    private String name;\n    public void setName(String input) { name = input ; }\n}\n\npublic class Droid extends Cast {\n    public void speak() { System.out.print(\"Droid \") ; }\n}\n\npublic class R2D2 extends Droid{\n    public void speak() { System.out.print(\"Beep beep boop!\"); }\n}\n\npublic class BB8 extends Droid {\n    public void speak() {\n        super.speak();\n        System.out.println(\"Bwoop whirr beep!\"); }\n}\n```\n\nWhat will be printed after executing the following?\n\n```java\nDroid bb8 = new BB8() ;\n((BB8) bb8).speak() ;\n```",
        "correct_mcq_key": "C",
        "existing_solution": "Droid Bwoop whirr beep!",
        "classifications": {
            "edge case": "0.32",
            "proof": "0",
            "abstract": "0.4"
        },
        "audit_trail": {
            "source_document": "Midterm_Fall2024.pdf",
            "why": "Generated to test inheritance scoping, casting rules, and compile-time vs run-time method resolution traps.",
            "reference": "links"
        }
    })


def _load_question_payload(question_json: Optional[str]) -> Dict[str, Any]:
    """Load an MCQ payload from a JSON string or @file reference."""
    if not question_json:
        raise ValueError("An --question-json value or @file reference is required.")

    candidate = question_json.strip()
    if candidate.startswith("@"):
        path = candidate[1:].strip()
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    else:
        payload = json.loads(candidate)

    if not isinstance(payload, dict):
        raise ValueError("MCQ payload must be a JSON object.")
    return payload


def run_agent3_mcq(mcq_payload: Union[Dict[str, Any], MCQ]) -> Dict[str, Any]:
    """Run the Agent 3 MCQ solution workflow: get_solution -> compare_to_options."""
    from exygen_agent.validation.mcq_validator import MCQValidator

    raw_payload = mcq_payload.model_dump() if isinstance(mcq_payload, MCQ) else dict(mcq_payload)
    validator = MCQValidator(raw_payload)
    parsed, error = validator.validate_schema()
    if parsed is None:
        raise ValueError(f"MCQ schema validation failed: {error}")

    solution = validator.get_solution(parsed)
    correct = validator.compare_solution_to_options(solution, parsed.mcq_options)

    matched_option_key: Optional[str] = None
    for option_key, option_value in (parsed.mcq_options or {}).items():
        if validator.compare_solution_to_options(solution, {option_key: option_value}):
            matched_option_key = str(option_key)
            break

    return {
        "question_id": parsed.question_id,
        "question_type": parsed.question_type,
        "solution": matched_option_key if matched_option_key is not None else solution,
        "correct": correct,
        "matched_option_key": matched_option_key,
        "mcq_options": parsed.mcq_options,
        "correct_mcq_key": parsed.correct_mcq_key,
        "existing_solution": parsed.existing_solution,
    }


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="exygen-agent",
        description="Exygen multi-agent orchestration and exam generation pipeline",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("run", help="Run the default synthetic end-to-end demo.")
    agent3_parser = subparsers.add_parser(
        "agent3",
        help="Run the Agent 3 MCQ solution workflow against a mock MCQ payload.",
    )
    agent3_parser.add_argument(
        "--question-json",
        default=None,
        help="Raw MCQ JSON payload. Defaults to a built-in mock MCQ.",
    )
    args = parser.parse_args(argv)

    if args.command == "agent3":
        if args.question_json:
            payload: Union[Dict[str, Any], MCQ] = _load_question_payload(args.question_json)
        else:
            payload = default_agent3_mcq_payload()
        print(json.dumps(run_agent3_mcq(payload), indent=2))
        return

    orchestrator = ExamPipelineOrchestrator()
    docs = default_synthetic_documents()
    extracted = [orchestrator.extract_document(doc) for doc in docs]
    profile = orchestrator.build_profile(profile_id="profile-comp251", exams=extracted)
    exam = orchestrator.generate_exam(
        exam_id="exam-demo-001",
        profile=profile,
        request=ExamGenerationRequest(profile_id=profile.id, question_count=4, total_marks=40),
        source_exams=extracted,
    )
    summary = {
        "exam_id": exam.id,
        "course": exam.course,
        "profile_id": exam.profile_id,
        "question_count": len(exam.questions),
        "total_marks": sum(q.marks for q in exam.questions),
        "alignment_summary": exam.alignment_summary,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
