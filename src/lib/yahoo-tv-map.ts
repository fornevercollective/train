/** Yahoo Finance-style tickers → TradingView symbols for mini embeds. */
export const YAHOO_TO_TRADINGVIEW: Record<string, string> = {
	'GC=F': 'COMEX:GC1!',
	'SI=F': 'COMEX:SI1!',
	'PL=F': 'NYMEX:PL1!',
	'PA=F': 'NYMEX:PA1!',
	'HG=F': 'COMEX:HG1!',
	'ALI=F': 'COMEX:ALI1!',
	'ES=F': 'CME:ES1!',
	QQQ: 'NASDAQ:QQQ',
	'^GSPC': 'SP:SPX',
	'BTC-USD': 'COINBASE:BTCUSD',
	MSFT: 'NASDAQ:MSFT',
	NVDA: 'NASDAQ:NVDA',
	AAPL: 'NASDAQ:AAPL',
};

export function tradingViewMiniUrl(tvSymbol: string): string {
	const params = new URLSearchParams({
		locale: 'en',
		symbol: tvSymbol,
		colorTheme: 'dark',
		isTransparent: 'true',
		autosize: 'true',
		interval: '60',
	});
	return `https://www.tradingview-widget.com/embed-widget/mini-symbol-overview/?${params.toString()}`;
}
