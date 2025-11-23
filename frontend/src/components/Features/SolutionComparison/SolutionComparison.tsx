import { Select, Button, Stack, Paper, Title, Group, Grid } from '@mantine/core';
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
    const [selectedMySolution, setSelectedMySolution] = useState<string | null>(null);
    const [selectedCompetitor, setSelectedCompetitor] = useState<string | null>(null);
    const [selectedCompetitorSolution, setSelectedCompetitorSolution] = useState<string | null>(null);
    const [modalOpened, setModalOpened] = useState(false);
    const [comparisonReport, setComparisonReport] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const selectedCompetitorData = competitors.find(c => c.name === selectedCompetitor);
    const competitorSolutions = selectedCompetitorData?.solutions || [];

    const handleCompare = async () => {
        if (!selectedMySolution || !selectedCompetitor || !selectedCompetitorSolution) return;

        try {
            setLoading(true);
            setModalOpened(true);
            setComparisonReport(null);

            // Get competitor domain (website)
            const competitorDomain = selectedCompetitorData?.website || selectedCompetitor;

            console.log('Fetching comparison:', {
                domain: companyDomain,
                competitorDomain,
                companySolution: selectedMySolution,
                competitorSolution: selectedCompetitorSolution
            });

            const result = await api.compareSolutions(
                companyDomain,
                competitorDomain,
                selectedMySolution,
                selectedCompetitorSolution
            );

            setComparisonReport(result.formatted_report);
            console.log('Comparison fetched successfully');
        } catch (error) {
            console.error('Failed to fetch comparison:', error);
            setComparisonReport('<p style="color: red;">Failed to load comparison report. Please try again.</p>');
        } finally {
            setLoading(false);
        }
    };

    const isCompareDisabled = !selectedMySolution || !selectedCompetitor || !selectedCompetitorSolution;

    return (
        <Stack gap="xl">
            <Title order={3}>Compare Solutions</Title>

            <Grid gutter="xl">
                <Grid.Col span={{ base: 12, md: 6 }}>
                    <Paper withBorder radius="md" p="lg" bg="var(--mantine-color-body)">
                        <Stack gap="md">
                            <Title order={4} c="orange">Your Solution</Title>
                            <Select
                                label="Select Your Solution"
                                placeholder="Choose a solution"
                                data={mySolutions.map(s => s.name)}
                                value={selectedMySolution}
                                onChange={setSelectedMySolution}
                                searchable
                                clearable
                                size="md"
                            />
                        </Stack>
                    </Paper>
                </Grid.Col>

                <Grid.Col span={{ base: 12, md: 6 }}>
                    <Paper withBorder radius="md" p="lg" bg="var(--mantine-color-body)">
                        <Stack gap="md">
                            <Title order={4} c="blue">Competitor Details</Title>
                            <Select
                                label="Select Competitor"
                                placeholder="Choose a competitor"
                                data={competitors.map(c => c.name)}
                                value={selectedCompetitor}
                                onChange={(value) => {
                                    setSelectedCompetitor(value);
                                    setSelectedCompetitorSolution(null);
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
                        </Stack>
                    </Paper>
                </Grid.Col>
            </Grid>

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
                companySolution={selectedMySolution || ''}
                competitorSolution={selectedCompetitorSolution || ''}
                competitorDomain={selectedCompetitorData?.website || selectedCompetitor || ''}
            />
        </Stack>
    );
}
