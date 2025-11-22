export interface CompanyAnalysisResponse {
    domain: string;
    company_profile: any;
    solutions_profile: any[];
    analysis_metadata: any;
}

const API_BASE_URL = 'http://localhost:8000';

export const api = {
    async fetchCompanyAnalysis(domain: string): Promise<CompanyAnalysisResponse> {
        const response = await fetch(`${API_BASE_URL}/profile_competitors_solution?domain=${encodeURIComponent(domain)}`);

        if (!response.ok) {
            throw new Error(`API call failed: ${response.statusText}`);
        }

        return response.json();
    }
};
