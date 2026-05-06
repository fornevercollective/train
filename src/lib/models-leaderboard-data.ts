/** Static illustrative rows for the Train /models page — not vendor benchmarks. */

export type LlmDeskRow = {
	model: string;
	provider: string;
	params: string;
	context: string;
	inputPerM: number;
	outputPerM: number;
	mmluPro: number;
	intelligenceIdx: number;
	speedTps: number;
};

export const llmDeskRows: LlmDeskRow[] = [
	{
		model: 'Claude Opus 4.6',
		provider: 'Anthropic',
		params: 'N/A',
		context: '200K',
		inputPerM: 15,
		outputPerM: 75,
		mmluPro: 82,
		intelligenceIdx: 57,
		speedTps: 53,
	},
	{
		model: 'Gemini 3.1 Pro',
		provider: 'Google',
		params: 'N/A',
		context: '1M',
		inputPerM: 2,
		outputPerM: 12,
		mmluPro: 85,
		intelligenceIdx: 57,
		speedTps: 122,
	},
	{
		model: 'GPT-5.4 (xhigh)',
		provider: 'OpenAI',
		params: 'N/A',
		context: '1M',
		inputPerM: 2.5,
		outputPerM: 15,
		mmluPro: 88,
		intelligenceIdx: 57,
		speedTps: 87,
	},
	{
		model: 'DeepSeek V3.2',
		provider: 'DeepSeek',
		params: '685B',
		context: '130K',
		inputPerM: 0.28,
		outputPerM: 0.42,
		mmluPro: 85,
		intelligenceIdx: 52,
		speedTps: 64,
	},
	{
		model: 'Grok 4.3',
		provider: 'xAI',
		params: 'N/A',
		context: '131K',
		inputPerM: 3,
		outputPerM: 15,
		mmluPro: 84,
		intelligenceIdx: 53,
		speedTps: 190,
	},
	{
		model: 'gpt-oss-120B (high)',
		provider: 'OpenAI',
		params: '117B',
		context: '128K',
		inputPerM: 0.15,
		outputPerM: 0.6,
		mmluPro: 90,
		intelligenceIdx: 33,
		speedTps: 228,
	},
];

export type BenchmarkMini = { label: string; value: number };

export type BenchmarkBlock = {
	slug: string;
	title: string;
	lede: string;
	minis: BenchmarkMini[];
};

export const benchmarkBlocks: BenchmarkBlock[] = [
	{
		slug: 'ace',
		title: 'ACE-style consumer desk index',
		lede:
			'Illustrative “everyday desk tasks” scores (shopping-style rubrics remapped to catalog QA). Not the real ACE benchmark; layout inspired by benchmark rows on third-party leaderboards.',
		minis: [
			{ label: 'Browse + filter', value: 56 },
			{ label: 'Schema match', value: 61 },
			{ label: 'Multi-hop note', value: 49 },
		],
	},
	{
		slug: 'coding',
		title: 'Coding lane (static proxy)',
		lede:
			'Represents how often the desk runbook routes through codegen vs SQL for Erika transforms — synthetic percentages for layout only.',
		minis: [
			{ label: 'Patch apply', value: 72 },
			{ label: 'Test harness', value: 64 },
			{ label: 'Docs cross-link', value: 58 },
		],
	},
	{
		slug: 'agentic',
		title: 'Agentic relay stress',
		lede:
			'Captions + relay fan-out scenarios scored on a 0–100 static scale. Mirrors how third-party leaderboards stack agent and speed tabs (see page intro for external references).',
		minis: [
			{ label: 'Tool budget', value: 54 },
			{ label: 'Retry discipline', value: 67 },
			{ label: 'Handoff clarity', value: 51 },
		],
	},
];
