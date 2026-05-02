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
		'Below is a static teaching grid: flagship-contract mids vs. a crude “outside reference” fair (poll/book/model blend stub), gap in percentage points, an 80% illustrative uncertainty band on that gap, and a liquidity score. Numbers are normalized for comparison — they are not scraped from Kalshi or Coinbase and must not be traded on.',
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

