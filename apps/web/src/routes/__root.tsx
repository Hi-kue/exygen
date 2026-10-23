import { TanStackDevtools } from "@tanstack/react-devtools";
import type { QueryClient } from "@tanstack/react-query";
import {
	createRootRouteWithContext,
	HeadContent,
	Link,
	Scripts,
} from "@tanstack/react-router";
import { TanStackRouterDevtoolsPanel } from "@tanstack/react-router-devtools";
import { BookOpenCheck } from "lucide-react";
import type { ReactNode } from "react";
import TanStackQueryDevtools from "../integrations/tanstack-query/devtools";
import appCss from "../styles.css?url";

interface RouterContext {
	queryClient: QueryClient;
}

export const Route = createRootRouteWithContext<RouterContext>()({
	head: () => ({
		meta: [
			{
				charSet: "utf-8",
			},
			{
				name: "viewport",
				content: "width=device-width, initial-scale=1",
			},
			{
				title: "Exygen | CS Practice Exam Intelligence",
			},
			{
				name: "description",
				content:
					"Multi-agent Computer Science exam analysis, original question generation, and verification platform.",
			},
		],
		links: [
			{
				rel: "stylesheet",
				href: appCss,
			},
		],
	}),
	shellComponent: RootDocument,
});

function RootDocument({ children }: { children: ReactNode }) {
	return (
		<html lang="en">
			<head>
				<HeadContent />
			</head>
			<body className="min-h-screen bg-slate-950 text-slate-100">
				<header className="border-b border-slate-800 bg-slate-950/90 backdrop-blur">
					<div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
						<Link
							to="/"
							className="flex items-center gap-2.5 text-lg font-semibold tracking-tight text-white"
						>
							<BookOpenCheck className="size-5 text-emerald-400" />
							<span>Exygen</span>
						</Link>
						<nav className="flex items-center gap-6 text-sm font-medium text-slate-300">
							<Link
								to="/"
								className="transition-colors hover:text-white"
								activeProps={{ className: "text-emerald-400" }}
							>
								Overview
							</Link>
							<Link
								to="/app"
								className="rounded-md bg-emerald-500 px-3.5 py-1.5 text-slate-950 transition-colors hover:bg-emerald-400"
							>
								Launch Studio
							</Link>
						</nav>
					</div>
				</header>
				<div className="min-h-[calc(100vh-8rem)]">{children}</div>
				<footer className="border-t border-slate-800 py-6 text-center text-xs text-slate-500">
					Exygen Monorepo (Python Agent + FastAPI + React & TanStack)
				</footer>
				<TanStackDevtools
					config={{
						position: "bottom-right",
					}}
					plugins={[
						{
							name: "TanStack Router",
							render: <TanStackRouterDevtoolsPanel />,
						},
						TanStackQueryDevtools,
					]}
				/>
				<Scripts />
			</body>
		</html>
	);
}
