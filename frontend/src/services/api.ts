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

export interface CompetitorResponse {
    domain: string;
    solutions: any[];
    id: number;
}

export interface SolutionsComparisonResponse {
    comparison_result: string;
    cached: boolean;
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

    async compareSolutions(
        domain: string,
        companySolution: any,
        competitorSolution: any,
        model: string = 'gemini-3-pro-preview'
    ): Promise<SolutionsComparisonResponse> {
        const companySolutionStr = encodeURIComponent(JSON.stringify(companySolution));
        const competitorSolutionStr = encodeURIComponent(JSON.stringify(competitorSolution));
        const modelStr = encodeURIComponent(model);

        const response = await fetch(
            `${API_BASE_URL}/solutions_comparison?domain=${encodeURIComponent(domain)}&company_solution=${companySolutionStr}&competitor_solution=${competitorSolutionStr}&model=${modelStr}`
        );

        if (!response.ok) {
            throw new Error(`API call failed: ${response.statusText}`);
        }

        return response.json();
    }
};
