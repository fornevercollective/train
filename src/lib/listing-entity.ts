/**
 * Legal-entity display helpers for listing profiles.
 * Prefers enriched `ln` (e.g. "Tesla, Inc.") over short trade names (`nm`).
 */

export type CatalogListingRecord = {
	id?: string;
	sy?: string;
	nm?: string;
	ln?: string;
	co?: string;
	cc?: string;
	ls?: string;
	registry?: {
		source?: string;
		jurisdiction?: string;
		companyId?: string;
		license?: string;
	};
};

export function legalEntityLabel(record: CatalogListingRecord): string {
	const legal = String(record.ln || '').trim();
	const trade = String(record.nm || '').trim();
	if (legal) return legal;
	return trade || String(record.id || record.sy || 'Listing');
}

export function tradeNameLabel(record: CatalogListingRecord): string {
	return String(record.nm || record.sy || record.id || '').trim();
}

export function legalEntityDiffersFromTradeName(record: CatalogListingRecord): boolean {
	const legal = String(record.ln || '').trim().toLowerCase();
	const trade = String(record.nm || '').trim().toLowerCase();
	if (!legal || !trade) return false;
	return legal !== trade;
}

export function secEdgarCompanyUrl(record: CatalogListingRecord): string | null {
	const registry = record.registry;
	if (!registry || registry.source !== 'sec_edgar') return null;
	const cik = String(registry.companyId || '').trim().replace(/^0+/, '');
	if (!cik) return null;
	return `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${encodeURIComponent(cik)}`;
}

export function openRegistryCompanyUrl(record: CatalogListingRecord): string | null {
	const registry = record.registry;
	if (!registry || registry.source !== 'openregistry') return null;
	const jurisdiction = String(registry.jurisdiction || '').trim().toLowerCase();
	const companyId = String(registry.companyId || '').trim();
	if (!jurisdiction || !companyId) return null;
	return `https://openregistry.sophymarine.com/company/${jurisdiction}/${companyId}`;
}

export function registryAttribution(record: CatalogListingRecord): string | null {
	if (record.ls === 'sec_edgar') return 'SEC EDGAR (public domain)';
	if (record.ls === 'openregistry') return 'OpenRegistry · statutory registry';
	const registry = record.registry;
	if (registry?.source === 'openregistry') {
		const license = registry.license ? ` · ${registry.license}` : '';
		return `OpenRegistry${license}`;
	}
	return null;
}
