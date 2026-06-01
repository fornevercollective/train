/**
 * Month / week / day return buckets from daily OHLCV for flow + candlestick panels.
 */

import type { HistorySeriesV1 } from './history-types';
import { dayKeyToISO } from './history-shard-loader';

export type PeriodBucket = {
	key: string;
	label: string;
	returnPct: number;
	reason: string;
	bars: number;
	/** Week-only: Fri→Mon gap return when available. */
	weekendReturnPct?: number;
	weekendReason?: string;
};

function jsDate(dayKey: number): Date {
	const y = Math.floor(dayKey / 10000);
	const m = Math.floor((dayKey % 10000) / 100) - 1;
	const d = dayKey % 100;
	return new Date(y, m, d);
}

function weekday(dayKey: number): number {
	return jsDate(dayKey).getDay();
}

function monthKey(dayKey: number): string {
	const y = Math.floor(dayKey / 10000);
	const m = Math.floor((dayKey % 10000) / 100);
	return `${y}-${String(m).padStart(2, '0')}`;
}

function isoWeekKey(dayKey: number): string {
	const d = jsDate(dayKey);
	const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
	const day = date.getUTCDay() || 7;
	date.setUTCDate(date.getUTCDate() + 4 - day);
	const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
	const week = Math.ceil(((date.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
	return `${date.getUTCFullYear()}-W${String(week).padStart(2, '0')}`;
}

export function buildMonthBuckets(series: HistorySeriesV1, maxMonths = 36): PeriodBucket[] {
	const groups = new Map<string, number[]>();
	for (let i = 0; i < series.rows; i++) {
		const k = monthKey(series.d[i]);
		if (!groups.has(k)) groups.set(k, []);
		groups.get(k)!.push(i);
	}
	const keys = [...groups.keys()].sort().slice(-maxMonths);
	return keys.map((k) => {
		const idx = groups.get(k)!;
		const first = series.c[idx[0]];
		const last = series.c[idx[idx.length - 1]];
		const ret = first > 0 ? ((last / first - 1) * 100) : 0;
		return {
			key: k,
			label: k,
			returnPct: Math.round(ret * 100) / 100,
			bars: idx.length,
			reason: `${k}: ${idx.length} sessions · close ${first.toFixed(2)} → ${last.toFixed(2)} (${ret >= 0 ? '+' : ''}${ret.toFixed(2)}%)`,
		};
	});
}

export function buildWeekBuckets(series: HistorySeriesV1, maxWeeks = 52): PeriodBucket[] {
	type WeekAcc = {
		indices: number[];
		lastFridayClose: number | null;
		weekendFromFriday: number | null;
	};
	const groups = new Map<string, WeekAcc>();

	for (let i = 0; i < series.rows; i++) {
		const k = isoWeekKey(series.d[i]);
		if (!groups.has(k)) {
			groups.set(k, { indices: [], lastFridayClose: null, weekendFromFriday: null });
		}
		const acc = groups.get(k)!;
		acc.indices.push(i);

		const wd = weekday(series.d[i]);
		if (wd === 5) acc.lastFridayClose = series.c[i];
		if (wd === 1 && acc.lastFridayClose && acc.lastFridayClose > 0) {
			const gap = ((series.c[i] / acc.lastFridayClose - 1) * 100);
			acc.weekendFromFriday = Math.round(gap * 100) / 100;
		}
	}

	const keys = [...groups.keys()].sort().slice(-maxWeeks);
	return keys.map((k) => {
		const acc = groups.get(k)!;
		const idx = acc.indices;
		const first = series.c[idx[0]];
		const last = series.c[idx[idx.length - 1]];
		const ret = first > 0 ? ((last / first - 1) * 100) : 0;
		const weekendRet = acc.weekendFromFriday ?? 0;
		return {
			key: k,
			label: k.replace('-W', ' W'),
			returnPct: Math.round(ret * 100) / 100,
			bars: idx.length,
			reason: `${k}: ${idx.length} sessions · week close ${first.toFixed(2)} → ${last.toFixed(2)} (${ret >= 0 ? '+' : ''}${ret.toFixed(2)}%)`,
			weekendReturnPct: acc.weekendFromFriday ?? undefined,
			weekendReason:
				acc.weekendFromFriday !== null
					? `Weekend gap (Fri→Mon): ${weekendRet >= 0 ? '+' : ''}${weekendRet.toFixed(2)}%`
					: 'No Fri→Mon bridge in this week',
		};
	});
}

export function buildDayBuckets(series: HistorySeriesV1, maxDays = 63): PeriodBucket[] {
	const start = Math.max(1, series.rows - maxDays);
	const out: PeriodBucket[] = [];
	for (let i = start; i < series.rows; i++) {
		const prev = series.c[i - 1];
		const curr = series.c[i];
		if (!prev || prev <= 0 || !curr) continue;
		const ret = (Math.log(curr / prev) * 100);
		const iso = dayKeyToISO(series.d[i]);
		const wd = weekday(series.d[i]);
		const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
		out.push({
			key: String(series.d[i]),
			label: iso.slice(5),
			returnPct: Math.round(ret * 100) / 100,
			bars: 1,
			reason: `${iso} (${dayNames[wd]}): ${prev.toFixed(2)} → ${curr.toFixed(2)} (${ret >= 0 ? '+' : ''}${ret.toFixed(2)}% log)`,
		});
	}
	return out;
}
