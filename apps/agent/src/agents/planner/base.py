"""Exam Planner

This file turns tagged anchor questions into the blueprint the Synthesizer and Critic work
from. It is deterministic: it uses no model, and the same anchors always give the same
blueprint. Each anchor becomes one slot that copies its measured values.

A value that was not measured stays None. Marks and difficulty can be missing, because the
Synthesizer can work without them, and an exam graded pass/fail has no marks at all. An
anchor with no topic or format cannot be planned, so it is skipped with a warning rather
than filled in with a guess.
"""

from __future__ import annotations

from src.agents.schemas import AnchorQuestion, BlueprintSlot, ExamBlueprintWithSlots
from src.clients.langfuse_client import langfuse_client
from src.schemas.clients import AgentIdentifier


class ExamPlanner:
    """Planner: Builds a blueprint with one slot per plannable anchor question."""

    _identifier = AgentIdentifier.PLANNER

    def plan(
        self, anchors: list[AnchorQuestion], exam_id: str, course: str
    ) -> tuple[ExamBlueprintWithSlots | None, list[str]]:
        """Plan one slot for each anchor that has a topic and a format.

        Args:
            anchors: The tagged questions, in exam order.
            exam_id: The exam's id.
            course: The course the exam belongs to.

        Returns:
            The blueprint, or None when nothing could be planned, and a warning for
            each anchor that was skipped.
        """
        with langfuse_client.agent_span(
            self._identifier,
            input={"exam_id": exam_id, "anchors": [a.question_id for a in anchors]},
        ) as span:
            slots: list[BlueprintSlot] = []
            warnings: list[str] = []
            for anchor in anchors:
                missing = [
                    name
                    for name, value in (
                        ("topic", anchor.topic),
                        ("format", anchor.detected_format),
                    )
                    if value is None
                ]
                if missing:
                    warnings.append(
                        f"{anchor.question_id}: skipped by the planner because its "
                        f"{' and '.join(missing)} could not be measured."
                    )
                    continue
                slots.append(
                    BlueprintSlot(
                        slot_number=len(slots) + 1,
                        topic=anchor.topic,
                        format=anchor.detected_format,
                        target_marks=anchor.marks,
                        difficulty=anchor.difficulty_estimate,
                        anchor_question_id=anchor.question_id,
                    )
                )

            blueprint = None
            if slots:
                marks = [slot.target_marks for slot in slots]
                blueprint = ExamBlueprintWithSlots(
                    exam_id=exam_id,
                    target_course=course,
                    total_marks=None if None in marks else sum(marks),
                    slots=slots,
                )
            else:
                warnings.append(
                    "No question could be planned, so no blueprint was made."
                )

            if span is not None:
                span.update(
                    output={
                        "slots": len(slots),
                        "skipped": len(anchors) - len(slots),
                        "total_marks": blueprint.total_marks if blueprint else None,
                    }
                )
            return blueprint, warnings
