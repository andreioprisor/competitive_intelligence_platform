export interface CompanyAnalysisResponse {
    domain: string;
    company_profile: any;
    solutions_profile: any[];
    analysis_metadata: any;
}

export interface CompanyProfileUpdateRequest {
    company_profile: any;
}

export interface SolutionUpdateRequest {
    solution: any;
}

export interface CompetitorCreateRequest {
    competitor: any;
}

export interface CategoryObservationRequest {
    category_label: string;
    description: string;
}

export interface CategoryObservationResponse {
    id: number;
    name: string;
    definition: string;
    company_id: number;
}

export interface AddCriteriaRequest {
    domain: string;
    criteria_name: string;
    criteria_definition: string;
    value_ranges?: Record<string, string>;
}

export interface AddCriteriaResponse {
    success: boolean;
    message: string;
    criteria_id: number;
    criteria_name: string;
    company_id: number;
    company_name: string;
    competitors_analyzed: number;
    total_competitors: number;
    analysis_results: Record<string, any>;
    execution_time_seconds: number;
}

export interface CompetitorResponse {
    domain: string;
    solutions: any[];
    id: number;
}

export interface SolutionsComparisonResponse {
    comparison_result: string;
    cached: boolean;
}

export interface EnrichCompetitorsRequest {
    domain: string;
    force_refresh?: boolean;
}

export interface EnrichCompetitorsResponse {
    success: boolean;
    message: string;
    company_id: number;
    company_name: string;
    competitors_enriched: number;
    total_competitors: number;
    enrichment_results: {
        total: number;
        successful: number;
        failed: number;
        results: Array<{
            competitor_domain: string;
            competitor_id: number;
            success: boolean;
            data: any;
        }>;
        execution_time_seconds: number;
        company_name: string;
    };
    execution_time_seconds: number;
}

const API_BASE_URL = 'http://localhost:8000';

export const api = {
    async fetchCompanyAnalysis(domain: string): Promise<CompanyAnalysisResponse> {
        const response = await fetch(`${API_BASE_URL}/profile_competitors_solution?domain=${encodeURIComponent(domain)}`);

        if (!response.ok) {
            throw new Error(`API call failed: ${response.statusText}`);
        }

        return response.json();
    },

    async saveCompanyProfile(data: CompanyAnalysisResponse): Promise<any> {
        const response = await fetch(`${API_BASE_URL}/save_company_profile`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error(`API call failed: ${response.statusText}`);
        }

        return response.json();
    },

    async getCompanyProfile(domain: string): Promise<{ company_profile: any; cache_hit: boolean }> {
        const response = await fetch(`${API_BASE_URL}/company_profile?domain=${encodeURIComponent(domain)}`);

        if (!response.ok) {
            throw new Error(`API call failed: ${response.statusText}`);
        }

        return response.json();
    },

    async updateCompanyProfile(domain: string, data: CompanyProfileUpdateRequest): Promise<{ status: string; message: string }> {
        const response = await fetch(`${API_BASE_URL}/company_profile?domain=${encodeURIComponent(domain)}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error(`API call failed: ${response.statusText}`);
        }

        return response.json();
    },

    async getSolutions(domain: string): Promise<any[]> {
        const response = await fetch(`${API_BASE_URL}/solutions?domain=${encodeURIComponent(domain)}`);

        if (!response.ok) {
            throw new Error(`API call failed: ${response.statusText}`);
        }

        return response.json();
    },

    async updateSolution(domain: string, data: SolutionUpdateRequest): Promise<{ status: string; message: string }> {
        const response = await fetch(`${API_BASE_URL}/solutions?domain=${encodeURIComponent(domain)}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error(`API call failed: ${response.statusText}`);
        }

        return response.json();
    },

    async getCompetitors(domain: string): Promise<CompetitorResponse[]> {
        const response = await fetch(`${API_BASE_URL}/competitors?domain=${encodeURIComponent(domain)}`);

        if (!response.ok) {
            throw new Error(`API call failed: ${response.statusText}`);
        }

        return response.json();
    },

    async addCompetitor(domain: string, data: CompetitorCreateRequest): Promise<{ status: string; message: string }> {
        const response = await fetch(`${API_BASE_URL}/competitors?domain=${encodeURIComponent(domain)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error(`API call failed: ${response.statusText}`);
        }

        return response.json();
    },

    async deleteCompetitor(domain: string, competitorDomain: string): Promise<{ status: string; message: string }> {
        const response = await fetch(
            `${API_BASE_URL}/competitors?domain=${encodeURIComponent(domain)}&competitor_domain=${encodeURIComponent(competitorDomain)}`,
            {
                method: 'DELETE',
            }
        );

        if (!response.ok) {
            throw new Error(`API call failed: ${response.statusText}`);
        }

        return response.json();
    },

    async enrichCompetitors(request: { domain: string }): Promise<any> {
        const response = await fetch(`${API_BASE_URL}/enrich-competitors`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(request)
        });

        if (!response.ok) {
            throw new Error(`API call failed: ${response.statusText}`);
        }

        return response.json();
    },

    async recordCategoryObservation(domain: string, data: CategoryObservationRequest): Promise<CategoryObservationResponse> {
        const response = await fetch(`${API_BASE_URL}/category_observed?domain=${encodeURIComponent(domain)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error(`API call failed: ${response.statusText}`);
        }

        return response.json();
    },

    async addCriteria(request: AddCriteriaRequest): Promise<AddCriteriaResponse> {
        const response = await fetch(`${API_BASE_URL}/add-criteria`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(request)
        });

        if (!response.ok) {
            throw new Error(`API call failed: ${response.statusText}`);
        }

        return response.json();
    },

    async getTimeline(filters: TimelineRequest = {}): Promise<TimelineResponse> {
        const response = await fetch(`${API_BASE_URL}/timeline`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(filters)
        });

        if (!response.ok) {
            throw new Error(`API call failed: ${response.statusText}`);
        }

        return response.json();
    },

    async compareSolutions(
        domain: string,
        competitorDomain: string,
        competitorSolutionName: string
    ): Promise<{
        success: boolean;
        company_solution: string;
        competitor_solution: string;
        competitor_name: string;
        we_are_better: string[];
        they_are_better: string[];
        conclusion: string[];
        cached: boolean;
    }> {
        const response = await fetch(
            `${API_BASE_URL}/solutions_comparison?` +
            `domain=${encodeURIComponent(domain)}&` +
            `competitor_domain=${encodeURIComponent(competitorDomain)}&` +
            `competitor_solution_name=${encodeURIComponent(competitorSolutionName)}`
        );

        if (!response.ok) {
            throw new Error(`API call failed: ${response.statusText}`);
        }

        return response.json();
    },

    async enrichCompetitors(domain: string, force_refresh: boolean = false): Promise<EnrichCompetitorsResponse> {
        const response = await fetch(`${API_BASE_URL}/enrich-competitors`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ domain, force_refresh })
        });

        if (!response.ok) {
            throw new Error(`API call failed: ${response.statusText}`);
        }

        return response.json();
    }
};
