import { Select, Button, Stack, Paper, Title, Group } from '@mantine/core';
import { IconGitCompare } from '@tabler/icons-react';
import { useState } from 'react';
import { api } from '../../../services/api';
import { ComparisonReportModal } from '../ComparisonReportModal/ComparisonReportModal';

interface Solution {
    name: string;
    industries?: string[];
}

interface Competitor {
    name: string;
    website?: string;
    solutions?: string[];
}

interface SolutionComparisonProps {
    mySolutions: Solution[];
    competitors: Competitor[];
    companyDomain: string;
}

export function SolutionComparison({ mySolutions, competitors, companyDomain }: SolutionComparisonProps) {
    const [selectedCompetitor, setSelectedCompetitor] = useState<string | null>(null);
    const [selectedCompetitorSolution, setSelectedCompetitorSolution] = useState<string | null>(null);
    const [autoMappedSolution, setAutoMappedSolution] = useState<string | null>(null);
    const [modalOpened, setModalOpened] = useState(false);
    const [comparisonReport, setComparisonReport] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const selectedCompetitorData = competitors.find(c => c.name === selectedCompetitor);
    const competitorSolutions = selectedCompetitorData?.solutions || [];

    const handleCompare = async () => {
        if (!selectedCompetitor || !selectedCompetitorSolution) return;

        try {
            setLoading(true);
            setModalOpened(true);
            setComparisonReport(null);
            setAutoMappedSolution(null);

            // Get competitor domain (website)
            const competitorDomain = selectedCompetitorData?.website || selectedCompetitor;

            console.log('Fetching comparison:', {
                domain: companyDomain,
                competitorDomain,
                competitorSolution: selectedCompetitorSolution
            });

            const result = await api.compareSolutions(
                companyDomain,
                competitorDomain,
                selectedCompetitorSolution
            );

            // Store auto-mapped solution
            setAutoMappedSolution(result.company_solution);

            // Build HTML report from database fields
            const reportHTML = `
                <div style="font-family: system-ui, -apple-system, sans-serif; padding: 20px; max-width: 900px; margin: 0 auto;">
                    <h2 style="text-align: center; color: #2C3E50; margin-bottom: 30px;">Solution Comparison</h2>

                    <div style="background: #F8F9FA; padding: 20px; border-radius: 8px; margin-bottom: 30px;">
                        <p style="margin: 8px 0;"><strong>Your Solution:</strong> <span style="color: #27AE60; font-size: 18px;">${result.company_solution}</span></p>
                        <p style="margin: 8px 0;"><strong>Competitor Solution:</strong> <span style="color: #E74C3C; font-size: 18px;">${result.competitor_solution}</span></p>
                        <p style="margin: 8px 0;"><strong>Competitor:</strong> ${result.competitor_name || competitorDomain}</p>
                    </div>

                    <div style="margin-bottom: 30px;">
                        <h3 style="color: #27AE60; border-bottom: 3px solid #27AE60; padding-bottom: 10px; display: flex; align-items: center;">
                            <span style="font-size: 24px; margin-right: 10px;">✓</span> Our Advantages
                        </h3>
                        <ul style="list-style: none; padding-left: 0;">
                            ${result.we_are_better.map(item => `
                                <li style="padding: 12px; margin: 8px 0; background: #E8F8F5; border-left: 4px solid #27AE60; border-radius: 4px;">
                                    ${item}
                                </li>
                            `).join('')}
                        </ul>
                    </div>

                    <div style="margin-bottom: 30px;">
                        <h3 style="color: #E74C3C; border-bottom: 3px solid #E74C3C; padding-bottom: 10px; display: flex; align-items: center;">
                            <span style="font-size: 24px; margin-right: 10px;">⚠</span> Their Advantages
                        </h3>
                        <ul style="list-style: none; padding-left: 0;">
                            ${result.they_are_better.map(item => `
                                <li style="padding: 12px; margin: 8px 0; background: #FADBD8; border-left: 4px solid #E74C3C; border-radius: 4px;">
                                    ${item}
                                </li>
                            `).join('')}
                        </ul>
                    </div>

                    <div>
                        <h3 style="color: #3498DB; border-bottom: 3px solid #3498DB; padding-bottom: 10px; display: flex; align-items: center;">
                            <span style="font-size: 24px; margin-right: 10px;">📊</span> Conclusion
                        </h3>
                        <ul style="list-style: none; padding-left: 0;">
                            ${result.conclusion.map(item => `
                                <li style="padding: 12px; margin: 8px 0; background: #EBF5FB; border-left: 4px solid #3498DB; border-radius: 4px;">
                                    ${item}
                                </li>
                            `).join('')}
                        </ul>
                    </div>
                </div>
            `;

            setComparisonReport(reportHTML);
            console.log('Comparison fetched successfully');
        } catch (error) {
            console.error('Failed to fetch comparison:', error);
            setComparisonReport('<p style="color: red;">Failed to load comparison report. Please try again.</p>');
        } finally {
            setLoading(false);
        }
    };

    const isCompareDisabled = !selectedCompetitor || !selectedCompetitorSolution;

    return (
        <Stack gap="xl">
            <Title order={3}>Compare Solutions</Title>

            <Paper
                withBorder
                radius="md"
                p="lg"
                bg="var(--mantine-color-body)"
                style={{ maxWidth: '600px', margin: '0 auto' }}
            >
                <Stack gap="md">
                    <Title order={4} c="blue">Select Competitor to Compare</Title>
                    <Select
                        label="Select Competitor"
                        placeholder="Choose a competitor"
                        data={competitors.map(c => c.name)}
                        value={selectedCompetitor}
                        onChange={(value) => {
                            setSelectedCompetitor(value);
                            setSelectedCompetitorSolution(null);
                            setAutoMappedSolution(null);
                        }}
                        searchable
                        clearable
                        size="md"
                    />

                    <Select
                        label="Competitor's Solution"
                        placeholder="Choose their solution"
                        data={competitorSolutions}
                        value={selectedCompetitorSolution}
                        onChange={setSelectedCompetitorSolution}
                        disabled={!selectedCompetitor || competitorSolutions.length === 0}
                        searchable
                        clearable
                        size="md"
                    />

                    {autoMappedSolution && (
                        <Paper
                            p="md"
                            bg="#FFF9E6"
                            style={{
                                border: '2px solid #FFD700',
                                borderRadius: '8px',
                                marginTop: '8px'
                            }}
                        >
                            <Title order={6} c="orange" mb="xs">Auto-Mapped Your Solution:</Title>
                            <Title order={5} c="orange">{autoMappedSolution}</Title>
                        </Paper>
                    )}
                </Stack>
            </Paper>

            <Group justify="center">
                <Button
                    leftSection={<IconGitCompare size={18} />}
                    onClick={handleCompare}
                    disabled={isCompareDisabled}
                    size="lg"
                >
                    Compare Solutions
                </Button>
            </Group>

            <ComparisonReportModal
                opened={modalOpened}
                onClose={() => setModalOpened(false)}
                report={comparisonReport}
                loading={loading}
                companySolution={autoMappedSolution || ''}
                competitorSolution={selectedCompetitorSolution || ''}
                competitorDomain={selectedCompetitorData?.website || selectedCompetitor || ''}
            />
        </Stack>
    );
}
