/**
 * OHLCV-derived 5-axis snowflake (momentum, vol, volume, drawdown, win rate).
 */

import * as echarts from 'echarts/core';
import { RadarChart } from 'echarts/charts';
import { RadarComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { HistorySeriesV1 } from './history-types';
import type { SnowflakeRadarHandle } from './snowflake-radar-chart';

echarts.use([RadarChart, RadarComponent, TooltipComponent, CanvasRenderer]);

const muted = 'rgba(255, 255, 255, 0.55)';
const accent = 'rgba(160, 220, 255, 0.95)';
const accentFill = 'rgba(160, 220, 255, 0.22)';
const tipBg = 'rgba(12, 14, 24, 0.94)';

function clamp01(n: number): number {
	return Math.max(0, Math.min(1, n));
}

export function historySnowflakeMetrics(series: HistorySeriesV1): {
	labels: string[];
	values: number[];
	details: string[];
} {
	const closes = series.c;
	const n = series.rows;
	if (n < 2) {
		return {
			labels: ['Momentum', 'Volatility', 'Volume', 'Drawdown', 'Win rate'],
			values: [0, 0, 0, 0, 0],
			details: ['Insufficient bars'],
		};
	}

	const tail = Math.min(126, n - 1);
	const startIdx = n - tail - 1;
	const first = closes[startIdx];
	const last = closes[n - 1];
	const momentumPct = first > 0 ? (last / first - 1) * 100 : 0;
	const momentum = clamp01((momentumPct + 30) / 60);

	const returns: number[] = [];
	let wins = 0;
	for (let i = startIdx + 1; i < n; i++) {
		const a = closes[i - 1];
		const b = closes[i];
		if (!a || a <= 0 || !b) continue;
		const r = Math.log(b / a);
		returns.push(r);
		if (r > 0) wins += 1;
	}
	const mean = returns.reduce((s, r) => s + r, 0) / Math.max(returns.length, 1);
	const variance =
		returns.reduce((s, r) => s + (r - mean) ** 2, 0) / Math.max(returns.length, 1);
	const annVol = Math.sqrt(variance) * Math.sqrt(252) * 100;
	const volScore = clamp01(1 - annVol / 80);

	const volTail = series.v.slice(-tail);
	const avgVol = volTail.reduce((s, v) => s + v, 0) / Math.max(volTail.length, 1);
	const recentVol = volTail.slice(-21).reduce((s, v) => s + v, 0) / Math.min(21, volTail.length);
	const volTrend = clamp01(recentVol / Math.max(avgVol, 1) / 1.5);

	let peak = closes[startIdx];
	let maxDd = 0;
	for (let i = startIdx; i < n; i++) {
		if (closes[i] > peak) peak = closes[i];
		const dd = peak > 0 ? (closes[i] - peak) / peak : 0;
		if (dd < maxDd) maxDd = dd;
	}
	const ddScore = clamp01(1 + maxDd / 0.5);

	const winRate = clamp01(wins / Math.max(returns.length, 1));

	return {
		labels: ['Momentum', 'Volatility', 'Volume', 'Drawdown', 'Win rate'],
		values: [momentum, volScore, volTrend, ddScore, winRate],
		details: [
			`6m-style: ${momentumPct >= 0 ? '+' : ''}${momentumPct.toFixed(1)}%`,
			`Ann. vol ~${annVol.toFixed(1)}% (lower = higher score)`,
			`Recent vol / avg: ${(recentVol / Math.max(avgVol, 1)).toFixed(2)}×`,
			`Max drawdown: ${(maxDd * 100).toFixed(1)}%`,
			`Up days: ${((winRate * 100) | 0)}% of ${returns.length} sessions`,
		],
	};
}

export function mountHistorySnowflakeRadar(
	host: HTMLElement,
	series: HistorySeriesV1,
): SnowflakeRadarHandle {
	const chart = echarts.init(host);
	const { labels, values, details } = historySnowflakeMetrics(series);

	chart.setOption({
		animation: !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
		tooltip: {
			backgroundColor: tipBg,
			borderColor: 'rgba(255,255,255,0.12)',
			textStyle: { color: '#fff', fontSize: 11 },
			formatter: () => labels.map((l, i) => `${l}: ${details[i]} (${(values[i] * 100).toFixed(0)}%)`).join('<br/>'),
		},
		radar: {
			center: ['50%', '54%'],
			radius: '58%',
			indicator: labels.map((name) => ({ name, max: 1 })),
			axisName: { color: muted, fontSize: 9 },
			splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
			splitArea: { areaStyle: { color: ['rgba(255,255,255,0.02)', 'rgba(255,255,255,0.05)'] } },
		},
		series: [
			{
				type: 'radar',
				data: [
					{
						name: `${series.ticker} · price shape`,
						value: values,
						areaStyle: { color: accentFill },
						lineStyle: { color: accent, width: 2 },
						itemStyle: { color: accent },
					},
				],
			},
		],
		graphic: [
			{
				type: 'text',
				left: 'center',
				top: 4,
				style: {
					text: 'History snowflake · OHLCV',
					fill: muted,
					fontSize: 9,
				},
			},
		],
	});

	const ro = new ResizeObserver(() => chart.resize());
	ro.observe(host);
	const onWin = () => chart.resize();
	window.addEventListener('resize', onWin);

	return {
		dispose() {
			ro.disconnect();
			window.removeEventListener('resize', onWin);
			chart.dispose();
		},
	};
}
