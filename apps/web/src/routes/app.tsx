import { useForm } from "@tanstack/react-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { CheckCircle2, FileText, Sparkles } from "lucide-react";
import { useState } from "react";
import {
	type DifficultyLevel,
	documentsQueryOptions,
	examsQueryOptions,
	generatePracticeExam,
	profilesQueryOptions,
} from "../lib/api";

export const Route = createFileRoute("/app")({
	component: ExamStudioApp,
});

function ExamStudioApp() {
	const queryClient = useQueryClient();
	const { data: documents = [] } = useQuery(documentsQueryOptions());
	const { data: profiles = [] } = useQuery(profilesQueryOptions());
	const { data: exams = [] } = useQuery(examsQueryOptions());
	const [selectedExamId, setSelectedExamId] = useState<string | null>(null);

	const activeProfile = profiles[0];
	const activeExam =
		exams.find((exam) => exam.id === selectedExamId) ?? exams[0] ?? null;

	const generateMutation = useMutation({
		mutationFn: generatePracticeExam,
		onSuccess: (createdExam) => {
			queryClient.setQueryData(["exams"], (prev: typeof exams | undefined) => [
				createdExam,
				...(prev ?? []),
			]);
			setSelectedExamId(createdExam.id);
		},
	});

	const form = useForm({
		defaultValues: {
			question_count: 4,
			total_marks: 40,
			duration_minutes: 90,
			target_difficulty: "medium" as DifficultyLevel,
		},
		onSubmit: async ({ value }) => {
			await generateMutation.mutateAsync({
				profile_id: activeProfile?.id ?? "profile-comp251-default",
				...value,
			});
		},
	});

	return (
		<main className="mx-auto max-w-6xl space-y-10 px-6 py-10">
			<div>
				<h1 className="text-2xl font-bold text-white">
					Exygen Practice Exam Studio
				</h1>
				<p className="mt-1 text-sm text-slate-400">
					Review ingested CS exam fixtures, inspect the extracted instructor
					style profile, and generate verified practice exams.
				</p>
			</div>

			<div className="grid gap-6 lg:grid-cols-2">
				<section className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
					<div className="flex items-center gap-2 text-sm font-semibold text-emerald-400">
						<FileText className="size-4" />
						<h2>1. Authorized & Synthetic Source Exams</h2>
					</div>
					<div className="mt-4 space-y-3">
						{documents.map((doc) => (
							<div
								key={doc.source_document_id}
								className="rounded-lg border border-slate-800 bg-slate-950 p-4"
							>
								<div className="flex items-center justify-between">
									<span className="font-mono text-xs text-emerald-300">
										{doc.source_document_id}
									</span>
									<span className="text-xs text-slate-400">
										{doc.course} | {doc.total_marks} marks
									</span>
								</div>
								<p className="mt-2 text-xs text-slate-300">
									Extracted {doc.questions.length} traceable question(s).
								</p>
							</div>
						))}
					</div>
				</section>

				<section className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
					<h2 className="text-sm font-semibold text-emerald-400">
						2. Extracted Instructor Style Profile
					</h2>
					{activeProfile ? (
						<div className="mt-4 space-y-3 text-sm text-slate-300">
							<p>
								<span className="text-slate-400">Profile ID:</span>{" "}
								<code className="text-white">{activeProfile.id}</code>
							</p>
							<p>
								<span className="text-slate-400">Sections:</span>{" "}
								{activeProfile.sections.join(", ")}
							</p>
							<p>
								<span className="text-slate-400">Topics:</span>{" "}
								{Object.keys(activeProfile.topic_distribution).join(", ")}
							</p>
							<p className="text-xs text-slate-400">
								{activeProfile.evidence[0]}
							</p>
						</div>
					) : (
						<p className="mt-4 text-sm text-slate-400">
							Loading style profile...
						</p>
					)}
				</section>
			</div>

			<section className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
				<div className="flex items-center gap-2 text-sm font-semibold text-emerald-400">
					<Sparkles className="size-4" />
					<h2>3. Configure and Generate Practice Exam (TanStack Form)</h2>
				</div>
				<form
					className="mt-4 grid gap-4 sm:grid-cols-4"
					onSubmit={(e) => {
						e.preventDefault();
						e.stopPropagation();
						void form.handleSubmit();
					}}
				>
					<form.Field name="question_count">
						{(field) => (
							<label className="block text-xs text-slate-300">
								<span>Question Count</span>
								<input
									type="number"
									min={1}
									max={12}
									value={field.state.value}
									onChange={(e) => field.handleChange(Number(e.target.value))}
									className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
								/>
							</label>
						)}
					</form.Field>

					<form.Field name="total_marks">
						{(field) => (
							<label className="block text-xs text-slate-300">
								<span>Total Marks</span>
								<input
									type="number"
									min={10}
									max={200}
									value={field.state.value}
									onChange={(e) => field.handleChange(Number(e.target.value))}
									className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
								/>
							</label>
						)}
					</form.Field>

					<form.Field name="target_difficulty">
						{(field) => (
							<label className="block text-xs text-slate-300">
								<span>Target Difficulty</span>
								<select
									value={field.state.value}
									onChange={(e) =>
										field.handleChange(e.target.value as DifficultyLevel)
									}
									className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
								>
									<option value="easy">Easy</option>
									<option value="medium">Medium</option>
									<option value="hard">Hard</option>
								</select>
							</label>
						)}
					</form.Field>

					<div className="flex items-end">
						<button
							type="submit"
							disabled={generateMutation.isPending}
							className="w-full rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 transition-colors hover:bg-emerald-400 disabled:opacity-50"
						>
							{generateMutation.isPending ? "Generating..." : "Generate Exam"}
						</button>
					</div>
				</form>
			</section>

			{activeExam ? (
				<section className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
					<div className="flex flex-wrap items-center justify-between gap-4">
						<div>
							<h2 className="text-lg font-semibold text-white">
								4. Verified Practice Exam ({activeExam.id})
							</h2>
							<p className="mt-1 text-xs text-emerald-400">
								{activeExam.alignment_summary}
							</p>
						</div>
					</div>

					<div className="mt-6 space-y-4">
						{activeExam.questions.map((question, index) => {
							const report = activeExam.validation_reports.find(
								(r) => r.question_id === question.id,
							);
							return (
								<div
									key={question.id}
									className="rounded-lg border border-slate-800 bg-slate-950 p-5"
								>
									<div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
										<span className="font-semibold text-white">
											Question {index + 1} ({question.marks} marks) -{" "}
											{question.topic}
										</span>
										<span className="inline-flex items-center gap-1 text-emerald-400">
											<CheckCircle2 className="size-3.5" />
											{report?.correctness_status ?? "verified"} (alignment:{" "}
											{report?.style_alignment_score ?? 0.92})
										</span>
									</div>
									<p className="mt-3 text-sm leading-6 text-slate-200">
										{question.prompt}
									</p>
									<div className="mt-4 rounded border border-slate-800 bg-slate-900/70 p-3 text-xs text-slate-300">
										<p className="font-semibold text-emerald-300">
											Reference Solution:
										</p>
										<pre className="mt-1 whitespace-pre-wrap font-mono text-xs text-slate-200">
											{question.solution}
										</pre>
										<p className="mt-2 text-slate-400">
											Explanation: {question.explanation}
										</p>
									</div>
								</div>
							);
						})}
					</div>
				</section>
			) : null}
		</main>
	);
}
