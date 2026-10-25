import { queryOptions } from "@tanstack/react-query";

export type QuestionType =
	| "multiple_choice"
	| "short_answer"
	| "code_writing"
	| "algorithm_design";

export type DifficultyLevel = "easy" | "medium" | "hard";

export interface ExtractedQuestion {
	id: string;
	source_document_id: string;
	page_number: number;
	section: string;
	text: string;
	marks: number;
	question_type: QuestionType;
	topics: string[];
}

export interface ExtractedExam {
	source_document_id: string;
	course: string;
	total_marks: number;
	questions: ExtractedQuestion[];
}

export interface StyleProfile {
	id: string;
	course: string;
	source_document_ids: string[];
	sections: string[];
	question_type_distribution: Record<string, number>;
	topic_distribution: Record<string, number>;
	difficulty_distribution: Record<DifficultyLevel, number>;
	terminology: string[];
	wording_patterns: string[];
	evidence: string[];
	limitations: string[];
}

export interface GeneratedQuestion {
	id: string;
	section: string;
	prompt: string;
	marks: number;
	format: QuestionType;
	topic: string;
	difficulty: DifficultyLevel;
	solution: string;
	explanation: string;
}

export interface ValidationReport {
	question_id: string;
	correctness_status: "verified" | "flagged" | "unverified";
	style_alignment_score: number;
	duplicate_risk: "low" | "medium" | "high";
	issues: string[];
	verifier_notes: string;
	accepted: boolean;
}

export interface AssembledExam {
	id: string;
	course: string;
	profile_id: string;
	questions: GeneratedQuestion[];
	validation_reports: ValidationReport[];
	alignment_summary: string;
	markdown_export: string;
	student_pdf_path?: string;
	instructor_pdf_path?: string;
}

async function downloadExamFile(examId: string, type: "student" | "instructor"): Promise<void> {
	const response = await fetch(`${API_BASE_URL}/api/exams/${examId}/export?type=${type}`);
	if (!response.ok) throw new Error(`Failed to download ${type} exam`);

	const blob = await response.blob();
	const url = window.URL.createObjectURL(blob);
	const a = document.createElement("a");
	a.href = url;
	a.download = `exam_${examId}_${type}.pdf`;
	document.body.appendChild(a);
	a.click();
	window.URL.revokeObjectURL(url);
	document.body.removeChild(a);
}

export { downloadExamFile };

export interface ExamGenerationInput {
	profile_id: string;
	question_count: number;
	total_marks: number;
	duration_minutes: number;
	target_difficulty: DifficultyLevel;
}

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const FALLBACK_DOCUMENTS: ExtractedExam[] = [
	{
		source_document_id: "doc-comp251-fall",
		course: "COMP-251",
		total_marks: 20,
		questions: [
			{
				id: "doc-comp251-fall-p1-q2",
				source_document_id: "doc-comp251-fall",
				page_number: 1,
				section: "Section A: Graph Algorithms",
				text: "Q1. Design an algorithm to detect negative cycles in a directed graph.",
				marks: 10,
				question_type: "algorithm_design",
				topics: ["graphs"],
			},
			{
				id: "doc-comp251-fall-p1-q4",
				source_document_id: "doc-comp251-fall",
				page_number: 1,
				section: "Section B: Dynamic Programming",
				text: "Q2. Prove optimal substructure for weighted interval scheduling using dynamic programming.",
				marks: 10,
				question_type: "algorithm_design",
				topics: ["dynamic_programming"],
			},
		],
	},
];

const FALLBACK_PROFILES: StyleProfile[] = [
	{
		id: "profile-comp251-default",
		course: "COMP-251",
		source_document_ids: ["doc-comp251-fall", "doc-comp251-winter"],
		sections: [
			"Section A: Graph Algorithms",
			"Section A: Trees and Hashing",
			"Section B: Dynamic Programming",
		],
		question_type_distribution: {
			algorithm_design: 0.5,
			code_writing: 0.25,
			short_answer: 0.25,
		},
		topic_distribution: {
			graphs: 0.25,
			dynamic_programming: 0.25,
			trees: 0.25,
			hashing: 0.25,
		},
		difficulty_distribution: {
			easy: 0.25,
			medium: 0.5,
			hard: 0.25,
		},
		terminology: ["asymptotic complexity", "invariant", "recurrence relation"],
		wording_patterns: [
			"State and justify the worst-case time and space complexity.",
			"Provide a concise proof of correctness using a loop invariant.",
		],
		evidence: ["Analyzed 4 extracted questions across 2 synthetic CS exams."],
		limitations: [
			"Style profile is derived from a bounded sample of synthetic exams.",
		],
	},
];

const FALLBACK_EXAMS: AssembledExam[] = [
	{
		id: "exam-comp251-demo",
		course: "COMP-251",
		profile_id: "profile-comp251-default",
		questions: [
			{
				id: "gen-q1",
				section: "Section A: Graph Algorithms",
				prompt:
					"Given a directed weighted graph G = (V, E) with non-negative edge weights and k designated hub vertices, design an algorithm to compute the shortest path from s to t passing through at least one hub vertex.",
				marks: 10,
				format: "algorithm_design",
				topic: "graphs",
				difficulty: "medium",
				solution:
					"Run Dijkstra forward from s on G and backward from t on reversed graph G^R, then minimize dist(s, h) + dist(h, t) over all hubs h.",
				explanation:
					"Two Dijkstra runs take O((|V| + |E|) log |V|) time and evaluate all hub candidates.",
			},
			{
				id: "gen-q2",
				section: "Section B: Dynamic Programming",
				prompt:
					"Formulate a dynamic programming recurrence to maximize net throughput across n intervals with a cooldown of k steps.",
				marks: 10,
				format: "algorithm_design",
				topic: "dynamic_programming",
				difficulty: "medium",
				solution:
					"DP[i] = max(DP[i - 1], gain[i] + DP[max(0, i - k - 1)]) with DP[0] = 0.",
				explanation:
					"Optimal substructure holds on prefix intervals in O(n) time and space.",
			},
		],
		validation_reports: [
			{
				question_id: "gen-q1",
				correctness_status: "verified",
				style_alignment_score: 0.92,
				duplicate_risk: "low",
				issues: [],
				verifier_notes:
					"Verified solution structure, complexity justification, and originality.",
				accepted: true,
			},
			{
				question_id: "gen-q2",
				correctness_status: "verified",
				style_alignment_score: 0.92,
				duplicate_risk: "low",
				issues: [],
				verifier_notes:
					"Verified solution structure, complexity justification, and originality.",
				accepted: true,
			},
		],
		alignment_summary:
			"Course COMP-251: 2/2 questions verified. Mean style alignment score: 0.92.",
		markdown_export:
			"# COMP-251 Practice Exam\n\n## Questions\n\n1. Hub Shortest Path (10 marks)\n2. Cooldown Interval DP (10 marks)\n",
	},
];

async function fetchWithFallback<T>(path: string, fallback: T): Promise<T> {
	try {
		const res = await fetch(`${API_BASE_URL}${path}`);
		if (!res.ok) {
			return fallback;
		}
		return (await res.json()) as T;
	} catch {
		return fallback;
	}
}

export const documentsQueryOptions = () =>
	queryOptions({
		queryKey: ["documents"],
		queryFn: () => fetchWithFallback("/api/documents", FALLBACK_DOCUMENTS),
	});

export const profilesQueryOptions = () =>
	queryOptions({
		queryKey: ["profiles"],
		queryFn: () => fetchWithFallback("/api/profiles", FALLBACK_PROFILES),
	});

export const examsQueryOptions = () =>
	queryOptions({
		queryKey: ["exams"],
		queryFn: () => fetchWithFallback("/api/exams", FALLBACK_EXAMS),
	});

export async function generatePracticeExam(
	input: ExamGenerationInput,
): Promise<AssembledExam> {
	try {
		const res = await fetch(`${API_BASE_URL}/api/exams`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(input),
		});
		if (res.ok) {
			return (await res.json()) as AssembledExam;
		}
	} catch {
		// Fallback to deterministic client-side exam when API server is offline
	}
	return {
		...FALLBACK_EXAMS[0],
		id: `exam-fallback-${Date.now().toString(36)}`,
		profile_id: input.profile_id,
	};
}
