export function payoutForHundredDemo(probPct: number): number {
	const p = probPct / 100;
	if (p <= 0) return 0;
	return Math.round(100 / p);
}

/** Demo cards aligned with the Game console strip (illustrative only). */
export const trainPredictionDemoMarkets = [
	{
		id: 'tp-1',
		title: 'Game 6: Cleveland at Toronto',
		subtitle: 'Pro basketball · single game',
		icon: '🏀',
		live: true,
		vol24h: '$6,350,233',
		outcomes: [
			{ code: 'CLE', probPct: 34, payout: payoutForHundredDemo(34) },
			{ code: 'TOR', probPct: 66, payout: payoutForHundredDemo(66) },
		],
	},
	{
		id: 'tp-2',
		title: 'Texas vs Detroit',
		subtitle: 'MLB · moneyline',
		icon: '⚾',
		outcomes: [
			{ code: 'TEX', probPct: 90, payout: payoutForHundredDemo(90) },
			{ code: 'DET', probPct: 10, payout: payoutForHundredDemo(10) },
		],
	},
	{
		id: 'tp-3',
		title: 'Baller League US · MD9 headline',
		subtitle: 'Minor league · exhibition ladder',
		icon: '🟡',
		vol24h: '$842,110',
		outcomes: [
			{ code: 'SPD', probPct: 41, payout: payoutForHundredDemo(41) },
			{ code: 'SNO', probPct: 38, payout: payoutForHundredDemo(38) },
		],
	},
] as const;
