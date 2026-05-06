/**
 * Home topology + predictions strip visuals (Apache ECharts).
 * - Gauge ring: https://echarts.apache.org/examples/en/editor.html?c=gauge-ring
 * - Geo-style graph: https://echarts.apache.org/examples/en/editor.html?c=geo-graph (cartesian projection, no bundled GeoJSON)
 * - Flight-style arcs: https://echarts.apache.org/examples/en/editor.html?c=lines3d-flights-gl&gl=1 (2D lines + effect; no echarts-gl)
 * - Wind field: https://echarts.apache.org/examples/en/editor.html?c=custom-wind (custom series, illustrative)
 */
import * as echarts from 'echarts/core';
import { CustomChart, EffectScatterChart, GaugeChart, LinesChart, ScatterChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, TitleComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { CustomSeriesRenderItemAPI } from 'echarts';

echarts.use([
	GaugeChart,
	ScatterChart,
	LinesChart,
	EffectScatterChart,
	CustomChart,
	GridComponent,
	TooltipComponent,
	TitleComponent,
	CanvasRenderer,
]);

const muted = 'rgba(255, 255, 255, 0.55)';
const tipBg = 'rgba(12, 14, 24, 0.94)';

function reducedMotion(): boolean {
	return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function animMs(): number {
	return reducedMotion() ? 0 : 750;
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

/** Web Mercator-ish flatten for schematic “geo” layout */
function project(lon: number, lat: number): [number, number] {
	const x = ((lon + 180) / 360) * 100;
	const y = ((90 - lat) / 170) * 100;
	return [x, y];
}

const VENUE_COORDS: Record<string, [number, number]> = {
	'CME / Aurora futures': [-87.6, 41.9],
	'NASDAQ / NYSE / NYSE Arca / OPRA': [-74.0, 40.75],
	'LSE / ICE Europe / Euronext': [-0.08, 51.5],
	'Deutsche Boerse / Eurex': [8.68, 50.12],
	'JPX / OSE': [139.77, 35.68],
	'HKEX / SGX': [114.17, 22.32],
};

export type TopologyRouteLite = { venue: string; pop: string };

function shortVenue(name: string): string {
	const i = name.indexOf('/');
	return i > 0 ? name.slice(0, i).trim() : name.slice(0, 14);
}

function mountTopologyGauge(el: HTMLElement): (() => void) | undefined {
	const chart = echarts.init(el, undefined, { renderer: 'canvas' });
	const v = 72;
	chart.setOption({
		textStyle: { fontFamily: 'Inter, system-ui, sans-serif' },
		tooltip: {
			backgroundColor: tipBg,
			borderColor: 'rgba(255,255,255,0.12)',
			textStyle: { color: 'rgba(255,255,255,0.9)', fontSize: 11 },
			formatter: () =>
				`<strong>Relay readiness (illustrative)</strong><br/>${v}% — static desk metaphor, not a live SLO.`,
		},
		series: [
			{
				type: 'gauge',
				startAngle: 90,
				endAngle: -270,
				center: ['50%', '52%'],
				radius: '88%',
				pointer: { show: false },
				progress: {
					show: true,
					overlap: false,
					roundCap: true,
					clip: false,
					itemStyle: { color: 'rgba(72, 224, 188, 0.85)' },
				},
				axisLine: {
					lineStyle: { width: 14, color: [[1, 'rgba(30, 40, 58, 0.95)']] },
				},
				splitLine: { show: false },
				axisTick: { show: false },
				axisLabel: { show: false },
				detail: {
					valueAnimation: !reducedMotion(),
					fontSize: 22,
					fontWeight: 600,
					color: 'rgba(230, 236, 255, 0.92)',
					offsetCenter: [0, 0],
					formatter: '{value}%',
				},
				title: {
					offsetCenter: [0, '72%'],
					color: muted,
					fontSize: 11,
					fontWeight: 500,
				},
				data: [{ value: v, name: 'Readiness' }],
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

function mountTopologyGeoGraph(el: HTMLElement, routes: TopologyRouteLite[]): (() => void) | undefined {
	const pts = routes
		.map((r) => {
			const ll = VENUE_COORDS[r.venue];
			if (!ll) return null;
			const [x, y] = project(ll[0], ll[1]);
			return { name: shortVenue(r.venue), full: r.venue, pop: r.pop, x, y };
		})
		.filter(Boolean) as { name: string; full: string; pop: string; x: number; y: number }[];

	if (pts.length < 2) return undefined;

	const chart = echarts.init(el, undefined, { renderer: 'canvas' });
	const scatter = pts.map((p) => ({
		name: p.name,
		value: [p.x, p.y],
		pop: p.pop,
		full: p.full,
	}));

	chart.setOption({
		textStyle: { fontFamily: 'Inter, system-ui, sans-serif' },
		grid: { left: 6, right: 6, top: 10, bottom: 10, containLabel: true },
		tooltip: {
			backgroundColor: tipBg,
			borderColor: 'rgba(255,255,255,0.12)',
			textStyle: { color: 'rgba(255,255,255,0.9)', fontSize: 11 },
			formatter: (p: { data?: { full?: string; pop?: string } }) => {
				const d = p.data;
				if (!d) return '';
				return `<strong>${d.full}</strong><br/>${d.pop}`;
			},
		},
		xAxis: {
			type: 'value',
			min: 0,
			max: 100,
			show: false,
			splitLine: { show: false },
		},
		yAxis: {
			type: 'value',
			min: 0,
			max: 100,
			show: false,
			splitLine: { show: false },
		},
		series: [
			{
				type: 'scatter',
				symbolSize: 20,
				itemStyle: {
					color: 'rgba(120, 180, 255, 0.82)',
					borderColor: 'rgba(72, 224, 188, 0.45)',
					borderWidth: 1,
					shadowBlur: 12,
					shadowColor: 'rgba(72, 224, 188, 0.25)',
				},
				label: {
					show: true,
					position: 'top',
					color: muted,
					fontSize: 10,
					formatter: (p: { name?: string }) => p.name ?? '',
				},
				data: scatter.map((s) => ({
					name: s.name,
					value: s.value,
					full: s.full,
					pop: s.pop,
				})),
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

function mountTopologyFlights(el: HTMLElement, routes: TopologyRouteLite[]): (() => void) | undefined {
	const pts = routes
		.map((r) => {
			const ll = VENUE_COORDS[r.venue];
			if (!ll) return null;
			return project(ll[0], ll[1]);
		})
		.filter(Boolean) as [number, number][];

	if (pts.length < 2) return undefined;

	const pairs: [number, number][][] = [];
	for (let i = 0; i < pts.length - 1; i++) pairs.push([pts[i]!, pts[i + 1]!]);
	pairs.push([pts[1]!, pts[3]!]);
	pairs.push([pts[2]!, pts[4]!]);

	const chart = echarts.init(el, undefined, { renderer: 'canvas' });
	const lineSeries = {
		type: 'lines' as const,
		coordinateSystem: 'cartesian2d' as const,
		polyline: false,
		effect: reducedMotion()
			? { show: false }
			: {
					show: true,
					period: 5,
					trailLength: 0.22,
					symbol: 'arrow',
					symbolSize: 7,
					color: 'rgba(255, 210, 120, 0.75)',
				},
		lineStyle: {
			color: 'rgba(170, 90, 255, 0.55)',
			width: 1.4,
			curveness: 0.22,
			opacity: 0.85,
		},
		data: pairs.map((coords) => ({ coords })),
		animationDuration: animMs(),
	};
	const pulseSeries = {
		type: 'effectScatter' as const,
		coordinateSystem: 'cartesian2d' as const,
		rippleEffect: { brushType: 'stroke' as const, period: 3.5, scale: 3.2 },
		symbolSize: 8,
		itemStyle: { color: 'rgba(72, 224, 188, 0.55)' },
		data: pts.map(([x, y]) => [x, y]),
		animationDuration: animMs(),
	};
	chart.setOption({
		textStyle: { fontFamily: 'Inter, system-ui, sans-serif' },
		grid: { left: 6, right: 6, top: 8, bottom: 8, containLabel: true },
		tooltip: {
			show: false,
		},
		xAxis: { type: 'value', min: 0, max: 100, show: false },
		yAxis: { type: 'value', min: 0, max: 100, show: false },
		series: reducedMotion() ? [lineSeries] : [lineSeries, pulseSeries],
	});
	const off = bindResize(chart, el);
	return () => {
		off();
		chart.dispose();
	};
}

function windField(ix: number, iy: number): [number, number] {
	const x = ix / 6;
	const y = iy / 4;
	return [Math.sin(y * 1.7) + Math.cos(x * 1.1) * 0.35, Math.cos(x * 1.4) - Math.sin(y * 0.9) * 0.25];
}

function mountPredictionsWind(el: HTMLElement): (() => void) | undefined {
	const chart = echarts.init(el, undefined, { renderer: 'canvas' });
	const cols = 26;
	const rows = 10;
	const data: [number, number][] = [];
	for (let j = 0; j < rows; j++) {
		for (let i = 0; i < cols; i++) data.push([i, j]);
	}

	const renderItem = (_: unknown, api: CustomSeriesRenderItemAPI) => {
		const ix = api.value(0) as number;
		const iy = api.value(1) as number;
		const c = api.coord([ix, iy]);
		if (!c) return;
		const [wx, wy] = windField(ix, iy);
		const ang = Math.atan2(wy, wx);
		const len = 9;
		const x2 = c[0]! + len * Math.cos(ang);
		const y2 = c[1]! + len * Math.sin(ang);
		const tone = 0.35 + ((ix * 13 + iy * 7) % 40) / 100;
		return {
			type: 'line',
			shape: { x1: c[0], y1: c[1], x2, y2 },
			style: {
				stroke: `rgba(120, 200, 255, ${tone})`,
				lineWidth: 1.1,
				lineCap: 'round',
			},
		};
	};

	chart.setOption({
		textStyle: { fontFamily: 'Inter, system-ui, sans-serif' },
		grid: { left: 4, right: 4, top: 4, bottom: 4, containLabel: false },
		xAxis: { type: 'value', min: -0.5, max: cols - 0.5, show: false, splitLine: { show: false } },
		yAxis: { type: 'value', min: -0.5, max: rows - 0.5, show: false, splitLine: { show: false } },
		series: [
			{
				type: 'custom',
				renderItem,
				encode: { x: 0, y: 1 },
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

function readTopologyPayload(enc: string | undefined): TopologyRouteLite[] | null {
	if (!enc) return null;
	try {
		return JSON.parse(decodeURIComponent(enc)) as TopologyRouteLite[];
	} catch {
		return null;
	}
}

export function mountTopologyPredictionsViz(): () => void {
	const disposers: (() => void)[] = [];

	const root = document.getElementById('topology-viz-root');
	const routes = readTopologyPayload(root?.dataset.payload);
	if (routes?.length) {
		const g = document.getElementById('topology-viz-gauge');
		const geo = document.getElementById('topology-viz-geo');
		const fl = document.getElementById('topology-viz-flights');
		if (g) {
			const d = mountTopologyGauge(g);
			if (d) disposers.push(d);
		}
		if (geo) {
			const d = mountTopologyGeoGraph(geo, routes);
			if (d) disposers.push(d);
		}
		if (fl) {
			const d = mountTopologyFlights(fl, routes);
			if (d) disposers.push(d);
		}
	}

	return () => {
		for (const d of disposers) d();
	};
}

/** Wind strip only — use on `/predictions/` where `HomePageViz` is not present. */
export function mountEpPredictionsWindViz(): () => void {
	const wind = document.getElementById('ep-pred-wind-viz');
	if (!wind) return () => {};
	const d = mountPredictionsWind(wind);
	return d ?? (() => {});
}
