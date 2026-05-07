/**
 * JSON shape + helpers for “show day” digests aligned with the Train live-captions desk
 * (working paper, evidence log) and optional weekly stats panels.
 *
 * Summarization model: LiquidAI/LFM2-2.6B-Transcript — long-form transcript → structured summary.
 * Use low temperature (~0.3), English, single user turn with formatted body per model card.
 *
 * @see https://huggingface.co/LiquidAI/LFM2-2.6B-Transcript
 */

export const LIQUID_TRANSCRIPT_SYSTEM_PROMPT =
	'You are an expert meeting analyst. Analyze the transcript carefully and provide clear, accurate information based on the content.';

/** Recommended by Liquid for this model family. */
export const LIQUID_TRANSCRIPT_DEFAULT_TEMPERATURE = 0.3;

export type ShowSegment = {
	/** Stable id for anchors / TOC (e.g. segment-01-open). */
	id: string;
	/** Segment title — maps to “meeting section” style notes. */
	label: string;
	window: { startISO: string; endISO: string };
	/** Short overview of what was discussed in this slice. */
	overview: string;
	topics: string[];
	actionItems?: string[];
	keyDecisions?: string[];
};

export type ThemeClaim = {
	theme: string;
	text: string;
	/** Optional 0–1 from a classifier or self-reported logit. */
	confidence?: number;
	/** Optional cross-walk to Erika / Yahoo-style symbols for catalog.json checks. */
	catalogSymbols?: string[];
};

export type SessionWrapUp = {
	abstract: string;
	segments: ShowSegment[];
	claimsUnderReview: ThemeClaim[];
	/** Free text under “Catalog cross-check” on the desk. */
	catalogCrossCheckNotes?: string;
};

export type HorizonRollup = 'day' | 'week' | 'month' | 'quarter' | 'year';

export type ComparativeRollup = {
	horizon: HorizonRollup;
	periodLabel: string;
	/** Narrative vs prior periods (not “ground truth” prices). */
	vsHistoricalSummary: string;
	/** Explicit scenario language; keep separate from facts. */
	forecastNotes?: string;
	disclaimer: string;
};

/** One row for pills / “% statistical outcomes” style strips (attempted vs cataloged). */
export type WeeklyAnalysisStat = {
	label: string;
	attempted: number;
	cataloged: number;
	/** 0–100; define attempted vs cataloged in your relay docs. */
	percentCataloged: number;
};

/** One cell for GitHub-style contribution / activity grids. */
export type WeeklyActivityCell = {
	date: string;
	/** 0–4 or 0–1 normalized; UI maps to color. */
	intensity: number;
	meta?: Record<string, unknown>;
};

export type ShowDailyReportDocument = {
	schemaVersion: 1;
	showTitle: string;
	sessionISO: string;
	model: { id: string; temperature?: number };
	wrapUp: SessionWrapUp;
	rollups: ComparativeRollup[];
	weeklyStats?: WeeklyAnalysisStat[];
	/** Rows = weekday index 0–6 or labels; columns = week buckets — UI decides. */
	weeklyHeatmap?: WeeklyActivityCell[][];
	evidenceLog: { date: string; title: string; body: string }[];
};

export type TranscriptSummaryKind =
	| 'executive'
	| 'detailed'
	| 'action_items'
	| 'key_decisions'
	| 'topics_discussed'
	| 'participants';

const SUMMARY_PROMPTS: Record<TranscriptSummaryKind, string> = {
	executive:
		'Provide a brief executive summary (2-3 sentences) of the key outcomes and decisions from this transcript.',
	detailed:
		'Provide a detailed summary of the transcript, covering all major topics, discussions, and outcomes in paragraph form.',
	action_items:
		'List the specific action items that were assigned during this meeting. Include who is responsible for each item when mentioned.',
	key_decisions:
		'List the key decisions that were made during this meeting. Focus on concrete decisions and outcomes.',
	topics_discussed:
		'List the main topics and subjects that were discussed in this meeting.',
	participants:
		'List the participants mentioned in this transcript. Include their roles or titles when available.',
};

export function summaryPrompt(kind: TranscriptSummaryKind): string {
	return SUMMARY_PROMPTS[kind];
}

/**
 * Build the transcript body Liquid documents (Title / Date / … then `**Speaker**: line`).
 * Map broadcast captions to `cues` with speaker + text; unknown speaker is fine.
 */
export function formatBroadcastTranscriptBody(input: {
	title: string;
	dateLine: string;
	timeLine: string;
	durationLine: string;
	participantsLine?: string;
	cues: { speaker: string; text: string }[];
}): string {
	const parts: string[] = [
		input.title.toUpperCase(),
		`*Date*: ${input.dateLine}`,
		`*Time*: ${input.timeLine}`,
		`*Duration*: ${input.durationLine}`,
	];
	if (input.participantsLine) {
		parts.push(`*Participants*: ${input.participantsLine}`);
	}
	parts.push('----------', '');
	for (const c of input.cues) {
		parts.push(`*${c.speaker}*: ${c.text}`);
	}
	return parts.join('\n');
}

/** Full single user message: optional instruction line + transcript block (see HF examples). */
export function formatTranscriptUserMessage(instruction: string, transcriptBody: string): string {
	return `${instruction.trim()}\n\n${transcriptBody.trim()}`;
}

/**
 * Example document for UI fixtures / relay contract tests.
 * Replace `evidenceLog` with real desk deltas when wiring JSON from the relay.
 */
export const EXAMPLE_SHOW_DAILY_REPORT: ShowDailyReportDocument = {
	schemaVersion: 1,
	showTitle: 'Bloomberg Surveillance (example day)',
	sessionISO: '2026-05-05T12:00:00.000Z',
	model: { id: 'LiquidAI/LFM2-2.6B-Transcript-GGUF', temperature: LIQUID_TRANSCRIPT_DEFAULT_TEMPERATURE },
	wrapUp: {
		abstract:
			'Example wrap: macro and rates led the open; energy inventories mid-session; equities pinned to VWAP into the close. Claims below are illustrative until live relay JSON is attached.',
		segments: [
			{
				id: 'seg-open',
				label: 'Open — macro & rates',
				window: { startISO: '2026-05-05T13:00:00.000Z', endISO: '2026-05-05T13:45:00.000Z' },
				overview: 'Curve and auction chatter; cross-asset de-risking mentioned repeatedly.',
				topics: ['Treasury supply', 'Real yields', 'Dollar'],
			},
			{
				id: 'seg-mid',
				label: 'Mid — commodities & equities',
				window: { startISO: '2026-05-05T14:00:00.000Z', endISO: '2026-05-05T15:30:00.000Z' },
				overview: 'Energy inventory narrative; index futures vs VWAP.',
				topics: ['WTI', 'Index futures', 'Breadth'],
			},
		],
		claimsUnderReview: [
			{ theme: 'Rates', text: 'Treasury curve flattens as traders weigh auction demand.', catalogSymbols: ['^TNX'] },
			{ theme: 'Energy', text: 'WTI moves on inventory surprise; refined products follow.', catalogSymbols: ['CL=F'] },
		],
		catalogCrossCheckNotes:
			'Map each theme to symbols present in the Erika directory; Directory tab / catalog.json remains ground truth for coverage.',
	},
	rollups: [
		{
			horizon: 'week',
			periodLabel: 'Week of May 5, 2026',
			vsHistoricalSummary:
				'Illustrative: compare theme frequencies and catalog hit rates to the prior 4 weeks once daily JSON exists.',
			forecastNotes:
				'Optional scenario language only — not a price forecast; cite method and horizon in any public copy.',
			disclaimer: 'Educational / research layout only — not investment advice.',
		},
	],
	weeklyStats: [
		{ label: 'Themes extracted', attempted: 120, cataloged: 86, percentCataloged: 71.7 },
		{ label: 'Symbols resolved', attempted: 86, cataloged: 72, percentCataloged: 83.7 },
	],
	weeklyHeatmap: undefined,
	evidenceLog: [
		{
			date: '2026-05-05',
			title: 'Stub multi-segment report',
			body: 'First stitched daily JSON using show-session-report types; heatmap left undefined until metrics job lands.',
		},
	],
};
