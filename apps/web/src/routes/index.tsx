import { createFileRoute, Link } from "@tanstack/react-router";
import {
	ArrowRight,
	CheckCircle2,
	Cpu,
	FileCheck2,
	Layers,
	ShieldCheck,
} from "lucide-react";

export const Route = createFileRoute("/")({
	component: LandingPage,
});

const PIPELINE_STEPS = [
	{
		step: "01",
		title: "Extraction Agent",
		description:
			"Parses authorized CS exams into structured question records with section and page citations.",
	},
	{
		step: "02",
		title: "Style Analysis Agent",
		description:
			"Builds an interpretable instructor profile covering topics, question types, and complexity conventions.",
	},
	{
		step: "03",
		title: "Exam Planning Agent",
		description:
			"Reconciles mark budgets, duration, section distribution, and difficulty targets into an exam blueprint.",
	},
	{
		step: "04",
		title: "Generation & Validation Agents",
		description:
			"Produces original CS problems with draft solutions and independently verifies correctness and originality.",
	},
];

function LandingPage() {
	return (
		<main className="mx-auto max-w-6xl px-6 py-16">
			<section className="grid gap-12 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
				<div>
					<div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-300">
						<Cpu className="size-3.5" />
						<span>Multi-Agent CS Practice Exam Studio</span>
					</div>
					<h1 className="mt-6 text-4xl font-bold tracking-tight text-white sm:text-5xl">
						Instructor-aligned Computer Science practice exams, verified before
						review.
					</h1>
					<p className="mt-5 max-w-2xl text-base leading-7 text-slate-300">
						Exygen analyzes authorized historical Computer Science assessments
						to extract structural signals, generate original practice problems,
						and verify every solution and explanation before export.
					</p>
					<div className="mt-8 flex flex-wrap items-center gap-4">
						<Link
							to="/app"
							className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-slate-950 transition-colors hover:bg-emerald-400"
						>
							<span>Open Exam Studio</span>
							<ArrowRight className="size-4" />
						</Link>
						<a
							href="#pipeline"
							className="rounded-lg border border-slate-700 px-5 py-2.5 text-sm font-medium text-slate-200 transition-colors hover:border-slate-500"
						>
							Inspect Agent Pipeline
						</a>
					</div>
				</div>

				<div className="rounded-xl border border-slate-800 bg-slate-900/70 p-6">
					<h2 className="text-sm font-semibold uppercase tracking-wider text-emerald-400">
						Monorepo Architecture
					</h2>
					<ul className="mt-4 space-y-4 text-sm text-slate-300">
						<li className="flex items-start gap-3">
							<Layers className="mt-0.5 size-4 shrink-0 text-emerald-400" />
							<div>
								<strong className="text-white">apps/agent (Python)</strong>:
								Typed Pydantic contracts and 6-stage agent pipeline.
							</div>
						</li>
						<li className="flex items-start gap-3">
							<ShieldCheck className="mt-0.5 size-4 shrink-0 text-emerald-400" />
							<div>
								<strong className="text-white">apps/api (FastAPI)</strong>: REST
								endpoints for ingestion, style profiling, and exam synthesis.
							</div>
						</li>
						<li className="flex items-start gap-3">
							<FileCheck2 className="mt-0.5 size-4 shrink-0 text-emerald-400" />
							<div>
								<strong className="text-white">
									apps/web (React + TanStack)
								</strong>
								: Website and interactive studio powered by TanStack Start,
								Router, Query, and Form.
							</div>
						</li>
					</ul>
				</div>
			</section>

			<section id="pipeline" className="mt-20">
				<h2 className="text-2xl font-bold text-white">
					Six-Stage Agent Workflow
				</h2>
				<div className="mt-6 grid gap-6 sm:grid-cols-2">
					{PIPELINE_STEPS.map((item) => (
						<div
							key={item.step}
							className="rounded-xl border border-slate-800 bg-slate-900/50 p-6"
						>
							<span className="font-mono text-xs text-emerald-400">
								STAGE {item.step}
							</span>
							<h3 className="mt-2 text-lg font-semibold text-white">
								{item.title}
							</h3>
							<p className="mt-2 text-sm leading-6 text-slate-300">
								{item.description}
							</p>
						</div>
					))}
				</div>
				<div className="mt-8 flex items-center gap-2 text-xs text-slate-400">
					<CheckCircle2 className="size-4 text-emerald-400" />
					<span>
						Deterministic fallback mode enabled for reproducible offline
						demonstrations.
					</span>
				</div>
			</section>
		</main>
	);
}
