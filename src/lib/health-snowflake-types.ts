/**
 * Snowflake health profile (5 axes) — shared by Train UI and api.qbitos.ai consumers.
 * Aligns with Ritual ROI–style checks; dividend axis may be partial until EDGAR/FMP jobs land.
 */

export type SnowflakeCheckState = 'pass' | 'fail' | 'na';

export type SnowflakeCheck = {
	id: string;
	label: string;
	detail: string;
	state: SnowflakeCheckState;
};

export type SnowflakeAxisName = 'value' | 'future' | 'past' | 'health' | 'dividends';

export type SnowflakeAxis = {
	name: SnowflakeAxisName;
	label: string;
	scoreLabel: string;
	passed: number;
	total: number;
	checks: SnowflakeCheck[];
};

export type SnowflakeProfileV1 = {
	schemaVersion: 1;
	ticker: string;
	displayName?: string;
	asOfISO: string;
	sourceNotes: string[];
	axes: SnowflakeAxis[];
};
