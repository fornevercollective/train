/**
 * Home-page decorative ECharts (Apache ECharts) inspired by gallery examples:
 * theme river, radar, calendar heatmap, matrix heatmap, graph, parallel, polar punch.
 * Data is illustrative or derived from static catalog facets — not live trading metrics.
 */
import * as echarts from 'echarts/core';
import { GraphChart, HeatmapChart, ParallelChart, RadarChart, ScatterChart, ThemeRiverChart } from 'echarts/charts';
import {
	CalendarComponent,
	GridComponent,
	LegendComponent,
	ParallelComponent,
	PolarComponent,
	RadarComponent,
	SingleAxisComponent,
	TitleComponent,
	TooltipComponent,
	VisualMapComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([
	ThemeRiverChart,
	RadarChart,
	HeatmapChart,
	GraphChart,
	ScatterChart,
	ParallelChart,
	GridComponent,
	CalendarComponent,
	PolarComponent,
	RadarComponent,
	ParallelComponent,
	SingleAxisComponent,
	TooltipComponent,
	TitleComponent,
	LegendComponent,
	VisualMapComponent,
	CanvasRenderer,
]);

const muted = 'rgba(255, 255, 255, 0.55)';
const border = 'rgba(255, 255, 255, 0.1)';
const tipBg = 'rgba(12, 14, 24, 0.94)';

function reducedMotion(): boolean {
	return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function animMs(): number {
	return reducedMotion() ? 0 : 650;
}

function bindResize(chart: echarts.ECharts, el: HTMLElement): () => void {
	const ro = new ResizeObserver(() => chart.resize());
	ro.observe(el);
	const onWin = () => chart.resize();
	window.addEventListener('resize', onWin);
	return () => {
		ro.disconnect();
		window.removeEventListener('resize', onWin);
	};
}

function symbolHash(s: string): number {
	let h = 0;
	for (let i = 0; i < s.length; i++) h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
	return Math.abs(h);
}

export type FacetItem = { name: string; count: number };

function mountBloombergCalendar(el: HTMLElement): (() => void) | undefined {
	const chart = echarts.init(el, undefined, { renderer: 'canvas' });
	const end = new Date();
	const start = new Date(end);
	start.setDate(start.getDate() - 119);
	const fmt = (d: Date) =>
		`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
	const data: [string, number][] = [];
	for (let t = start.getTime(); t <= end.getTime(); t += 86400000) {
		const d = new Date(t);
		const key = fmt(d);
		const w = d.getDay();
		const base = w === 0 || w === 6 ? 1 : 3;
		const bump = (symbolHash(key) % 5) + (d.getDate() % 4);
		data.push([key, base + bump]);
	}
	chart.setOption({
		textStyle: { fontFamily: 'Inter, system-ui, sans-serif' },
		tooltip: {
			position: 'top',
			backgroundColor: tipBg,
			borderColor: border,
			textStyle: { color: 'rgba(255,255,255,0.9)', fontSize: 11 },
			formatter: (p: { value?: [string, number] }) => {
				const v = p.value;
				if (!v) return '';
				return `${v[0]} · illustrative desk opens`;
			},
		},
		visualMap: {
			min: 0,
			max: 12,
			calculable: false,
			orient: 'horizontal',
			left: 'center',
			bottom: 2,
			textStyle: { color: muted, fontSize: 10 },
			inRange: { color: ['#1a2a38', '#48e0bc', '#aa5aff'] },
		},
		calendar: {
			range: [fmt(start), fmt(end)],
			cellSize: ['auto', 12],
			orient: 'horizontal',
			splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
			itemStyle: { borderWidth: 1, borderColor: 'rgba(0,0,0,0.35)' },
			dayLabel: { color: muted, fontSize: 10 },
			monthLabel: { color: muted, fontSize: 10 },
			yearLabel: { show: false },
		},
		series: [
			{
				type: 'heatmap',
				coordinateSystem: 'calendar',
				data,
				animationDuration: animMs(),
			},
		],
	});
	const off = bindResize(chart, el);
	return () => {
		off();
		chart.dispose();
	};
}

function mountFacetCountries(el: HTMLElement, items: FacetItem[]): (() => void) | undefined {
	const slice = items.slice(0, 12);
	const hub = 'Catalog';
	const nodes = [
		{
			id: hub,
			name: hub,
			symbolSize: 46,
			category: 0,
			label: { show: true, color: '#e8ecff', fontSize: 11, fontWeight: 600 },
		},
		...slice.map((c, i) => ({
			id: c.name,
			name: `${c.name}\n${c.count.toLocaleString()}`,
			symbolSize: 18 + Math.min(34, Math.log10(c.count + 1) * 14),
			category: 1,
			value: c.count,
			label: { show: i < 6, color: muted, fontSize: 9 },
		})),
	];
	const links = slice.map((c) => ({
		source: hub,
		target: c.name,
		lineStyle: { width: 1 + Math.log10(c.count + 1), curveness: 0.12 },
	}));
	const chart = echarts.init(el, undefined, { renderer: 'canvas' });
	chart.setOption({
		tooltip: {
			backgroundColor: tipBg,
			borderColor: border,
			textStyle: { color: 'rgba(255,255,255,0.9)', fontSize: 11 },
		},
		legend: { show: false },
		series: [
			{
				type: 'graph',
				layout: 'force',
				roam: true,
				draggable: true,
				force: { repulsion: 220, edgeLength: [48, 120], gravity: 0.08 },
				categories: [
					{ name: 'hub', itemStyle: { color: '#48e0bc' } },
					{ name: 'country', itemStyle: { color: '#78b4ff' } },
				],
				data: nodes,
				links,
				lineStyle: { color: 'source', opacity: 0.35, curveness: 0.1 },
				emphasis: { focus: 'adjacency', lineStyle: { width: 3, opacity: 0.75 } },
				animationDuration: animMs(),
			},
		],
	});
	const off = bindResize(chart, el);
	return () => {
		off();
		chart.dispose();
	};
}

function mountFacetExchangesMatrix(el: HTMLElement, items: FacetItem[]): (() => void) | undefined {
	const slice = items.slice(0, 8);
	const names = slice.map((x) => x.name);
	const maxC = Math.max(...slice.map((x) => x.count), 1);
	const data: [number, number, number][] = [];
	for (let i = 0; i < slice.length; i++) {
		for (let j = 0; j < slice.length; j++) {
			const v = Math.round((slice[i]!.count * slice[j]!.count) / maxC / maxC * 100);
			data.push([j, i, v || 1]);
		}
	}
	const chart = echarts.init(el, undefined, { renderer: 'canvas' });
	chart.setOption({
		tooltip: {
			position: 'top',
			backgroundColor: tipBg,
			borderColor: border,
			textStyle: { color: 'rgba(255,255,255,0.9)', fontSize: 11 },
			formatter: (p: { data?: [number, number, number] }) => {
				const d = p.data;
				if (!d) return '';
				return `${names[d[1]]} × ${names[d[0]]}<br/>affinity ${d[2]}`;
			},
		},
		grid: { top: 8, right: 8, bottom: 28, left: 72, containLabel: false },
		xAxis: {
			type: 'category',
			data: names,
			axisLabel: { color: muted, fontSize: 9, rotate: 35, interval: 0 },
			splitArea: { show: true },
		},
		yAxis: {
			type: 'category',
			data: names,
			axisLabel: { color: muted, fontSize: 9 },
			splitArea: { show: true },
		},
		visualMap: {
			min: 0,
			max: 100,
			calculable: false,
			orient: 'horizontal',
			left: 'center',
			bottom: 0,
			textStyle: { color: muted, fontSize: 9 },
			inRange: { color: ['#0f1624', '#48e0bc', '#ffd278'] },
		},
		series: [
			{
				type: 'heatmap',
				data,
				label: { show: false },
				emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(72,224,188,0.35)' } },
				animationDuration: animMs(),
			},
		],
	});
	const off = bindResize(chart, el);
	return () => {
		off();
		chart.dispose();
	};
}

function mountFacetSectorsParallel(el: HTMLElement, items: FacetItem[]): (() => void) | undefined {
	const slice = items.slice(0, 10);
	const total = slice.reduce((s, x) => s + x.count, 0) || 1;
	const names = slice.map((x) => x.name);
	const chart = echarts.init(el, undefined, { renderer: 'canvas' });
	const rows = slice.map((x) => [x.count, Math.round((x.count / total) * 1000) / 10, x.name] as (string | number)[]);
	chart.setOption({
		parallelAxis: [
			{ dim: 0, name: 'Listings', type: 'value', nameLocation: 'end', nameTextStyle: { color: muted, fontSize: 10 } },
			{
				dim: 1,
				name: 'Share %',
				type: 'value',
				min: 0,
				max: 100,
				nameLocation: 'end',
				nameTextStyle: { color: muted, fontSize: 10 },
			},
			{
				dim: 2,
				name: 'Sector',
				type: 'category',
				data: names,
				nameTextStyle: { color: muted, fontSize: 10 },
				axisLabel: { color: muted, fontSize: 9 },
			},
		],
		parallel: {
			left: 52,
			right: 36,
			bottom: 14,
			top: 28,
			parallelAxisDefault: {
				areaSelectStyle: { opacity: 0.15, borderColor: 'rgba(72,224,188,0.4)' },
			},
		},
		series: [
			{
				type: 'parallel',
				lineStyle: { width: 2, opacity: 0.5, color: '#78b4ff' },
				emphasis: { lineStyle: { width: 3, opacity: 0.95, color: '#48e0bc' } },
				data: rows,
				animationDuration: animMs(),
			},
		],
	});
	const off = bindResize(chart, el);
	return () => {
		off();
		chart.dispose();
	};
}

function mountPriorityPolarPunch(el: HTMLElement): (() => void) | undefined {
	const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
	const hours = Array.from({ length: 24 }, (_, h) => `${h}`);
	const data: [number, number, number][] = [];
	for (let d = 0; d < 7; d++) {
		for (let h = 0; h < 24; h++) {
			const session = h >= 9 && h <= 16 && d >= 1 && d <= 5 ? 4 : 1;
			const noise = (symbolHash(`${d}-${h}`) % 5) / 10;
			const v = session + noise;
			if (v > 2.2 || (d < 5 && h > 6 && h < 22 && (symbolHash(`${d}${h}`) % 7 === 0))) {
				data.push([d, h, v]);
			}
		}
	}
	const chart = echarts.init(el, undefined, { renderer: 'canvas' });
	chart.setOption({
		polar: { radius: [12, '78%'] },
		tooltip: {
			backgroundColor: tipBg,
			borderColor: border,
			textStyle: { color: 'rgba(255,255,255,0.9)', fontSize: 11 },
			formatter: (p: { value?: [number, number, number] }) => {
				const v = p.value;
				if (!v) return '';
				return `${days[v[0]]} ${v[1]}:00 · desk intensity`;
			},
		},
		angleAxis: {
			type: 'category',
			data: days,
			boundaryGap: true,
			splitLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.06)' } },
			axisLine: { lineStyle: { color: border } },
			axisLabel: { color: muted, fontSize: 10 },
		},
		radiusAxis: {
			type: 'category',
			data: hours,
			axisLine: { show: false },
			axisTick: { show: false },
			axisLabel: { color: muted, fontSize: 8, interval: 3 },
			splitLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.05)' } },
		},
		series: [
			{
				type: 'scatter',
				coordinateSystem: 'polar',
				symbolSize(val: [number, number, number]) {
					return 4 + val[2] * 5;
				},
				itemStyle: {
					color: 'rgba(120, 180, 255, 0.75)',
					shadowBlur: 6,
					shadowColor: 'rgba(72, 224, 188, 0.25)',
				},
				data,
				animationDuration: animMs(),
			},
		],
	});
	const off = bindResize(chart, el);
	return () => {
		off();
		chart.dispose();
	};
}

export type PrioritySnapshotPayload = {
	symbol: string;
	name: string;
	depthPct: number;
	altPct: number;
	status: string;
};

function mountPriorityRiverRadar(riverEl: HTMLElement, radarEl: HTMLElement, p: PrioritySnapshotPayload): (() => void) | undefined {
	const seed = symbolHash(p.symbol);
	const streams = ['Hourly', 'Session', 'Desk'];
	const riverData: [string, number, string][] = [];
	const start = new Date();
	start.setDate(start.getDate() - 27);
	for (let i = 0; i < 28; i++) {
		const d = new Date(start);
		d.setDate(d.getDate() + i);
		const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
		for (let s = 0; s < streams.length; s++) {
			const wave = Math.sin((i + seed) / 4 + s) * 8 + 12 + ((seed >> (s * 3)) % 9);
			riverData.push([key, Math.max(2, wave + (i % 3)), streams[s]!]);
		}
	}
	const river = echarts.init(riverEl, undefined, { renderer: 'canvas' });
	river.setOption({
		singleAxis: {
			top: 8,
			bottom: 4,
			axisTick: { show: false },
			axisLabel: { color: muted, fontSize: 9 },
			type: 'time',
			splitLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.06)' } },
		},
		tooltip: {
			backgroundColor: tipBg,
			borderColor: border,
			textStyle: { color: 'rgba(255,255,255,0.9)', fontSize: 10 },
		},
		series: [
			{
				type: 'themeRiver',
				data: riverData,
				emphasis: { itemStyle: { shadowBlur: 10 } },
				animationDuration: animMs(),
			},
		],
	});

	const statusScore =
		p.status === 'strong' ? 95 : p.status === 'good' ? 78 : p.status === 'medium' ? 58 : p.status === 'limited' ? 40 : 22;
	const radar = echarts.init(radarEl, undefined, { renderer: 'canvas' });
	radar.setOption({
		radar: {
			indicator: [
				{ name: 'Depth', max: 100 },
				{ name: 'Surface', max: 100 },
				{ name: 'Coverage', max: 100 },
				{ name: 'Liquidity\n(proxy)', max: 100 },
				{ name: 'Desk fit', max: 100 },
			],
			axisName: { color: muted, fontSize: 9, lineHeight: 12 },
			splitLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
			splitArea: { show: true, areaStyle: { color: ['rgba(72,224,188,0.04)', 'rgba(0,0,0,0.05)'] } },
		},
		series: [
			{
				type: 'radar',
				symbol: 'circle',
				symbolSize: 5,
				lineStyle: { width: 2, color: 'rgba(170, 90, 255, 0.85)' },
				areaStyle: { color: 'rgba(72, 224, 188, 0.12)' },
				data: [
					{
						value: [p.depthPct, p.altPct, statusScore, 55 + (seed % 28), 48 + (seed % 22)],
						name: p.symbol,
					},
				],
				animationDuration: animMs(),
			},
		],
	});

	const offR = bindResize(river, riverEl);
	const offD = bindResize(radar, radarEl);
	return () => {
		offR();
		offD();
		river.dispose();
		radar.dispose();
	};
}

function readPayload<T>(enc: string | undefined): T | null {
	if (!enc) return null;
	try {
		return JSON.parse(decodeURIComponent(enc)) as T;
	} catch {
		return null;
	}
}

export function mountHomePageViz(): () => void {
	const disposers: (() => void)[] = [];

	const cal = document.getElementById('home-bloomberg-calendar-viz');
	if (cal) {
		const d = mountBloombergCalendar(cal);
		if (d) disposers.push(d);
	}

	const fc = document.getElementById('home-facet-countries-viz');
	if (fc?.dataset.payload) {
		const items = readPayload<FacetItem[]>(fc.dataset.payload);
		if (items?.length) {
			const d = mountFacetCountries(fc, items);
			if (d) disposers.push(d);
		}
	}

	const fe = document.getElementById('home-facet-exchanges-viz');
	if (fe?.dataset.payload) {
		const items = readPayload<FacetItem[]>(fe.dataset.payload);
		if (items?.length) {
			const d = mountFacetExchangesMatrix(fe, items);
			if (d) disposers.push(d);
		}
	}

	const fs = document.getElementById('home-facet-sectors-viz');
	if (fs?.dataset.payload) {
		const items = readPayload<FacetItem[]>(fs.dataset.payload);
		if (items?.length) {
			const d = mountFacetSectorsParallel(fs, items);
			if (d) disposers.push(d);
		}
	}

	const polar = document.getElementById('home-viz-priority-polar');
	if (polar) {
		const d = mountPriorityPolarPunch(polar);
		if (d) disposers.push(d);
	}

	for (const wrap of document.querySelectorAll<HTMLElement>('[data-home-priority-snapshot]')) {
		const river = wrap.querySelector<HTMLElement>('[data-home-priority-river]');
		const radar = wrap.querySelector<HTMLElement>('[data-home-priority-radar]');
		const enc = wrap.dataset.payload;
		if (!river || !radar || !enc) continue;
		const payload = readPayload<PrioritySnapshotPayload>(enc);
		if (!payload) continue;
		const d = mountPriorityRiverRadar(river, radar, payload);
		if (d) disposers.push(d);
	}

	return () => {
		for (const d of disposers) d();
	};
}
