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

export interface SolutionData {
    name: string;
    description: string;
    industries: string[];
    features: string[];
    benefits: string[];
    useCases: string[];
}

export interface CompetitorData {
    name: string;
    logoUrl: string;
    description: string;
    strategies: string[];
    category: string;
    website: string;
    location: string;
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

export const mapApiResponseToSolutions = (response: CompanyAnalysisResponse): SolutionData[] => {
    if (!response.solutions_profile || !Array.isArray(response.solutions_profile)) {
        return [];
    }

    return response.solutions_profile.map((solution: any) => ({
        name: solution.Title || 'Unnamed Solution',
        description: solution.Description || '',
        industries: Array.isArray(solution.Target_Industries) ? solution.Target_Industries : [],
        features: Array.isArray(solution.Features) ? solution.Features.slice(0, 5) : [],
        benefits: Array.isArray(solution.Benefits) ? solution.Benefits.slice(0, 3) : [],
        useCases: Array.isArray(solution.Use_Cases) ? solution.Use_Cases.slice(0, 3) : []
    }));
};

export const mapApiResponseToCompetitors = (response: CompanyAnalysisResponse): CompetitorData[] => {
    const competitors = response.company_profile?.competitors;

    if (!competitors || !Array.isArray(competitors)) {
        return [];
    }

    return competitors.map((competitor: any) => {
        // Determine category based on type
        let category = 'Emerging';
        if (competitor.type === 'direct') {
            category = 'Direct';
        } else if (competitor.type === 'indirect') {
            category = 'Indirect';
        }

        return {
            name: competitor.company_name || 'Unknown Company',
            logoUrl: competitor.website ? `https://logo.clearbit.com/${competitor.website}` : '',
            description: `${competitor.company_name} is a competitor based in ${competitor.location || 'Unknown location'}.`,
            strategies: [], // Not provided in API, could be populated later
            category: category,
            website: competitor.website || '',
            location: competitor.location || 'Unknown'
        };
    });
};
