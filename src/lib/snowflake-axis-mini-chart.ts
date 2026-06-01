/**
 * Per-axis mini snowflake radars (one check = one spoke).
 */

import * as echarts from 'echarts/core';
import { RadarChart } from 'echarts/charts';
import { RadarComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { SnowflakeAxis } from './health-snowflake-types';
import type { SnowflakeRadarHandle } from './snowflake-radar-chart';

echarts.use([RadarChart, RadarComponent, CanvasRenderer]);

const muted = 'rgba(255, 255, 255, 0.55)';

function checkScore(state: string): number {
	if (state === 'pass') return 1;
	if (state === 'fail') return 0.2;
	return 0.45;
}

export function mountSnowflakeAxisMini(
	host: HTMLElement,
	axis: SnowflakeAxis,
): SnowflakeRadarHandle {
	const chart = echarts.init(host);
	const indicators = axis.checks.map((c) => ({
		name: c.label.length > 12 ? `${c.label.slice(0, 11)}…` : c.label,
		max: 1,
	}));
	const values = axis.checks.map((c) => checkScore(c.state));

	chart.setOption({
		animation: false,
		radar: {
			center: ['50%', '52%'],
			radius: '62%',
			indicator: indicators,
			axisName: { show: false },
			splitLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
			axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
		},
		series: [
			{
				type: 'radar',
				data: [
					{
						value: values,
						areaStyle: { color: 'rgba(120, 200, 255, 0.2)' },
						lineStyle: { color: 'rgba(120, 200, 255, 0.85)', width: 1 },
						itemStyle: { color: 'rgba(120, 200, 255, 0.9)' },
						symbolSize: 2,
					},
				],
			},
		],
		graphic: [
			{
				type: 'text',
				left: 'center',
				bottom: 2,
				style: {
					text: `${axis.label} · ${axis.scoreLabel}`,
					fill: muted,
					fontSize: 8,
					textAlign: 'center',
				},
			},
		],
	});

	const ro = new ResizeObserver(() => chart.resize());
	ro.observe(host);

	return {
		dispose() {
			ro.disconnect();
			chart.dispose();
		},
	};
}

export type SnowflakeAxisGridHandle = { dispose: () => void };

export function mountSnowflakeAxisGrid(
	container: HTMLElement,
	axes: SnowflakeAxis[],
): SnowflakeAxisGridHandle {
	const handles: SnowflakeRadarHandle[] = [];
	container.innerHTML = '';
	for (const axis of axes) {
		const cell = document.createElement('div');
		cell.className = 'snowflake-mini-cell';
		cell.setAttribute('aria-label', `${axis.label} axis snowflake`);
		const host = document.createElement('div');
		host.className = 'snowflake-mini-radar';
		cell.appendChild(host);
		container.appendChild(cell);
		handles.push(mountSnowflakeAxisMini(host, axis));
	}
	return {
		dispose() {
			for (const h of handles) h.dispose();
		},
	};
}
