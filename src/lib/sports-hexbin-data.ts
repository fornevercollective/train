/** Synthetic league rows for hexbin + leaderboard demos (not live stats). */
export type Conference = 'East' | 'West' | 'Central';
export type FormWindow = 'week' | 'month' | 'season';

export type LeagueTeamRow = {
	id: string;
	name: string;
	conference: Conference;
	window: FormWindow;
	/** Possessions-style pace index (0–100). */
	pace: number;
	/** Defensive quality (higher = tighter). */
	defense: number;
	/** Desk “usage” index for ranking. */
	leaderboardScore: number;
};

const east = [
	'Cleveland Lake',
	'Toronto North',
	'Boston Harbor',
	'New York Metro',
	'Philadelphia Liberty',
	'Atlanta Peach',
	'Miami Shore',
	'Charlotte Crown',
	'Washington Potomac',
	'Detroit Motor',
	'Chicago Wind',
	'Milwaukee Cream',
	'Indiana Corn',
];
const west = [
	'Denver Mile',
	'Los Angeles Pacific',
	'Golden Bay',
	'Sacramento River',
	'Phoenix Suntrail',
	'Dallas Lone',
	'Houston Rockette',
	'San Antonio Alamo',
	'Memphis Bluff',
	'Minnesota Lake',
	'Portland Rose',
	'Utah Salt',
	'Oklahoma Prairie',
];
const central = [
	'Texas Long',
	'Detroit Anchor',
	'Kansas Windmill',
	'Louisville Derby',
	'Nashville Pick',
];

/** Deterministic pseudo-random 0..1 from string id */
function hash01(id: string, salt: number): number {
	let h = salt;
	for (let k = 0; k < id.length; k++) h = (h * 31 + id.charCodeAt(k)) >>> 0;
	return (h % 10007) / 10007;
}

function buildTeam(
	id: string,
	name: string,
	conference: Conference,
	window: FormWindow,
	salt: number,
): LeagueTeamRow {
	const h1 = hash01(id, salt + 1);
	const h2 = hash01(id, salt + 2);
	const h3 = hash01(id, salt + 3);
	const pace = 28 + h1 * 58 + (conference === 'West' ? 4 : 0) * h2;
	const defense = 22 + h2 * 62 + (window === 'season' ? 6 : 0) * h3;
	const leaderboardScore = Math.round(40 + h3 * 110 + pace * 0.35 + defense * 0.22);
	return { id, name, conference, window, pace, defense, leaderboardScore };
}

function teamsForConference(c: Conference): string[] {
	if (c === 'East') return east;
	if (c === 'West') return west;
	return central;
}

const rows: LeagueTeamRow[] = [];
let idx = 0;
for (const window of ['week', 'month', 'season'] as FormWindow[]) {
	for (const conference of ['East', 'West', 'Central'] as Conference[]) {
		const pool = teamsForConference(conference);
		for (let w = 0; w < pool.length; w++) {
			const name = pool[w]!;
			const id = `${conference}-${window}-${name}`.replace(/\s+/g, '-').toLowerCase();
			rows.push(buildTeam(id, name, conference, window, idx++));
		}
	}
}

export const SPORTS_HEXBIN_TEAMS: readonly LeagueTeamRow[] = rows;

export function filterTeams(window: FormWindow, conference: Conference | 'all'): LeagueTeamRow[] {
	return SPORTS_HEXBIN_TEAMS.filter((t) => {
		if (t.window !== window) return false;
		if (conference !== 'all' && t.conference !== conference) return false;
		return true;
	});
}
