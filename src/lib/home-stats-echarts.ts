import * as echarts from 'echarts/core';
import { BarChart, PieChart } from 'echarts/charts';
import {
	GridComponent,
	LegendComponent,
	TitleComponent,
	TooltipComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([BarChart, PieChart, GridComponent, LegendComponent, TitleComponent, TooltipComponent, CanvasRenderer]);

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

export function mountHomeStatsECharts(mount: HTMLElement, payload: HomeStatsEChartsPayload): () => void {
	const barEl = mount.querySelector<HTMLElement>('[data-home-echarts-bar]');
	const pieEl = mount.querySelector<HTMLElement>('[data-home-echarts-pie]');
	if (!barEl || !pieEl) return () => {};

	const anim = reducedMotion() ? 0 : 900;

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
		bar.resize();
		pie.resize();
	});
	ro.observe(mount);

	const onWin = () => {
		bar.resize();
		pie.resize();
	};
	window.addEventListener('resize', onWin);

	return () => {
		window.removeEventListener('resize', onWin);
		ro.disconnect();
		bar.dispose();
		pie.dispose();
	};
}
