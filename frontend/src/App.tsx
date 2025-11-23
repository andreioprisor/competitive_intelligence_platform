import { useState } from 'react';
import { AppShell } from '@mantine/core';
import { Navbar } from './components/Layout/Navbar';
import { LandingPage } from './components/Features/LandingPage';
import { LoadingModal } from './components/Features/LoadingModal';
import { Dashboard } from './components/Features/Dashboard';
import { api } from './services/api';
import { mapApiResponseToCompanyData, mapApiResponseToSolutions, mapApiResponseToCompetitors } from './utils/mapper';
import type { CompanyData, SolutionData, CompetitorData } from './utils/mapper';
import type { CompanyAnalysisResponse } from './services/api';

function App() {
  const [view, setView] = useState<'landing' | 'dashboard'>('landing');
  const [loading, setLoading] = useState(false);
  const [companyData, setCompanyData] = useState<CompanyData | null>(null);
  const [apiResponse, setApiResponse] = useState<CompanyAnalysisResponse | null>(null);
  const [solutions, setSolutions] = useState<SolutionData[]>([]);
  const [competitors, setCompetitors] = useState<CompetitorData[]>([]);

  const handleSearch = async (domain: string) => {
    setLoading(true);
    try {
      const response = await api.fetchCompanyAnalysis(domain);
      setApiResponse(response);
      const data = mapApiResponseToCompanyData(response);
      const solutionsData = mapApiResponseToSolutions(response);
      const competitorsData = mapApiResponseToCompetitors(response);
      console.log(data);
      console.log('Solutions:', solutionsData);
      console.log('Competitors:', competitorsData);
      setCompanyData(data);
      setSolutions(solutionsData);
      setCompetitors(competitorsData);
      setView('dashboard');
    } catch (error) {
      console.error('Failed to fetch company data:', error);
      // TODO: Handle error state (show notification)
    } finally {
      setLoading(false);
    }
  };


  return (
    <AppShell header={{ height: 60 }} padding="md">
      <AppShell.Header>
        <Navbar />
      </AppShell.Header>

      <AppShell.Main>
        {view === 'landing' ? (
          <LandingPage onSearch={handleSearch} />
        ) : (
          companyData && apiResponse && (
            <Dashboard
              companyData={companyData}
              apiResponse={apiResponse}
              solutions={solutions}
              competitors={competitors}
            />
          )
        )}
      </AppShell.Main>

      <LoadingModal opened={loading} />
    </AppShell>
  );
}

export default App;
