/**
 * Five-axis snowflake radar from coverage pass rates (ECharts radar, dark theme).
 */

import * as echarts from 'echarts/core';
import { RadarChart } from 'echarts/charts';
import { RadarComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { SnowflakeProfileV1 } from './health-snowflake-types';

echarts.use([RadarChart, RadarComponent, TooltipComponent, CanvasRenderer]);

const muted = 'rgba(255, 255, 255, 0.55)';
const accent = 'rgba(120, 200, 255, 0.9)';
const accentFill = 'rgba(120, 200, 255, 0.28)';
const failColor = 'rgba(255, 120, 140, 0.85)';
const failFill = 'rgba(255, 120, 140, 0.15)';
const tipBg = 'rgba(12, 14, 24, 0.94)';

export type SnowflakeRadarHandle = { dispose: () => void };

/** Pass rate among scored checks (excludes na so the polygon is visible). */
function axisPassRate(axis: SnowflakeProfileV1['axes'][number]): number {
	const scored = axis.checks.filter((c) => c.state !== 'na');
	if (!scored.length) return 0;
	return axis.passed / scored.length;
}

function axisFailRate(axis: SnowflakeProfileV1['axes'][number]): number {
	const scored = axis.checks.filter((c) => c.state !== 'na');
	if (!scored.length) return 0;
	const fail = scored.filter((c) => c.state === 'fail').length;
	return fail / scored.length;
}

export function mountSnowflakeRadar(host: HTMLElement, profile: SnowflakeProfileV1): SnowflakeRadarHandle {
	const chart = echarts.init(host);
	const indicators = profile.axes.map((axis) => ({
		name: axis.label,
		max: 1,
	}));
	const passRates = profile.axes.map(axisPassRate);
	const failRates = profile.axes.map(axisFailRate);
	const hasScored = passRates.some((v) => v > 0) || failRates.some((v) => v > 0);

	chart.setOption({
		animation: !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
		tooltip: {
			backgroundColor: tipBg,
			borderColor: 'rgba(255,255,255,0.12)',
			textStyle: { color: '#fff', fontSize: 11 },
			formatter: () => {
				return profile.axes
					.map((axis) => `${axis.label}: ${axis.scoreLabel}`)
					.join('<br/>');
			},
		},
		radar: {
			center: ['50%', '54%'],
			radius: hasScored ? '62%' : '58%',
			indicator: indicators,
			axisName: { color: muted, fontSize: 10 },
			splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
			splitArea: { areaStyle: { color: ['rgba(255,255,255,0.02)', 'rgba(255,255,255,0.05)'] } },
			axisLine: { lineStyle: { color: 'rgba(255,255,255,0.14)' } },
		},
		series: [
			{
				type: 'radar',
				data: [
					{
						name: 'Pass (scored checks)',
						value: passRates,
						areaStyle: { color: accentFill },
						lineStyle: { color: accent, width: 2 },
						itemStyle: { color: accent },
						symbol: 'circle',
						symbolSize: 4,
					},
					{
						name: 'Fail (scored checks)',
						value: failRates,
						areaStyle: { color: failFill },
						lineStyle: { color: failColor, width: 1.5, type: 'dashed' },
						itemStyle: { color: failColor },
						symbol: 'circle',
						symbolSize: 3,
					},
				],
			},
		],
		graphic: hasScored
			? []
			: [
					{
						type: 'text',
						left: 'center',
						top: 'middle',
						style: {
							text: 'Awaiting scored checks',
							fill: muted,
							fontSize: 11,
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
