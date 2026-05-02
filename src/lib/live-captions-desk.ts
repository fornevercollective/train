/** Static desk copy for the live-captions page — replace with API / relay JSON when wired. */

export type TocItem = { id: string; label: string };

export type ResearchCard = {
	title: string;
	blurb: string;
	tags: string[];
	href: string;
	external?: boolean;
};

export type ChangelogEntry = {
	date: string;
	title: string;
	body: string;
};

/** Order matches scroll position on the page (relay sits directly under the hero). */
export const tocItems: TocItem[] = [
	{ id: 'home-bloomberg-live', label: 'Bloomberg relay panel' },
	{ id: 'live-captions-how', label: 'How the desk works' },
	{ id: 'live-captions-explorables', label: 'Interpretability & data' },
	{ id: 'live-captions-paper', label: 'Working paper from captions' },
	{ id: 'live-captions-changelog', label: 'Evidence log' },
	{ id: 'live-captions-apis', label: 'External references' },
];

export const researchCards: ResearchCard[] = [
	{
		title: 'PAIR — human-centered ML',
		blurb:
			'Explainability, interpretability, and fairness framing for anything you infer from captions or side chat.',
		tags: ['HCI', 'Interpretability'],
		href: 'https://pair.withgoogle.com/',
		external: true,
	},
	{
		title: 'PAIR research archive',
		blurb: 'Paper-style references when you want the desk to read like a literature-backed review, not a tweet thread.',
		tags: ['Research', 'Papers'],
		href: 'https://pair.withgoogle.com/research/',
		external: true,
	},
	{
		title: 'AI Explorables',
		blurb: 'Interactive explainers — good mental model for turning caption streams into explorable sections.',
		tags: ['Explorable', 'Visualization'],
		href: 'https://pair.withgoogle.com/explorables/',
		external: true,
	},
	{
		title: 'Public — Agents prompting guide',
		blurb: 'Long-form “how we think about intent” layout: triggers, boundaries, and review before anything goes live.',
		tags: ['Agents', 'Prompting'],
		href: 'https://public.com/ai-agents/how-it-works',
		external: true,
	},
	{
		title: 'Public Trading API changelog',
		blurb: 'Dated deltas and capabilities — mirror this shape for “what changed in our digest since last session.”',
		tags: ['Changelog', 'API'],
		href: 'https://public.com/api/docs/changelog',
		external: true,
	},
];

export const changelogEntries: ChangelogEntry[] = [
	{
		date: 'May 1, 2026',
		title: 'Desk shell: captions + catalog cross-check',
		body:
			'Introduced a dedicated captions route with a working-paper scaffold. Claims list is client-generated from seed caption lines until the relay exposes JSON.',
	},
	{
		date: 'April 28, 2026',
		title: 'Relay panel shared with home',
		body:
			'Bloomberg live relay card is a single component so the same DOM contract (`#home-bloomberg-live`) works on home and on this desk for deep links.',
	},
	{
		date: 'April 12, 2026',
		title: 'Market alignment stub',
		body:
			'Priority markets from the Erika catalog (metals, benchmarks, crypto presets) are the default “universe” for tagging caption-derived themes.',
	},
];

/** Seed lines used to simulate caption → theme clustering in the browser. */
export const captionSeeds: { text: string; theme: string }[] = [
	{ theme: 'Rates', text: 'Treasury curve flattens as traders weigh auction demand.' },
	{ theme: 'Energy', text: 'WTI moves on inventory surprise; refined products follow.' },
	{ theme: 'Equities', text: 'Index futures hug VWAP into the cash open.' },
	{ theme: 'FX', text: 'Dollar bid returns on cross-asset de-risking.' },
	{ theme: 'Metals', text: 'Gold holds range as real yields oscillate.' },
];
