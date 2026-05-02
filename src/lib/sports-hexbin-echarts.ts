import * as echarts from 'echarts/core';
import { CustomChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, VisualMapContinuousComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

import {
	type Conference,
	type FormWindow,
	type LeagueTeamRow,
	filterTeams,
} from './sports-hexbin-data';

echarts.use([CustomChart, GridComponent, TooltipComponent, VisualMapContinuousComponent, CanvasRenderer]);

/** Data-space distance from hex center to vertex (flat-top orientation). */
const R_DATA = 6.2;

function flatHexCorners(px: number, py: number, pr: number): number[][] {
	const pts: number[][] = [];
	for (let i = 0; i < 6; i++) {
		const a = -Math.PI / 2 + (i * Math.PI) / 3;
		pts.push([px + pr * Math.cos(a), py + pr * Math.sin(a)]);
	}
	return pts;
}

function buildHexCenters(xmin: number, xmax: number, ymin: number, ymax: number): [number, number][] {
	const dx = Math.sqrt(3) * R_DATA;
	const dy = 1.5 * R_DATA;
	const centers: [number, number][] = [];
	for (let j = 0; ; j++) {
		const y = ymin + j * dy;
		if (y > ymax + dy) break;
		const xOff = (j % 2) * (dx / 2);
		for (let i = 0; ; i++) {
			const x = xmin + xOff + i * dx;
			if (x > xmax + dx) break;
			centers.push([x, y]);
		}
	}
	return centers;
}

const CENTERS = buildHexCenters(18, 96, 12, 94);

function nearestCenter(px: number, py: number): [number, number] {
	let best = CENTERS[0]!;
	let bestD = Infinity;
	for (const c of CENTERS) {
		const d = (px - c[0]) ** 2 + (py - c[1]) ** 2;
		if (d < bestD) {
			bestD = d;
			best = c;
		}
	}
	return best;
}

function binRows(teams: LeagueTeamRow[]): number[][] {
	const binMap = new Map<
		string,
		{ cx: number; cy: number; count: number; names: string[]; score: number }
	>();
	const key = (cx: number, cy: number) => `${cx.toFixed(3)},${cy.toFixed(3)}`;

	for (const t of teams) {
		const [cx, cy] = nearestCenter(t.pace, t.defense);
		const k = key(cx, cy);
		let b = binMap.get(k);
		if (!b) {
			b = { cx, cy, count: 0, names: [], score: 0 };
			binMap.set(k, b);
		}
		b.count += 1;
		b.score += t.leaderboardScore;
		if (b.names.length < 6) b.names.push(t.name);
	}

	return [...binMap.values()]
		.filter((b) => b.count > 0)
		.map((b) => [b.cx, b.cy, b.count, b.score, b.names.join(' · ')] as number[]);
}

function reducedMotion(): boolean {
	return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function renderRankList(ol: HTMLOListElement, teams: LeagueTeamRow[]) {
	const sorted = [...teams].sort((a, b) => b.leaderboardScore - a.leaderboardScore).slice(0, 8);
	ol.innerHTML = sorted
		.map(
			(t, i) =>
				`<li><span class="sports-hexbin-rank-idx">${i + 1}</span><span class="sports-hexbin-rank-name">${escapeHtml(t.name)}</span><span class="sports-hexbin-rank-score">${t.leaderboardScore.toLocaleString()} idx</span></li>`,
		)
		.join('');
}

function escapeHtml(s: string): string {
	return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export function mountSportsLeaderboardHexbin(root: HTMLElement): () => void {
	const chartEl = root.querySelector<HTMLElement>('[data-sports-hexbin-chart]');
	const rankOl = root.querySelector<HTMLOListElement>('[data-sports-hexbin-rank]');
	const windowBtns = Array.from(root.querySelectorAll<HTMLButtonElement>('[data-sports-window]'));
	const confBtns = Array.from(root.querySelectorAll<HTMLButtonElement>('[data-sports-conf]'));
	if (!chartEl || !rankOl) return () => {};

	let timeWindow: FormWindow = 'week';
	let conference: Conference | 'all' = 'all';

	const chart = echarts.init(chartEl, undefined, { renderer: 'canvas' });
	const anim = reducedMotion() ? 0 : 650;

	const applyFilter = (w: FormWindow, c: Conference | 'all') => {
		timeWindow = w;
		conference = c;
		for (const b of windowBtns) {
			b.classList.toggle('is-active', b.dataset.sportsWindow === timeWindow);
		}
		for (const b of confBtns) {
			b.classList.toggle('is-active', b.dataset.sportsConf === conference);
		}
		const teams = filterTeams(timeWindow, conference);
		const binData = binRows(teams);
		const maxCnt = Math.max(1, ...binData.map((d) => d[2]!));

		renderRankList(rankOl, teams);

		chart.setOption(
			{
				animationDuration: anim,
				tooltip: {
					trigger: 'item',
					backgroundColor: 'rgba(12, 14, 24, 0.94)',
					borderColor: 'rgba(255, 255, 255, 0.12)',
					textStyle: { color: 'rgba(255, 255, 255, 0.92)', fontSize: 12 },
					formatter: (p: { value: number[] }) => {
						const v = p.value;
						if (!v || v.length < 5) return '';
						const cnt = v[2]!;
						const sum = v[3]!;
						const names = String(v[4]);
						return `<div style="max-width:280px"><strong>${cnt} team${cnt === 1 ? '' : 's'}</strong> in cell<br/>Σ desk index ${sum.toLocaleString()}<br/><span style="opacity:.85">${names}</span></div>`;
					},
				},
				grid: { left: 52, right: 18, top: 28, bottom: 56, containLabel: false },
				xAxis: {
					type: 'value',
					name: 'Pace index',
					nameLocation: 'middle',
					nameGap: 28,
					min: 15,
					max: 100,
					axisLine: { lineStyle: { color: 'rgba(255,255,255,0.2)' } },
					splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
					axisLabel: { color: 'rgba(255,255,255,0.62)' },
					nameTextStyle: { color: 'rgba(255,255,255,0.55)', fontSize: 11 },
				},
				yAxis: {
					type: 'value',
					name: 'Defense index',
					nameLocation: 'middle',
					nameGap: 36,
					min: 10,
					max: 100,
					axisLine: { lineStyle: { color: 'rgba(255,255,255,0.2)' } },
					splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
					axisLabel: { color: 'rgba(255,255,255,0.62)' },
					nameTextStyle: { color: 'rgba(255,255,255,0.55)', fontSize: 11 },
				},
				visualMap: {
					show: true,
					type: 'continuous',
					dimension: 2,
					min: 1,
					max: maxCnt,
					orient: 'horizontal',
					left: 'center',
					bottom: 6,
					itemWidth: 120,
					itemHeight: 12,
					text: ['Dense', 'Sparse'],
					textStyle: { color: 'rgba(255,255,255,0.62)', fontSize: 10 },
					inRange: { color: ['rgba(72, 224, 188, 0.22)', 'rgba(170, 90, 255, 0.78)'] },
				},
				series: [
					{
						type: 'custom',
						coordinateSystem: 'cartesian2d',
						animationDuration: anim,
						data: binData,
						// ECharts custom series render typings are heavy; keep runtime-only surface here.
						renderItem(params: { data: unknown }, api: { coord: (p: number[]) => number[]; size: (a: number[]) => number[] }) {
							const raw = params.data as number[] | { value: (number | string)[] };
							const vals = Array.isArray(raw) ? raw : raw.value;
							const cx = Number(vals[0]);
							const cy = Number(vals[1]);
							const cnt = Number(vals[2]);
							const center = api.coord([cx, cy]);
							if (!center || !Number.isFinite(center[0]) || !Number.isFinite(center[1])) {
								return;
							}
							const sx = api.size([R_DATA, 0])[0];
							const sy = api.size([0, R_DATA])[1];
							const pr = ((sx + sy) / 2) * 0.46;
							const pts = flatHexCorners(center[0]!, center[1]!, pr);
							const t = Math.min(1, (cnt - 1) / Math.max(1, maxCnt - 1));
							const fill = `rgba(${Math.round(72 + t * 98)}, ${Math.round(224 - t * 120)}, ${Math.round(188 - t * 40)}, ${0.28 + t * 0.45})`;
							return {
								type: 'polygon',
								shape: { points: pts },
								style: {
									fill,
									stroke: 'rgba(255,255,255,0.14)',
									lineWidth: 1,
								},
							};
						},
					},
				],
			},
			true,
		);
	};

	applyFilter(timeWindow, conference);

	for (const b of windowBtns) {
		b.addEventListener('click', () => {
			const w = b.dataset.sportsWindow as FormWindow | undefined;
			if (!w) return;
			applyFilter(w, conference);
		});
	}
	for (const b of confBtns) {
		b.addEventListener('click', () => {
			const c = b.dataset.sportsConf as Conference | 'all' | undefined;
			if (!c) return;
			applyFilter(timeWindow, c);
		});
	}

	const ro = new ResizeObserver(() => chart.resize());
	ro.observe(chartEl);
	const onWin = () => chart.resize();
	globalThis.addEventListener('resize', onWin);

	return () => {
		globalThis.removeEventListener('resize', onWin);
		ro.disconnect();
		chart.dispose();
	};
}
