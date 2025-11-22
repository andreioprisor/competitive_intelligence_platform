import type { CompanyAnalysisResponse } from '../services/api';

export interface CompanyData {
    domain: string;
    name: string;
    description: string;
    industry: string;
    location: string;
    employees: string;
    foundedYear: number;
    website: string;
    revenue: string;
    marketCap: string;
    keyProducts: string[];
    // UI specific fields
    logoUrl: string;
    domainOfActivity: string;
    differentiators: string;
    services: string;
    geography: string;
    businessModel: string;
    industryTrends: string[];
}

export const mapApiResponseToCompanyData = (response: CompanyAnalysisResponse): CompanyData => {
    const profile = response.company_profile;
    const coreBusiness = profile.core_business || {};
    const marketContext = profile.market_context || {};

    // Extract founded year
    const foundedMatch = coreBusiness.company_overview?.match(/founded.*?(\d{4})/i);
    const foundedYear = foundedMatch ? parseInt(foundedMatch[1]) : new Date().getFullYear();

    // Extract employees (simple cleanup if needed)
    const employees = coreBusiness.company_size || 'Unknown';

    // Helper to join array or return string
    const joinOrString = (val: any) => Array.isArray(val) ? val.join(', ') : (val || 'Unknown');

    return {
        domain: response.domain,
        name: profile.name || response.domain,
        description: coreBusiness.company_overview || '',
        industry: coreBusiness.industry || 'Unknown',
        location: 'Global', // Default as it's not explicitly in the sample
        employees: employees,
        foundedYear: foundedYear,
        website: `https://${response.domain}`,
        revenue: 'See Business Model', // Not structured in sample
        marketCap: 'Public', // Not structured in sample
        keyProducts: response.solutions_profile?.map((s: any) => s.Title) || [],

        // UI Mappings
        logoUrl: `https://logo.clearbit.com/${response.domain}`,
        domainOfActivity: coreBusiness.industry || 'Unknown',
        differentiators: joinOrString(marketContext.competitive_advantages),
        services: response.solutions_profile?.map((s: any) => s.Title).join(', ') || 'Unknown',
        geography: joinOrString(marketContext.addressed_geography),
        businessModel: coreBusiness.business_model || 'Unknown',
        industryTrends: Array.isArray(marketContext.industry_trends) ? marketContext.industry_trends.slice(0, 3) : []
    };
};
