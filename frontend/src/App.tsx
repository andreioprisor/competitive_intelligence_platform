import { useState } from 'react';
import { AppShell } from '@mantine/core';
import { Navbar } from './components/Layout/Navbar';
import { LandingPage } from './components/Features/LandingPage';
import { LoadingModal } from './components/Features/LoadingModal';
import { Dashboard } from './components/Features/Dashboard';
import { api } from './services/api';
import { mapApiResponseToCompanyData } from './utils/mapper';
import type { CompanyData } from './utils/mapper';

function App() {
  const [view, setView] = useState<'landing' | 'dashboard'>('landing');
  const [loading, setLoading] = useState(false);
  const [companyData, setCompanyData] = useState<CompanyData | null>(null);

  const handleSearch = async (domain: string) => {
    setLoading(true);
    try {
      const response = await api.fetchCompanyAnalysis(domain);
      const data = mapApiResponseToCompanyData(response);
      console.log(data);
      setCompanyData(data);
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
          companyData && <Dashboard companyData={companyData} />
        )}
      </AppShell.Main>

      <LoadingModal opened={loading} />
    </AppShell>
  );
}

export default App;
