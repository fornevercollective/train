/**
 * Static mock for a GitHub Models–style side-by-side compare (Compare tab pattern).
 * @see https://github.blog/changelog/2025-05-19-github-models-built-into-your-repository-is-in-public-preview/
 */

export const modelTesterLinks = {
	marketplaceModels: 'https://github.com/marketplace/models',
	marketplaceTypeModels: 'https://github.com/marketplace?type=models',
	changelog: 'https://github.blog/changelog/2025-05-19-github-models-built-into-your-repository-is-in-public-preview/',
} as const;

export type ModelTesterScoreVariant = 'high' | 'mid' | 'low';

export type ModelTesterColumn = {
	/** <select> option values */
	options: { value: string; label: string }[];
	selectedValue: string;
	versionLabel: string;
	modelSize: string;
	lastUpdated: string;
	scorePct: string;
	scoreVariant: ModelTesterScoreVariant;
	inputTok: number;
	outputTok: number;
	latencyMs: number;
	metrics: { label: string; value: string }[];
	/** JSON body split so the middle segment can be wrapped in <mark> */
	jsonParts: { text: string; diff?: boolean }[];
};

export const modelTesterContext =
	'erika-market / Add categories to transaction prompt #6233';

export const modelTesterColumns: ModelTesterColumn[] = [
	{
		options: [
			{ value: 'gpt-4.1', label: 'OpenAI GPT-4.1' },
			{ value: 'gpt-4o', label: 'OpenAI GPT-4o' },
		],
		selectedValue: 'gpt-4.1',
		versionLabel: 'Original main',
		modelSize: 'private',
		lastUpdated: '2025-05',
		scorePct: '90.00',
		scoreVariant: 'high',
		inputTok: 842,
		outputTok: 186,
		latencyMs: 920,
		metrics: [
			{ label: 'Correct categorization', value: '0.90' },
			{ label: 'Confidence calibration', value: '0.82' },
			{ label: 'JSON validation', value: 'pass' },
		],
		jsonParts: [
			{ text: '{\n  "categories": [\n    { "name": "Groceries", "confidence": 0.91 },\n    { "name": "Transport", "confidence": 0.88 }\n  ]\n}' },
		],
	},
	{
		options: [
			{ value: 'llama-scout', label: 'Llama 4 Scout' },
			{ value: 'llama-mav', label: 'Llama 4 Maverick' },
		],
		selectedValue: 'llama-scout',
		versionLabel: 'Version 1',
		modelSize: 'MoE / Scout',
		lastUpdated: '2025-04',
		scorePct: '50.55',
		scoreVariant: 'low',
		inputTok: 842,
		outputTok: 204,
		latencyMs: 1410,
		metrics: [
			{ label: 'Correct categorization', value: '0.30' },
			{ label: 'Confidence calibration', value: '0.55' },
			{ label: 'JSON validation', value: 'pass' },
		],
		jsonParts: [
			{ text: '{\n  "categories": [\n    { "name": "' },
			{ text: 'Culture', diff: true },
			{ text: '", "confidence": ' },
			{ text: '0.30', diff: true },
			{ text: ' },\n    { "name": "Transport", "confidence": 0.61 }\n  ]\n}' },
		],
	},
	{
		options: [
			{ value: 'cohere-v2', label: 'Cohere v2' },
			{ value: 'command-r', label: 'Command R' },
		],
		selectedValue: 'cohere-v2',
		versionLabel: 'Version 2',
		modelSize: 'private',
		lastUpdated: '2025-10',
		scorePct: '77.60',
		scoreVariant: 'mid',
		inputTok: 842,
		outputTok: 178,
		latencyMs: 680,
		metrics: [
			{ label: 'Correct categorization', value: '0.72' },
			{ label: 'Confidence calibration', value: '0.79' },
			{ label: 'JSON validation', value: 'pass' },
		],
		jsonParts: [
			{ text: '{\n  "categories": [\n    { "name": "Groceries", "confidence": 0.85 },\n    { "name": "Transport", "confidence": 0.77 }\n  ]\n}' },
		],
	},
];
