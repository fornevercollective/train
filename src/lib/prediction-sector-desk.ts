/** Educational copy for the Train predictions page — not trading advice. */

export const sectorDeskSynopsis = {
	kicker: 'Sector outlook',
	title: 'Where prediction liquidity is clustering right now',
	lede:
		'Across regulated event-contract venues (Coinbase Prediction Markets, powered by Kalshi), trending flow still skews heavily into sports — especially NBA playoffs, championships, and other major leagues. That concentration matters for anyone thinking about near-term edge: depth, spreads, and how fast markets resolve.',
	note:
		'Contracts trade like yes/no shares (e.g. ~$0.65 implying ~65% implied probability, paying $1 if the event resolves yes). Categories span Sports, Crypto, Politics, Economics, Entertainment, Companies, Science & tech, and more — but activity is not evenly distributed.',
};

export const sportsWhyBlocks = [
	{
		title: 'Volume & liquidity',
		body:
			'Trending boards are often dominated by NBA (champion, conferences, high-stakes games), golf, hockey, soccer, baseball, UFC, cricket, F1, and similar. Some single games show very large 24h notional. Deeper books mean tighter spreads, easier size, and less slippage.',
	},
	{
		title: 'Resolvable cadence',
		body:
			'Short horizons — games, series, props — give fast feedback loops compared with multi-year political or macro markets. You can react to lineups, injuries, and in-play information with clearer settlement rules.',
	},
	{
		title: 'Crowd vs. domain edge',
		body:
			'Public narratives (favorites, recency, storylines) can over- or under-shoot fair odds. Traders with structured models or deep domain read sometimes find repeatable disagreement versus consensus — the classic “information edge” story in prediction markets.',
	},
	{
		title: 'Partial independence from risk assets',
		body:
			'Sports outcomes are not the same thing as S&P or BTC direction; they can decorrelate from broad risk-on/off, even if macro sentiment occasionally bleeds into discretionary flow.',
	},
];

export const sectorContenders = [
	{
		tag: 'Crypto',
		title: 'Price milestones & buckets',
		body:
			'High mindshare with Coinbase-native users; often more volatile and more correlated with spot crypto. Can reward specialists who track flows, funding, and on-chain context — but path risk is real.',
	},
	{
		tag: 'Politics',
		title: 'Elections & nominations',
		body:
			'Can print large notional on long-dated questions (e.g. 2028 fields). Slower resolution and more narrative/polarization risk; liquidity can cluster on a handful of flagship markets.',
	},
	{
		tag: 'Economics',
		title: 'Fed, inflation, prices',
		body:
			'Scheduled data releases and well-defined calendars suit model-driven traders who like macro baselines — but surprises and revision noise still dominate short windows.',
	},
];

export const deskTips = [
	'Anchor on expertise — sports analytics, on-chain crypto, polling + fundamentals for politics, or macro nowcasts for economics — instead of trading every vertical at once.',
	'Compare implied probabilities to independent references (books where legal, models, base rates). Think in terms of mispricing vs. consensus, not “directional hot takes.”',
	'Size for binary risk: contracts can go to zero; use bankroll rules. Prefer deep, trending books when you need to move size.',
	'U.S. access is constrained (state rules, waitlists). Funding is typically USD / USDC on-platform; always read the venue disclosures — Train is not a broker.',
];

export const platformFootnote =
	'Industry reporting sometimes attributes an outsized share of notional to sports-heavy periods (e.g. large single-sport shares on Kalshi in some windows). Trending tabs move quickly — check the live app for current books.';

/** How to read venue vs. reference columns on the desk (not execution advice). */
export const mispricingKalshiCoinbasePlaybook =
	'Look for mispricings: compare Coinbase/Kalshi implied odds to bookmakers, polls, or models. Buy undervalued probabilities and sell overvalued ones (or exit early).';

/** Synthetic “rest of month” snapshot — NOT live Kalshi/Coinbase data; for layout + methodology only. */
export const monthlyEstimatesIntro = {
	title: 'Rest-of-month sector estimates (illustrative statistics)',
	lede:
		'Each sector row expands to an illustrative top 5 contract basket for the rest of the month. Summary bars show flagship mids vs. a crude reference fair, gap (pp), 80% CI on the gap, liquidity, and RoM yield index — all normalized for teaching; not scraped from Kalshi or Coinbase.',
	periodNote: 'Window label: calendar remainder of current month · Regenerate monthly in your own data pipeline when you wire APIs.',
};

export type MonthlySectorEstimateRow = {
	sector: string;
	/** Synthetic venue-weighted mid for a representative basket in that vertical (% probability). */
	venueMidPct: number;
	/** Synthetic independent reference fair (%). */
	refFairPct: number;
	/** venueMidPct − refFairPct (positive ⇒ venue looks “rich” vs. reference). */
	gapPctPoints: number;
	/** Half-width of an illustrative 80% interval on the gap (percentage points). */
	ci80HalfWidthPp: number;
	/** 0–100 liquidity / depth proxy for the vertical this month. */
	liquidityScore: number;
	/** 0–100 relative “information yield” score for the rest-of-month window (ranking only). */
	romYieldScore: number;
};

/**
 * Illustrative rows across predictive sectors. `romYieldScore` is pre-ranked:
 * highest = strongest modeled rest-of-month edge potential vs. consensus reference in this toy deck.
 */
export const monthlySectorEstimateRows: MonthlySectorEstimateRow[] = [
	{
		sector: 'Sports',
		venueMidPct: 61,
		refFairPct: 57,
		gapPctPoints: 4.0,
		ci80HalfWidthPp: 1.6,
		liquidityScore: 96,
		romYieldScore: 100,
	},
	{
		sector: 'Crypto',
		venueMidPct: 52,
		refFairPct: 49,
		gapPctPoints: 3.0,
		ci80HalfWidthPp: 2.4,
		liquidityScore: 82,
		romYieldScore: 86,
	},
	{
		sector: 'Economics / macro',
		venueMidPct: 44,
		refFairPct: 46,
		gapPctPoints: -2.0,
		ci80HalfWidthPp: 1.1,
		liquidityScore: 74,
		romYieldScore: 71,
	},
	{
		sector: 'Politics / elections',
		venueMidPct: 38,
		refFairPct: 41,
		gapPctPoints: -3.0,
		ci80HalfWidthPp: 2.0,
		liquidityScore: 68,
		romYieldScore: 64,
	},
	{
		sector: 'Entertainment',
		venueMidPct: 55,
		refFairPct: 54,
		gapPctPoints: 1.0,
		ci80HalfWidthPp: 2.8,
		liquidityScore: 58,
		romYieldScore: 59,
	},
	{
		sector: 'Companies',
		venueMidPct: 48,
		refFairPct: 50,
		gapPctPoints: -2.0,
		ci80HalfWidthPp: 2.2,
		liquidityScore: 52,
		romYieldScore: 55,
	},
	{
		sector: 'Science & tech',
		venueMidPct: 41,
		refFairPct: 43,
		gapPctPoints: -2.0,
		ci80HalfWidthPp: 2.5,
		liquidityScore: 46,
		romYieldScore: 48,
	},
];

export type MonthlyTopContract = {
	rank: number;
	contract: string;
	venueMidPct: number;
	refFairPct: number;
	gapPp: number;
	/** Illustrative depth label — not exchange volume. */
	volTier: 'Heavy' | 'Active' | 'Thin';
};

/** Five synthetic “highest attention” contracts per sector (rank 1 = strongest RoM desk signal in this toy set). */
export const monthlySectorTopFives: Record<string, MonthlyTopContract[]> = {
	Sports: [
		{ rank: 1, contract: 'Pro basketball champion (flagship)', venueMidPct: 62, refFairPct: 58, gapPp: 4, volTier: 'Heavy' },
		{ rank: 2, contract: 'Conference finals game 7 — moneyline favorite', venueMidPct: 58, refFairPct: 55, gapPp: 3, volTier: 'Heavy' },
		{ rank: 3, contract: 'Stanley Cup series — series price', venueMidPct: 54, refFairPct: 52, gapPp: 2, volTier: 'Active' },
		{ rank: 4, contract: 'Golf major — top-10 finish (market leader)', venueMidPct: 41, refFairPct: 44, gapPp: -3, volTier: 'Active' },
		{ rank: 5, contract: 'Soccer UCL — advancement leg', venueMidPct: 49, refFairPct: 50, gapPp: -1, volTier: 'Thin' },
	],
	Crypto: [
		{ rank: 1, contract: 'BTC / $100k milestone (windowed)', venueMidPct: 51, refFairPct: 47, gapPp: 4, volTier: 'Heavy' },
		{ rank: 2, contract: 'ETH / merge milestone follow-on', venueMidPct: 44, refFairPct: 42, gapPp: 2, volTier: 'Active' },
		{ rank: 3, contract: 'Major alt — ETF catalyst basket', venueMidPct: 38, refFairPct: 40, gapPp: -2, volTier: 'Active' },
		{ rank: 4, contract: 'Stablecoin depeg watch (illustrative)', venueMidPct: 12, refFairPct: 9, gapPp: 3, volTier: 'Thin' },
		{ rank: 5, contract: 'Reg headline — venue policy risk (stub)', venueMidPct: 33, refFairPct: 35, gapPp: -2, volTier: 'Thin' },
	],
	'Economics / macro': [
		{ rank: 1, contract: 'Fed funds path — next meeting cut/cut skip', venueMidPct: 46, refFairPct: 48, gapPp: -2, volTier: 'Active' },
		{ rank: 2, contract: 'CPI print vs. consensus band', venueMidPct: 52, refFairPct: 51, gapPp: 1, volTier: 'Active' },
		{ rank: 3, contract: 'Payrolls surprise threshold', venueMidPct: 39, refFairPct: 41, gapPp: -2, volTier: 'Thin' },
		{ rank: 4, contract: 'Gas retail — regional average (RoM)', venueMidPct: 28, refFairPct: 30, gapPp: -2, volTier: 'Thin' },
		{ rank: 5, contract: 'Core PCE — revision risk window', venueMidPct: 44, refFairPct: 43, gapPp: 1, volTier: 'Thin' },
	],
	'Politics / elections': [
		{ rank: 1, contract: 'Primary field — next dropout (illustrative)', venueMidPct: 36, refFairPct: 39, gapPp: -3, volTier: 'Active' },
		{ rank: 2, contract: 'Debate performance — instant reaction contract', venueMidPct: 48, refFairPct: 46, gapPp: 2, volTier: 'Active' },
		{ rank: 3, contract: 'Cabinet / agency headline — resolution window', venueMidPct: 22, refFairPct: 24, gapPp: -2, volTier: 'Thin' },
		{ rank: 4, contract: 'Swing-state poll aggregator vs. mid', venueMidPct: 55, refFairPct: 54, gapPp: 1, volTier: 'Thin' },
		{ rank: 5, contract: 'Ballot measure — signature threshold', venueMidPct: 31, refFairPct: 33, gapPp: -2, volTier: 'Thin' },
	],
	Entertainment: [
		{ rank: 1, contract: 'Award season — best picture front-runner', venueMidPct: 57, refFairPct: 55, gapPp: 2, volTier: 'Active' },
		{ rank: 2, contract: 'Streaming premiere — opening weekend (stub)', venueMidPct: 42, refFairPct: 43, gapPp: -1, volTier: 'Thin' },
		{ rank: 3, contract: 'Box office — domestic floor vs. tracking', venueMidPct: 49, refFairPct: 48, gapPp: 1, volTier: 'Thin' },
		{ rank: 4, contract: 'Music chart — #1 single window', venueMidPct: 35, refFairPct: 37, gapPp: -2, volTier: 'Thin' },
		{ rank: 5, contract: 'Reality finale — elimination order (illustrative)', venueMidPct: 61, refFairPct: 59, gapPp: 2, volTier: 'Thin' },
	],
	Companies: [
		{ rank: 1, contract: 'Mag7 — next earnings beat / miss (toy)', venueMidPct: 47, refFairPct: 49, gapPp: -2, volTier: 'Active' },
		{ rank: 2, contract: 'IPO pop — first week range', venueMidPct: 33, refFairPct: 31, gapPp: 2, volTier: 'Thin' },
		{ rank: 3, contract: 'M&A close — regulatory approval', venueMidPct: 54, refFairPct: 55, gapPp: -1, volTier: 'Thin' },
		{ rank: 4, contract: 'Product launch — pre-order threshold', venueMidPct: 41, refFairPct: 42, gapPp: -1, volTier: 'Thin' },
		{ rank: 5, contract: 'Dividend / buyback announcement (RoM)', venueMidPct: 29, refFairPct: 30, gapPp: -1, volTier: 'Thin' },
	],
	'Science & tech': [
		{ rank: 1, contract: 'Launch window — mission success (stub)', venueMidPct: 44, refFairPct: 46, gapPp: -2, volTier: 'Thin' },
		{ rank: 2, contract: 'AI benchmark — headline leaderboard bet', venueMidPct: 51, refFairPct: 49, gapPp: 2, volTier: 'Active' },
		{ rank: 3, contract: 'Clinical readout — primary endpoint', venueMidPct: 37, refFairPct: 39, gapPp: -2, volTier: 'Thin' },
		{ rank: 4, contract: 'Weather — named storm landfall (seasonal)', venueMidPct: 26, refFairPct: 27, gapPp: -1, volTier: 'Thin' },
		{ rank: 5, contract: 'Space debris / policy headline (illustrative)', venueMidPct: 18, refFairPct: 17, gapPp: 1, volTier: 'Thin' },
	],
};

export function sectorSlug(sector: string): string {
	return sector
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-|-$/g, '');
}

