import * as echarts from 'echarts/core';
import { BarChart, PieChart, RadarChart } from 'echarts/charts';
import {
	GridComponent,
	LegendComponent,
	RadarComponent,
	TitleComponent,
	TooltipComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([
	BarChart,
	PieChart,
	RadarChart,
	GridComponent,
	LegendComponent,
	RadarComponent,
	TitleComponent,
	TooltipComponent,
	CanvasRenderer,
]);

export type HomeStatsEChartsPayload = {
	barLabels: string[];
	barValues: number[];
	pie: { name: string; value: number }[];
};

const axisMuted = 'rgba(255, 255, 255, 0.55)';
const splitLine = 'rgba(255, 255, 255, 0.08)';
const barColors = ['#48e0bc', '#aa5aff', '#78b4ff', '#ffd278', '#48e0bc', '#c49bff'];

function reducedMotion(): boolean {
	return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function radarNormalizedValues(values: number[]): number[] {
	const m = Math.max(...values, 1);
	return values.map((v) => Math.min(100, Math.round((v / m) * 100)));
}

export function mountHomeStatsECharts(mount: HTMLElement, payload: HomeStatsEChartsPayload): () => void {
	const barEl = mount.querySelector<HTMLElement>('[data-home-echarts-bar]');
	const pieEl = mount.querySelector<HTMLElement>('[data-home-echarts-pie]');
	const radarEl = mount.querySelector<HTMLElement>('[data-home-echarts-radar]');
	if (!barEl || !pieEl || !radarEl) return () => {};

	const anim = reducedMotion() ? 0 : 900;
	const radarVals = radarNormalizedValues(payload.barValues);

	const radar = echarts.init(radarEl, undefined, { renderer: 'canvas' });
	radar.setOption({
		textStyle: { fontFamily: 'Inter, system-ui, sans-serif' },
		tooltip: {
			trigger: 'item',
			backgroundColor: 'rgba(12, 14, 24, 0.94)',
			borderColor: 'rgba(255, 255, 255, 0.12)',
			textStyle: { color: 'rgba(255, 255, 255, 0.92)', fontSize: 11 },
			formatter: (p: { name?: string; value?: number[] }) => {
				const vals = p.value;
				if (!vals?.length) return '';
				const rows = payload.barLabels.map((label, i) => `${label}: ${vals[i]}% (shape)`);
				return `<strong>${p.name ?? 'Coverage'}</strong><br/>${rows.join('<br/>')}`;
			},
		},
		radar: {
			indicator: payload.barLabels.map((name) => ({ name, max: 100 })),
			center: ['50%', '54%'],
			radius: '62%',
			splitNumber: 4,
			axisName: {
				color: axisMuted,
				fontSize: 10,
				lineHeight: 14,
				formatter: (name: string) => (name.length > 14 ? `${name.slice(0, 12)}…` : name),
			},
			splitLine: { lineStyle: { color: splitLine } },
			splitArea: {
				show: true,
				areaStyle: {
					color: ['rgba(72, 224, 188, 0.06)', 'rgba(120, 180, 255, 0.04)', 'rgba(72, 224, 188, 0.05)', 'rgba(0,0,0,0.06)'],
				},
			},
			axisLine: { lineStyle: { color: splitLine } },
		},
		series: [
			{
				type: 'radar',
				name: 'Coverage mix',
				symbol: 'circle',
				symbolSize: 5,
				lineStyle: { width: 2, color: 'rgba(120, 200, 255, 0.95)' },
				areaStyle: {
					color: {
						type: 'linear',
						x: 0,
						y: 0,
						x2: 0,
						y2: 1,
						colorStops: [
							{ offset: 0, color: 'rgba(120, 200, 255, 0.35)' },
							{ offset: 1, color: 'rgba(72, 224, 188, 0.12)' },
						],
					},
				},
				itemStyle: {
					color: 'rgba(120, 200, 255, 0.95)',
					borderColor: 'rgba(8, 10, 18, 0.9)',
					borderWidth: 1,
				},
				data: [{ value: radarVals, name: 'Coverage mix' }],
				animationDuration: anim,
				animationEasing: 'cubicOut',
			},
		],
	});

	const bar = echarts.init(barEl, undefined, { renderer: 'canvas' });
	bar.setOption({
		title: {
			text: 'Coverage scale',
			left: 0,
			top: 0,
			textStyle: { color: axisMuted, fontSize: 11, fontWeight: 600, fontFamily: 'IBM Plex Mono, monospace' },
		},
		tooltip: {
			trigger: 'axis',
			axisPointer: { type: 'shadow' },
			backgroundColor: 'rgba(12, 14, 24, 0.94)',
			borderColor: 'rgba(255, 255, 255, 0.12)',
			textStyle: { color: 'rgba(255, 255, 255, 0.92)' },
			valueFormatter: (v: number) => v.toLocaleString(),
		},
		grid: { left: 4, right: 28, top: 36, bottom: 4, containLabel: true },
		xAxis: {
			type: 'value',
			axisLine: { lineStyle: { color: splitLine } },
			splitLine: { lineStyle: { color: splitLine } },
			axisLabel: { color: axisMuted, formatter: (v: number) => (v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : v >= 1e4 ? `${Math.round(v / 1000)}k` : `${v}`) },
		},
		yAxis: {
			type: 'category',
			data: payload.barLabels,
			inverse: true,
			axisLine: { show: false },
			axisTick: { show: false },
			axisLabel: { color: axisMuted, fontSize: 11 },
		},
		series: [
			{
				type: 'bar',
				data: payload.barValues.map((v, i) => ({
					value: v,
					itemStyle: {
						color: barColors[i % barColors.length]!,
						borderRadius: [0, 8, 8, 0],
					},
				})),
				barMaxWidth: 22,
				animationDuration: anim,
				animationEasing: 'cubicOut',
				label: {
					show: true,
					position: 'right',
					color: 'rgba(255, 255, 255, 0.88)',
					fontSize: 11,
					formatter: (p: { value: number }) => p.value.toLocaleString(),
				},
			},
		],
	});

	const pie = echarts.init(pieEl, undefined, { renderer: 'canvas' });
	pie.setOption({
		title: {
			text: 'By security type',
			left: 'center',
			top: 0,
			textStyle: { color: axisMuted, fontSize: 11, fontWeight: 600, fontFamily: 'IBM Plex Mono, monospace' },
		},
		tooltip: {
			trigger: 'item',
			backgroundColor: 'rgba(12, 14, 24, 0.94)',
			borderColor: 'rgba(255, 255, 255, 0.12)',
			textStyle: { color: 'rgba(255, 255, 255, 0.92)' },
			formatter: '{b}: {c} ({d}%)',
		},
		legend: {
			orient: 'horizontal',
			bottom: 0,
			textStyle: { color: axisMuted, fontSize: 11 },
		},
		series: [
			{
				type: 'pie',
				radius: ['40%', '68%'],
				center: ['50%', '52%'],
				avoidLabelOverlap: true,
				itemStyle: {
					borderRadius: 8,
					borderColor: 'rgba(8, 10, 18, 0.95)',
					borderWidth: 2,
				},
				label: { color: 'rgba(255, 255, 255, 0.88)', fontSize: 11 },
				emphasis: {
					itemStyle: { shadowBlur: 18, shadowColor: 'rgba(72, 224, 188, 0.35)' },
					label: { fontWeight: 600 },
				},
				animationDuration: anim,
				animationEasing: 'cubicOut',
				data: payload.pie.map((d, i) => ({
					...d,
					itemStyle: {
						color: i === 0 ? 'rgba(120, 200, 255, 0.85)' : 'rgba(255, 200, 130, 0.82)',
					},
				})),
			},
		],
	});

	const ro = new ResizeObserver(() => {
		radar.resize();
		bar.resize();
		pie.resize();
	});
	ro.observe(mount);

	const onWin = () => {
		radar.resize();
		bar.resize();
		pie.resize();
	};
	window.addEventListener('resize', onWin);

	return () => {
		window.removeEventListener('resize', onWin);
		ro.disconnect();
		radar.dispose();
		bar.dispose();
		pie.dispose();
	};
}
