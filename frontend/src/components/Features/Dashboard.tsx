import { Tabs, Grid, Container, Title, Text, Stack, Button } from '@mantine/core';
import { IconBuildingSkyscraper, IconUsers, IconBulb, IconPlus, IconChartBar, IconGitCompare, IconTimeline, IconSettings } from '@tabler/icons-react';
import { MOCK_COMPETITORS, MOCK_SOLUTIONS, MOCK_TIMELINE_ALERTS } from '../../data/mockData';
import { CompanyCard } from './CompanyCard/CompanyCard';
import { CompetitorCard } from './CompetitorCard/CompetitorCard';
import { SolutionCard } from './SolutionCard/SolutionCard';
import { ComparisonTable } from './ComparisonTable/ComparisonTable';
import { SolutionComparison } from './SolutionComparison/SolutionComparison';
import { Timeline } from './Timeline/Timeline';
import { UserPreferences } from './UserPreferences/UserPreferences';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';
import type { DropResult } from '@hello-pangea/dnd';
import { useState } from 'react';

import type { CompanyData } from '../../utils/mapper';

interface DashboardProps {
    companyData: CompanyData;
}

export function Dashboard({ companyData }: DashboardProps) {
    const [columns, setColumns] = useState<{ [key: string]: typeof MOCK_COMPETITORS }>({
        Direct: MOCK_COMPETITORS.filter(c => c.category === 'Direct'),
        Indirect: MOCK_COMPETITORS.filter(c => c.category === 'Indirect'),
        Emerging: MOCK_COMPETITORS.filter(c => c.category === 'Emerging'),
    });

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

    const handleAddCategory = (newCategory: { label: string; description: string }) => {
        const id = `custom-${Date.now()}`;
        const categoryToAdd = { ...newCategory, id, isSystem: false };

        setCustomCategories(prev => [...prev, categoryToAdd]);
        setLoadingCategories(prev => new Set(prev).add(id));

        // Simulate NLP data fetching
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
    };

    const handleDeleteCategory = (id: string) => {
        setCustomCategories(prev => prev.filter(c => c.id !== id));
        setCustomMetricValues(prev => {
            const next = { ...prev };
            delete next[id];
            return next;
        });
    };

    return (
        <Container size="xl" py="xl">
            <Tabs defaultValue="company">
                <Tabs.List mb="lg">
                    <Tabs.Tab value="company" leftSection={<IconBuildingSkyscraper size={16} />}>
                        Company Info
                    </Tabs.Tab>
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
                </Tabs.List>

                <Tabs.Panel value="company">
                    <Grid>
                        <Grid.Col span={{ base: 12, md: 8 }}>
                            <CompanyCard data={companyData} />
                        </Grid.Col>
                    </Grid>
                </Tabs.Panel>

                <Tabs.Panel value="solutions">
                    <Grid>
                        {MOCK_SOLUTIONS.map((solution, index) => (
                            <Grid.Col key={index} span={{ base: 12, md: 4 }}>
                                <SolutionCard data={solution} />
                            </Grid.Col>
                        ))}
                        <Grid.Col span={{ base: 12, md: 4 }}>
                            <Button
                                variant="outline"
                                h="100%"
                                w="100%"
                                style={{ borderStyle: 'dashed' }}
                                leftSection={<IconPlus size={20} />}
                            >
                                Add Solution
                            </Button>
                        </Grid.Col>
                    </Grid>
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
                                                            <CompetitorCard data={competitor} />
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
                                                            <CompetitorCard data={competitor} />
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
                                                            <CompetitorCard data={competitor} />
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
                        mySolutions={MOCK_SOLUTIONS}
                        competitors={MOCK_COMPETITORS}
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
