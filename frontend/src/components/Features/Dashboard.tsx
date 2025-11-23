import { Tabs, Grid, Container, Title, Text, Stack, Card, Modal, Button } from '@mantine/core';
import { IconBuildingSkyscraper, IconUsers, IconBulb, IconPlus, IconChartBar, IconGitCompare, IconTimeline, IconSettings } from '@tabler/icons-react';
import { MOCK_COMPETITORS, MOCK_SOLUTIONS, MOCK_TIMELINE_ALERTS } from '../../data/mockData';
import { CompanyCard } from './CompanyCard/CompanyCard';
import { CompetitorCard } from './CompetitorCard/CompetitorCard';
import { SolutionCard } from './SolutionCard/SolutionCard';
import { ComparisonTable } from './ComparisonTable/ComparisonTable';
import { SolutionComparison } from './SolutionComparison/SolutionComparison';
import { Timeline } from './Timeline/Timeline';
import { UserPreferences } from './UserPreferences/UserPreferences';
import { AddSolutionModal } from './AddSolutionModal/AddSolutionModal';
import { AddCompetitorModal } from './AddCompetitorModal/AddCompetitorModal';
import { CompetitorDetailsModal } from './CompetitorDetailsModal/CompetitorDetailsModal';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';
import type { DropResult } from '@hello-pangea/dnd';
import { useState, useEffect } from 'react';

import type { CompanyData, SolutionData, CompetitorData } from '../../utils/mapper';
import type { CompanyAnalysisResponse } from '../../services/api';
import { api } from '../../services/api';

interface DashboardProps {
    companyData: CompanyData;
    apiResponse: CompanyAnalysisResponse;
    solutions: SolutionData[];
    competitors: CompetitorData[];
}

export function Dashboard({ companyData, apiResponse, solutions: initialSolutions, competitors }: DashboardProps) {
    const [isSaved, setIsSaved] = useState(false);
    const [solutions, setSolutions] = useState(initialSolutions);
    const [addSolutionModalOpened, setAddSolutionModalOpened] = useState(false);
    const [addCompetitorModalOpened, setAddCompetitorModalOpened] = useState(false);
    const [showInfoModal, setShowInfoModal] = useState(true);
    const [selectedCompetitor, setSelectedCompetitor] = useState<typeof competitors[0] | null>(null);
    const [selectedCompetitorSolutions, setSelectedCompetitorSolutions] = useState<any>(null);
    const [backendCompetitors, setBackendCompetitors] = useState<CompetitorData[]>([]);
    const [competitorsWithSolutions, setCompetitorsWithSolutions] = useState<Array<{ name: string; website?: string; solutions?: string[] }>>([]);
    const [competitorsFullData, setCompetitorsFullData] = useState<Array<{ domain: string; solutions: any }>>([]);
    const [isEnrichingCompetitors, setIsEnrichingCompetitors] = useState(false);

    // Organize competitors by category
    const [columns, setColumns] = useState<{ [key: string]: CompetitorData[] }>(() => ({
        Direct: competitors.filter(c => c.category === 'Direct'),
        Indirect: competitors.filter(c => c.category === 'Indirect'),
        Emerging: competitors.filter(c => c.category === 'Emerging'),
    }));

    // Load competitors from backend when component mounts and company is saved
    useEffect(() => {
        if (!isSaved) return;

        const loadCompetitors = async () => {
            try {
                const competitorsFromBackend = await api.getCompetitors(companyData.domain);
                console.log('Loaded competitors from backend:', competitorsFromBackend);

                // Transform backend format to CompetitorData format
                const transformedCompetitors: CompetitorData[] = competitorsFromBackend.map(comp => ({
                    name: comp.domain,
                    logoUrl: '',
                    description: `Competitor: ${comp.domain}`,
                    strategies: [],
                    category: 'Direct', // Default category
                    website: comp.domain,
                    location: 'Unknown'
                }));

                setBackendCompetitors(transformedCompetitors);

                // Store competitors with solutions for SolutionComparison component
                const competitorsWithSols = competitorsFromBackend.map(comp => ({
                    name: comp.domain,
                    website: comp.domain,
                    solutions: (() => {
                        if (Array.isArray(comp.solutions)) {
                            return comp.solutions.map((sol: any) => sol.name || sol);
                        } else if (comp.solutions && typeof comp.solutions === 'object') {
                            // Handle enriched competitor structure with Solutions array
                            const solutionsObj: any = comp.solutions;
                            if (Array.isArray(solutionsObj.Solutions)) {
                                return solutionsObj.Solutions.map((sol: any) => sol.solution_name);
                            }
                            // Fallback to object keys
                            return Object.keys(comp.solutions);
                        }
                        return [];
                    })()
                }));
                setCompetitorsWithSolutions(competitorsWithSols);

                // Store full competitor data including solutions JSONB
                setCompetitorsFullData(competitorsFromBackend.map(comp => ({
                    domain: comp.domain,
                    solutions: comp.solutions
                })));

                // Merge backend competitors into columns by category
                if (transformedCompetitors.length > 0) {
                    const newColumns: { [key: string]: CompetitorData[] } = {
                        Direct: [...columns.Direct],
                        Indirect: [...columns.Indirect],
                        Emerging: [...columns.Emerging]
                    };

                    transformedCompetitors.forEach(comp => {
                        const category = comp.category || 'Direct';
                        // Only add if not already in the column
                        if (!newColumns[category].find((c: CompetitorData) => c.name === comp.name)) {
                            newColumns[category].push(comp);
                        }
                    });

                    setColumns(newColumns);
                }
            } catch (error) {
                console.error('Failed to load competitors from backend:', error);
            }
        };

        loadCompetitors();
    }, [isSaved, companyData.domain]);

    const onDragEnd = (result: DropResult) => {
        const { source, destination } = result;

        if (!destination) return;

        if (
            source.droppableId === destination.droppableId &&
            source.index === destination.index
        ) {
            return;
        }

        const sourceColumn = columns[source.droppableId];
        const destColumn = columns[destination.droppableId];
        const sourceItems = [...sourceColumn];
        const destItems = source.droppableId === destination.droppableId ? sourceItems : [...destColumn];

        const [removed] = sourceItems.splice(source.index, 1);

        if (source.droppableId === destination.droppableId) {
            sourceItems.splice(destination.index, 0, removed);
            setColumns({
                ...columns,
                [source.droppableId]: sourceItems,
            });
        } else {
            // Update category when moving to a different column
            const movedItem = { ...removed, category: destination.droppableId };
            destItems.splice(destination.index, 0, movedItem);
            setColumns({
                ...columns,
                [source.droppableId]: sourceItems,
                [destination.droppableId]: destItems,
            });
        }
    };

    const [customCategories, setCustomCategories] = useState<Array<{ id: string; label: string; description: string; isSystem?: boolean }>>([]);
    const [customMetricValues, setCustomMetricValues] = useState<Record<string, Record<string, string>>>({});
    const [loadingCategories, setLoadingCategories] = useState<Set<string>>(new Set());

    const handleAddCategory = async (newCategory: { label: string; description: string }) => {
        const id = `custom-${Date.now()}`;
        const categoryToAdd = { ...newCategory, id, isSystem: false };

        setCustomCategories(prev => [...prev, categoryToAdd]);
        setLoadingCategories(prev => new Set(prev).add(id));

        try {
            // Call the backend API to record category observation
            const response = await api.recordCategoryObservation(companyData.domain, {
                category_label: newCategory.label,
                description: newCategory.description
            });

            console.log('Category observation recorded:', response);

            // Simulate NLP data fetching (this could be replaced with real AI-generated values from backend)
            setTimeout(() => {
                const mockValues: Record<string, string> = {};
                const allCompanies = [
                    { name: companyData.name },
                    ...MOCK_COMPETITORS
                ];

                allCompanies.forEach(company => {
                    if (categoryToAdd.label.toLowerCase().includes('rate') || categoryToAdd.label.toLowerCase().includes('%')) {
                        mockValues[company.name] = `${Math.floor(Math.random() * 80 + 10)}%`;
                    } else if (categoryToAdd.label.toLowerCase().includes('score')) {
                        mockValues[company.name] = `${Math.floor(Math.random() * 50 + 50)}/100`;
                    } else {
                        mockValues[company.name] = ['High', 'Medium', 'Low', 'Very High'][Math.floor(Math.random() * 4)];
                    }
                });

                setCustomMetricValues(prev => ({
                    ...prev,
                    [id]: mockValues
                }));

                setLoadingCategories(prev => {
                    const next = new Set(prev);
                    next.delete(id);
                    return next;
                });
            }, 2500);
        } catch (error) {
            console.error('Failed to record category observation:', error);
            // Remove loading state on error
            setLoadingCategories(prev => {
                const next = new Set(prev);
                next.delete(id);
                return next;
            });
            // TODO: Show error notification
        }
    };

    const handleDeleteCategory = (id: string) => {
        setCustomCategories(prev => prev.filter(c => c.id !== id));
        setCustomMetricValues(prev => {
            const next = { ...prev };
            delete next[id];
            return next;
        });
    };

    const handleSaveProfile = async (updatedDescription: string) => {
        try {
            // Update the description in the API response
            const updatedResponse = {
                ...apiResponse,
                company_profile: {
                    ...apiResponse.company_profile,
                    core_business: {
                        ...apiResponse.company_profile.core_business,
                        company_overview: updatedDescription
                    }
                }
            };

            await api.saveCompanyProfile(updatedResponse);
            setIsSaved(true);
        } catch (error) {
            console.error('Failed to save company profile:', error);
            // TODO: Show error notification
        }
    };

    const handleAddSolution = async (newSolution: any) => {
        setSolutions(prev => [...prev, newSolution]);

        try {
            await api.updateSolution(companyData.domain, { solution: newSolution });
            console.log('Solution saved successfully:', newSolution);
        } catch (error) {
            console.error('Failed to save solution:', error);
            // TODO: Show error notification and revert state
        }
    };

    const handleAddCompetitor = async (newCompetitor: any) => {
        try {
            // Transform the competitor data to match CompetitorData interface
            const competitorData: CompetitorData = {
                name: newCompetitor.name,
                logoUrl: '',
                description: newCompetitor.description,
                strategies: [],
                category: newCompetitor.category,
                website: newCompetitor.website,
                location: newCompetitor.location
            };

            // Add to local state immediately for UI responsiveness
            setColumns(prev => ({
                ...prev,
                [newCompetitor.category]: [...prev[newCompetitor.category], competitorData]
            }));

            // Call backend API to save competitor
            await api.addCompetitor(companyData.domain, {
                competitor: {
                    domain: newCompetitor.domain,
                    name: newCompetitor.name,
                    solutions: []
                }
            });

            console.log('Competitor added successfully:', newCompetitor);
        } catch (error) {
            console.error('Failed to add competitor:', error);
            // TODO: Show error notification and revert state
        }
    };

    const handleDeleteCompetitor = async (competitor: CompetitorData, category: string) => {
        try {
            // Remove from local state immediately for UI responsiveness
            setColumns(prev => ({
                ...prev,
                [category]: prev[category].filter(c => c.name !== competitor.name)
            }));

            // Call backend API to delete competitor
            // Use website as domain identifier (which should be the domain)
            const competitorDomain = competitor.website || competitor.name;
            await api.deleteCompetitor(companyData.domain, competitorDomain);

            console.log('Competitor deleted successfully:', competitor.name);
        } catch (error) {
            console.error('Failed to delete competitor:', error);
            // Revert state on error - re-add the competitor
            setColumns(prev => ({
                ...prev,
                [category]: [...prev[category], competitor]
            }));
            // TODO: Show error notification
        }
    };

    const handleCloseInfoModal = () => {
        setShowInfoModal(false);
    };

    const handleEnrichCompetitors = async (forceRefresh: boolean = false) => {
        setIsEnrichingCompetitors(true);
        try {
            console.log(`Starting competitor enrichment (force_refresh=${forceRefresh})...`);
            const result = await api.enrichCompetitors(companyData.domain, forceRefresh);

            console.log('Enrichment completed:', result);

            // Reload competitors to get the enriched data
            const competitorsFromBackend = await api.getCompetitors(companyData.domain);

            // Transform backend format to CompetitorData format
            const transformedCompetitors: CompetitorData[] = competitorsFromBackend.map(comp => ({
                name: comp.domain,
                logoUrl: '',
                description: `Competitor: ${comp.domain}`,
                strategies: [],
                category: 'Direct',
                website: comp.domain,
                location: 'Unknown'
            }));

            setBackendCompetitors(transformedCompetitors);

            // Update competitors with solutions for SolutionComparison component
            const competitorsWithSols = competitorsFromBackend.map(comp => ({
                name: comp.domain,
                website: comp.domain,
                solutions: (() => {
                    if (Array.isArray(comp.solutions)) {
                        return comp.solutions.map((sol: any) => sol.name || sol);
                    } else if (comp.solutions && typeof comp.solutions === 'object') {
                        // Handle enriched competitor structure with Solutions array
                        const solutionsObj: any = comp.solutions;
                        if (Array.isArray(solutionsObj.Solutions)) {
                            return solutionsObj.Solutions.map((sol: any) => sol.solution_name);
                        }
                        // Fallback to object keys
                        return Object.keys(comp.solutions);
                    }
                    return [];
                })()
            }));
            setCompetitorsWithSolutions(competitorsWithSols);

            // Store full competitor data including solutions JSONB
            setCompetitorsFullData(competitorsFromBackend.map(comp => ({
                domain: comp.domain,
                solutions: comp.solutions
            })));

            // Show success message
            alert(`Successfully enriched ${result.competitors_enriched} out of ${result.total_competitors} competitors in ${result.execution_time_seconds.toFixed(2)} seconds!`);
        } catch (error) {
            console.error('Failed to enrich competitors:', error);
            alert(`Failed to enrich competitors: ${error instanceof Error ? error.message : 'Unknown error'}`);
        } finally {
            setIsEnrichingCompetitors(false);
        }
    };

    const handleCompetitorClick = (competitor: CompetitorData) => {
        setSelectedCompetitor(competitor);
        // Find the full solutions data for this competitor
        const fullData = competitorsFullData.find(c => c.domain === competitor.website || c.domain === competitor.name);
        setSelectedCompetitorSolutions(fullData?.solutions || null);
    };

    return (
        <Container size="xl" py="xl">
            <Tabs defaultValue="company">
                <Tabs.List mb="lg">
                    <Tabs.Tab value="company" leftSection={<IconBuildingSkyscraper size={16} />}>
                        Company Info
                    </Tabs.Tab>
                    {isSaved && (
                        <>
                            <Tabs.Tab value="solutions" leftSection={<IconBulb size={16} />}>
                                My Solutions
                            </Tabs.Tab>
                            <Tabs.Tab value="competitors" leftSection={<IconUsers size={16} />}>
                                Competitors
                            </Tabs.Tab>
                            <Tabs.Tab value="compare" leftSection={<IconChartBar size={16} />}>
                                Compare
                            </Tabs.Tab>
                            <Tabs.Tab value="compareSolutions" leftSection={<IconGitCompare size={16} />}>
                                Compare Solutions
                            </Tabs.Tab>
                            <Tabs.Tab value="timeline" leftSection={<IconTimeline size={16} />}>
                                Timeline
                            </Tabs.Tab>
                            <Tabs.Tab value="userPreferences" ml="auto" leftSection={<IconSettings size={16} />}>
                                User Preferences
                            </Tabs.Tab>
                        </>
                    )}
                </Tabs.List>

                <Tabs.Panel value="company">
                    <Modal
                        opened={showInfoModal && !isSaved}
                        onClose={handleCloseInfoModal}
                        title="Company Information"
                        centered
                        size="md"
                    >
                        <Stack gap="md">
                            <Text>
                                This is the current status of the company info. Modify accordingly if necessary, and press "Save" to continue.
                            </Text>
                            <Button onClick={handleCloseInfoModal} fullWidth>
                                Got it
                            </Button>
                        </Stack>
                    </Modal>

                    <Grid>
                        <Grid.Col span={{ base: 12, md: 8 }}>
                            <CompanyCard
                                data={companyData}
                                onSave={handleSaveProfile}
                                isSaved={isSaved}
                            />
                        </Grid.Col>
                    </Grid>
                </Tabs.Panel>

                <Tabs.Panel value="solutions">
                    <Grid>
                        {solutions.map((solution, index) => (
                            <Grid.Col key={index} span={{ base: 12, md: 4 }}>
                                <SolutionCard data={solution} />
                            </Grid.Col>
                        ))}
                        <Grid.Col span={{ base: 12, md: 4 }}>
                            <Card
                                withBorder
                                padding="lg"
                                radius="md"
                                h="100%"
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s ease',
                                    borderStyle: 'dashed',
                                    borderWidth: '2px'
                                }}
                                onClick={() => setAddSolutionModalOpened(true)}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.borderColor = 'var(--mantine-color-blue-6)';
                                    e.currentTarget.style.backgroundColor = 'var(--mantine-color-blue-0)';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.borderColor = '';
                                    e.currentTarget.style.backgroundColor = '';
                                }}
                            >
                                <Stack align="center" gap="xs">
                                    <IconPlus size={32} style={{ opacity: 0.6 }} />
                                    <Text size="lg" fw={500} c="dimmed">Add Solution</Text>
                                </Stack>
                            </Card>
                        </Grid.Col>
                    </Grid>

                    <AddSolutionModal
                        opened={addSolutionModalOpened}
                        onClose={() => setAddSolutionModalOpened(false)}
                        onAdd={handleAddSolution}
                    />
                </Tabs.Panel>

                <Tabs.Panel value="competitors">
                    <DragDropContext onDragEnd={onDragEnd}>
                        <Grid gutter={50}>
                            <Grid.Col span={{ base: 12, md: 4 }}>
                                <Title order={4} mb="xs">Direct Competitors</Title>
                                <Text size="sm" c="dimmed" mb="md">Direct rivals for the same customers</Text>
                                <Droppable droppableId="Direct">
                                    {(provided) => (
                                        <Stack gap="md" ref={provided.innerRef} {...provided.droppableProps} style={{ minHeight: '200px' }}>
                                            {columns.Direct.map((competitor, index) => (
                                                <Draggable key={competitor.name} draggableId={competitor.name} index={index}>
                                                    {(provided) => (
                                                        <div
                                                            ref={provided.innerRef}
                                                            {...provided.draggableProps}
                                                            {...provided.dragHandleProps}
                                                        >
                                                            <CompetitorCard
                                                                data={competitor}
                                                                onClick={() => handleCompetitorClick(competitor)}
                                                                onDelete={() => handleDeleteCompetitor(competitor, 'Direct')}
                                                            />
                                                        </div>
                                                    )}
                                                </Draggable>
                                            ))}
                                            {provided.placeholder}
                                        </Stack>
                                    )}
                                </Droppable>
                            </Grid.Col>

                            <Grid.Col span={{ base: 12, md: 4 }}>
                                <Title order={4} mb="xs">Indirect Competitors</Title>
                                <Text size="sm" c="dimmed" mb="md">Similar solutions, different approaches</Text>
                                <Droppable droppableId="Indirect">
                                    {(provided) => (
                                        <Stack gap="md" ref={provided.innerRef} {...provided.droppableProps} style={{ minHeight: '200px' }}>
                                            {columns.Indirect.map((competitor, index) => (
                                                <Draggable key={competitor.name} draggableId={competitor.name} index={index}>
                                                    {(provided) => (
                                                        <div
                                                            ref={provided.innerRef}
                                                            {...provided.draggableProps}
                                                            {...provided.dragHandleProps}
                                                        >
                                                            <CompetitorCard
                                                                data={competitor}
                                                                onClick={() => handleCompetitorClick(competitor)}
                                                                onDelete={() => handleDeleteCompetitor(competitor, 'Indirect')}
                                                            />
                                                        </div>
                                                    )}
                                                </Draggable>
                                            ))}
                                            {provided.placeholder}
                                        </Stack>
                                    )}
                                </Droppable>
                            </Grid.Col>

                            <Grid.Col span={{ base: 12, md: 4 }}>
                                <Title order={4} mb="xs">New/Emerging Competitors</Title>
                                <Text size="sm" c="dimmed" mb="md">Alternative solutions</Text>
                                <Droppable droppableId="Emerging">
                                    {(provided) => (
                                        <Stack gap="md" ref={provided.innerRef} {...provided.droppableProps} style={{ minHeight: '200px' }}>
                                            {columns.Emerging.map((competitor, index) => (
                                                <Draggable key={competitor.name} draggableId={competitor.name} index={index}>
                                                    {(provided) => (
                                                        <div
                                                            ref={provided.innerRef}
                                                            {...provided.draggableProps}
                                                            {...provided.dragHandleProps}
                                                        >
                                                            <CompetitorCard
                                                                data={competitor}
                                                                onClick={() => handleCompetitorClick(competitor)}
                                                                onDelete={() => handleDeleteCompetitor(competitor, 'Emerging')}
                                                            />
                                                        </div>
                                                    )}
                                                </Draggable>
                                            ))}
                                            {provided.placeholder}
                                        </Stack>
                                    )}
                                </Droppable>
                            </Grid.Col>
                        </Grid>
                    </DragDropContext>

                    <Stack gap="md" mt="xl">
                        <Button
                            leftSection={<IconPlus size={16} />}
                            onClick={() => setAddCompetitorModalOpened(true)}
                            size="md"
                            variant="light"
                        >
                            Add Competitor
                        </Button>

                        <Button
                            leftSection={<IconBulb size={16} />}
                            onClick={() => handleEnrichCompetitors(false)}
                            size="md"
                            variant="filled"
                            color="blue"
                            loading={isEnrichingCompetitors}
                            disabled={isEnrichingCompetitors}
                        >
                            {isEnrichingCompetitors ? 'Enriching Competitors...' : 'Enrich All Competitors'}
                        </Button>
                    </Stack>

                    <CompetitorDetailsModal
                        opened={selectedCompetitor !== null}
                        onClose={() => {
                            setSelectedCompetitor(null);
                            setSelectedCompetitorSolutions(null);
                        }}
                        competitor={selectedCompetitor}
                        competitorSolutions={selectedCompetitorSolutions}
                    />

                    <AddCompetitorModal
                        opened={addCompetitorModalOpened}
                        onClose={() => setAddCompetitorModalOpened(false)}
                        onAdd={handleAddCompetitor}
                    />
                </Tabs.Panel>

                <Tabs.Panel value="compare">
                    <ComparisonTable
                        companyData={{
                            name: companyData.name,
                            employees: companyData.employees,
                            marketCap: companyData.marketCap,
                            revenue: companyData.revenue,
                            foundedYear: companyData.foundedYear
                        }}
                        competitorData={MOCK_COMPETITORS.map(comp => ({
                            name: comp.name,
                            employees: comp.employees,
                            marketCap: comp.marketCap,
                            revenue: comp.revenue,
                            foundedYear: comp.foundedYear
                        }))}
                        customMetrics={customCategories.map(c => ({ key: c.id, label: c.label, description: c.description }))}
                        customMetricValues={customMetricValues}
                        loadingMetrics={loadingCategories}
                    />
                </Tabs.Panel>

                <Tabs.Panel value="compareSolutions">
                    <SolutionComparison
                        mySolutions={solutions}
                        competitors={competitorsWithSolutions}
                        companyDomain={companyData.domain}
                    />
                </Tabs.Panel>

                <Tabs.Panel value="timeline">
                    <Timeline
                        alerts={MOCK_TIMELINE_ALERTS}
                        competitors={MOCK_COMPETITORS.map(c => c.name)}
                    />
                </Tabs.Panel>

                <Tabs.Panel value="userPreferences">
                    <UserPreferences
                        customCategories={customCategories}
                        onAddCategory={handleAddCategory}
                        onDeleteCategory={handleDeleteCategory}
                    />
                </Tabs.Panel>
            </Tabs>
        </Container>
    );
}
