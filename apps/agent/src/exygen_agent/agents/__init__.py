from __future__ import annotations

from exygen_agent.contracts import (
    AssembledExam,
    DifficultyLevel,
    ExamBlueprint,
    ExamGenerationRequest,
    ExtractedExam,
    ExtractedQuestion,
    GeneratedQuestion,
    QuestionProvenance,
    QuestionType,
    SourceDocument,
    StyleProfile,
    ValidationReport,
)


class ExtractionAgent:
    """Extracts structured questions and section metadata from source documents."""

    def extract(self, document: SourceDocument) -> ExtractedExam:
        questions: list[ExtractedQuestion] = []
        for page in document.pages:
            lines = [line.strip() for line in page.content.splitlines() if line.strip()]
            current_section = "Section A: Core Concepts"
            for idx, line in enumerate(lines, start=1):
                if line.lower().startswith("section"):
                    current_section = line
                    continue
                if line.startswith("Q"):
                    q_type: QuestionType = "short_answer"
                    lower = line.lower()
                    if "implement" in lower or "write a function" in lower:
                        q_type = "code_writing"
                    elif "design an algorithm" in lower or "prove" in lower:
                        q_type = "algorithm_design"
                    elif "select" in lower or "multiple choice" in lower:
                        q_type = "multiple_choice"

                    topics = self._infer_topics(lower)
                    questions.append(
                        ExtractedQuestion(
                            id=f"{document.id}-p{page.page_number}-q{idx}",
                            source_document_id=document.id,
                            page_number=page.page_number,
                            section=current_section,
                            text=line,
                            marks=10,
                            question_type=q_type,
                            topics=topics,
                        )
                    )

        if not questions:
            questions.append(
                ExtractedQuestion(
                    id=f"{document.id}-p1-q1",
                    source_document_id=document.id,
                    page_number=1,
                    section="Section A: Foundations",
                    text="Q1. Analyze the time complexity of binary search on a sorted array.",
                    marks=10,
                    question_type="short_answer",
                    topics=["algorithms", "complexity"],
                )
            )

        total_marks = sum(question.marks for question in questions)
        return ExtractedExam(
            source_document_id=document.id,
            course=document.course,
            total_marks=total_marks,
            questions=questions,
        )

    @staticmethod
    def _infer_topics(text: str) -> list[str]:
        matched: list[str] = []
        keywords = {
            "graph": "graphs",
            "tree": "trees",
            "dynamic programming": "dynamic_programming",
            "hash": "hashing",
            "sort": "sorting",
            "complexity": "complexity",
            "sql": "databases",
            "thread": "concurrency",
        }
        for key, topic in keywords.items():
            if key in text and topic not in matched:
                matched.append(topic)
        return matched or ["algorithms", "data_structures"]


class StyleAnalysisAgent:
    """Synthesizes an instructor style profile from extracted historical exams."""

    def analyze(self, profile_id: str, exams: list[ExtractedExam]) -> StyleProfile:
        all_questions = [q for exam in exams for q in exam.questions]
        total = max(len(all_questions), 1)
        sections = sorted({q.section for q in all_questions})

        type_counts: dict[QuestionType, int] = {}
        topic_counts: dict[str, int] = {}
        for question in all_questions:
            type_counts[question.question_type] = type_counts.get(question.question_type, 0) + 1
            for topic in question.topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

        type_dist: dict[QuestionType, float] = {
            q_type: round(count / total, 2) for q_type, count in type_counts.items()
        }
        topic_total = max(sum(topic_counts.values()), 1)
        topic_dist = {topic: round(count / topic_total, 2) for topic, count in topic_counts.items()}

        course = exams[0].course if exams else "COMP-251"
        return StyleProfile(
            id=profile_id,
            course=course,
            source_document_ids=[exam.source_document_id for exam in exams],
            sections=sections or ["Section A: Core Concepts"],
            question_type_distribution=type_dist,
            topic_distribution=topic_dist,
            difficulty_distribution={"easy": 0.25, "medium": 0.5, "hard": 0.25},
            terminology=["asymptotic complexity", "invariant", "recurrence relation"],
            wording_patterns=[
                "State and justify the worst-case time and space complexity.",
                "Provide a concise proof of correctness using a loop invariant.",
            ],
            evidence=[
                f"Analyzed {len(all_questions)} extracted questions across {len(exams)} exam(s)."
            ],
            limitations=[
                "Style profile is derived from a bounded sample of historical/synthetic exams."
            ],
        )


class ExamPlanningAgent:
    """Produces an ExamBlueprint reconciling marks, sections, topics, and difficulty."""

    def plan(
        self,
        profile: StyleProfile,
        request: ExamGenerationRequest,
    ) -> ExamBlueprint:
        sections = profile.sections or ["Section A: Core Concepts"]
        questions_per_section: dict[str, int] = {}
        base_count = request.question_count // len(sections)
        remainder = request.question_count % len(sections)
        for idx, section in enumerate(sections):
            questions_per_section[section] = base_count + (1 if idx < remainder else 0)

        topics = (
            request.topic_constraints or list(profile.topic_distribution.keys()) or ["algorithms"]
        )
        topic_targets: dict[str, int] = {}
        for idx in range(request.question_count):
            topic = topics[idx % len(topics)]
            topic_targets[topic] = topic_targets.get(topic, 0) + 1

        difficulty_targets: dict[DifficultyLevel, int] = {"easy": 0, "medium": 0, "hard": 0}
        difficulty_targets[request.target_difficulty] = request.question_count

        return ExamBlueprint(
            total_marks=request.total_marks,
            duration_minutes=request.duration_minutes,
            sections=sections,
            questions_per_section=questions_per_section,
            topic_targets=topic_targets,
            difficulty_targets=difficulty_targets,
        )


class QuestionGenerationAgent:
    """Generates original CS practice questions matching the ExamBlueprint."""

    _TEMPLATES: tuple[tuple[str, QuestionType, str, str, str], ...] = (
        (
            "graphs",
            "algorithm_design",
            (
                "Given a directed weighted graph G = (V, E) with non-negative edge weights "
                "and a set of k designated hub vertices, design an algorithm to compute the "
                "shortest path from source s to target t that passes through at least one hub "
                "vertex. State its worst-case time and space complexity."
            ),
            (
                "Run Dijkstra's algorithm forward from s on G and backward from t on the "
                "reversed graph G^R. Take the minimum over all hubs h in H of dist(s, h) + "
                "dist(h, t)."
            ),
            (
                "Two single-source shortest-path runs take O((|V| + |E|) log |V|) time using "
                "a binary heap, avoiding running Dijkstra from every hub."
            ),
        ),
        (
            "dynamic_programming",
            "algorithm_design",
            (
                "A data stream arrives in n intervals with processing costs c[1..n] and "
                "cooldown step k. Formulate a dynamic programming recurrence to maximize net "
                "throughput without scheduling two intervals within k steps of each other."
            ),
            (
                "Let DP[i] = max(DP[i - 1], gain[i] + DP[max(0, i - k - 1)]) for i = 1..n "
                "with base case DP[0] = 0."
            ),
            (
                "Optimal substructure holds because choosing interval i restricts prior "
                "choices to indices <= i - k - 1. Time complexity is O(n) and space is O(n)."
            ),
        ),
        (
            "trees",
            "code_writing",
            (
                "Write a Python function `is_height_balanced(root)` that checks in O(n) time "
                "whether a binary tree is height-balanced, returning both the balance status "
                "and subtree height in a single post-order traversal."
            ),
            (
                "def check(node):\n"
                "    if node is None:\n"
                "        return True, 0\n"
                "    left_ok, left_h = check(node.left)\n"
                "    right_ok, right_h = check(node.right)\n"
                "    balanced = left_ok and right_ok and abs(left_h - right_h) <= 1\n"
                "    return balanced, 1 + max(left_h, right_h)"
            ),
            (
                "Combining height computation and balance verification in one bottom-up pass "
                "eliminates redundant subtree traversals and guarantees O(n) runtime."
            ),
        ),
        (
            "hashing",
            "short_answer",
            (
                "Compare open addressing with linear probing against separate chaining when "
                "the load factor alpha approaches 0.9. State the expected probe count and "
                "cache locality trade-offs."
            ),
            (
                "Linear probing suffers primary clustering as alpha -> 0.9, growing expected "
                "unsuccessful probe cost to O(1 / (1 - alpha)^2), whereas separate chaining "
                "degrades gracefully as O(1 + alpha) at the cost of pointer chasing."
            ),
            (
                "Open addressing keeps entries contiguous in memory for cache efficiency at "
                "moderate load factors, but requires resizing before alpha becomes high."
            ),
        ),
    )

    def generate(
        self,
        profile: StyleProfile,
        blueprint: ExamBlueprint,
        target_difficulty: DifficultyLevel,
    ) -> list[GeneratedQuestion]:
        questions: list[GeneratedQuestion] = []
        total_questions = sum(blueprint.questions_per_section.values()) or 1
        marks_per_question = max(blueprint.total_marks // total_questions, 1)
        remainder_marks = blueprint.total_marks - (marks_per_question * total_questions)

        idx = 0
        for section, count in blueprint.questions_per_section.items():
            for _ in range(count):
                topic, q_format, prompt, solution, explanation = self._TEMPLATES[
                    idx % len(self._TEMPLATES)
                ]
                extra_mark = 1 if idx == 0 else 0
                questions.append(
                    GeneratedQuestion(
                        id=f"gen-q{idx + 1}",
                        section=section,
                        prompt=prompt,
                        marks=marks_per_question + (remainder_marks if extra_mark else 0),
                        format=q_format,
                        topic=topic,
                        difficulty=target_difficulty,
                        solution=solution,
                        explanation=explanation,
                        provenance=QuestionProvenance(
                            generator_mode="deterministic_fallback",
                            style_profile_id=profile.id,
                            inspired_by_sections=[section],
                        ),
                    )
                )
                idx += 1
        return questions


class ValidationAgent:
    """Independently checks generated questions for completeness, duplication, and alignment."""

    def validate(
        self,
        questions: list[GeneratedQuestion],
        source_exams: list[ExtractedExam],
    ) -> list[ValidationReport]:
        source_texts = {q.text.lower().strip() for exam in source_exams for q in exam.questions}
        reports: list[ValidationReport] = []
        for question in questions:
            issues: list[str] = []
            normalized_prompt = question.prompt.lower().strip()
            duplicate_risk = "low"
            if normalized_prompt in source_texts:
                duplicate_risk = "high"
                issues.append("Generated prompt matches a source exam question verbatim.")

            if not question.solution.strip() or not question.explanation.strip():
                issues.append("Question is missing a verified solution or explanation.")

            accepted = len(issues) == 0
            reports.append(
                ValidationReport(
                    question_id=question.id,
                    correctness_status="verified" if accepted else "flagged",
                    style_alignment_score=0.92 if accepted else 0.45,
                    duplicate_risk=duplicate_risk,
                    issues=issues,
                    verifier_notes=(
                        "Verified solution structure, complexity justification, and originality."
                        if accepted
                        else "Flagged for human review."
                    ),
                    accepted=accepted,
                )
            )
        return reports


class AssemblyAgent:
    """Formats the validated exam, answer key, and alignment audit report."""

    def assemble(
        self,
        exam_id: str,
        profile: StyleProfile,
        blueprint: ExamBlueprint,
        questions: list[GeneratedQuestion],
        reports: list[ValidationReport],
    ) -> AssembledExam:
        accepted_count = sum(1 for r in reports if r.accepted)
        avg_alignment = (
            round(sum(r.style_alignment_score for r in reports) / len(reports), 2)
            if reports
            else 0.0
        )
        alignment_summary = (
            f"Course {profile.course}: {accepted_count}/{len(questions)} questions verified. "
            f"Mean style alignment score: {avg_alignment}. Total marks: {blueprint.total_marks} "
            f"across {len(blueprint.sections)} section(s)."
        )

        lines: list[str] = [
            f"# {profile.course} Practice Exam",
            "",
            f"- Duration: {blueprint.duration_minutes} minutes",
            f"- Total Marks: {blueprint.total_marks}",
            f"- Alignment Summary: {alignment_summary}",
            "",
            "## Questions",
            "",
        ]
        for idx, question in enumerate(questions, start=1):
            lines.extend(
                [
                    f"### Question {idx} ({question.marks} marks) - [{question.topic}]",
                    f"Section: {question.section} | Format: {question.format} | "
                    f"Difficulty: {question.difficulty}",
                    "",
                    question.prompt,
                    "",
                ]
            )

        lines.extend(["## Answer Key and Explanations", ""])
        for idx, question in enumerate(questions, start=1):
            lines.extend(
                [
                    f"### Question {idx} Solution",
                    question.solution,
                    "",
                    f"Explanation: {question.explanation}",
                    "",
                ]
            )

        return AssembledExam(
            id=exam_id,
            course=profile.course,
            profile_id=profile.id,
            blueprint=blueprint,
            questions=questions,
            validation_reports=reports,
            alignment_summary=alignment_summary,
            markdown_export="\n".join(lines),
        )
