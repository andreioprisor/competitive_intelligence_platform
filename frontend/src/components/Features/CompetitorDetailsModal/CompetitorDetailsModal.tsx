import { Modal, Stack, Group, Text, Title, Badge, Avatar, Grid, Divider } from '@mantine/core';
import { IconMapPin, IconWorld, IconCategory } from '@tabler/icons-react';

interface CompetitorDetailsModalProps {
    opened: boolean;
    onClose: () => void;
    competitor: {
        name: string;
        logoUrl: string;
        description: string;
        strategies: string[];
        category: string;
        website: string;
        location: string;
    } | null;
    competitorSolutions?: any;
}

export function CompetitorDetailsModal({ opened, onClose, competitor, competitorSolutions }: CompetitorDetailsModalProps) {
    if (!competitor) return null;

    // Extract solutions array from the enriched data structure
    const solutions = competitorSolutions?.Solutions || [];
    const hasEnrichedData = competitorSolutions && Object.keys(competitorSolutions).length > 0;

    return (
        <Modal
            opened={opened}
            onClose={onClose}
            title="Competitor Details"
            size={hasEnrichedData ? "xl" : "lg"}
            centered
            styles={{
                body: { maxHeight: '70vh', overflowY: 'auto' }
            }}
        >
            <Stack gap="lg">
                {/* Header with logo and name */}
                <Group>
                    <Avatar
                        src={competitor.logoUrl}
                        size={64}
                        radius="md"
                    />
                    <div style={{ flex: 1 }}>
                        <Title order={3}>{competitor.name}</Title>
                        <Group gap="xs" mt="xs">
                            <Badge color="blue" variant="light">
                                {competitor.category}
                            </Badge>
                        </Group>
                    </div>
                </Group>

                <Divider />

                {/* Basic Information */}
                <div>
                    <Title order={5} mb="sm">Basic Information</Title>
                    <Stack gap="sm">
                        <Group gap="xs">
                            <IconMapPin size={16} />
                            <Text size="sm" fw={500}>Location:</Text>
                            <Text size="sm" c="dimmed">{competitor.location}</Text>
                        </Group>

                        {competitor.website && (
                            <Group gap="xs">
                                <IconWorld size={16} />
                                <Text size="sm" fw={500}>Website:</Text>
                                <Text
                                    size="sm"
                                    c="blue"
                                    component="a"
                                    href={`https://${competitor.website}`}
                                    target="_blank"
                                    style={{ textDecoration: 'none' }}
                                >
                                    {competitor.website}
                                </Text>
                            </Group>
                        )}

                        <Group gap="xs">
                            <IconCategory size={16} />
                            <Text size="sm" fw={500}>Category:</Text>
                            <Text size="sm" c="dimmed">{competitor.category} Competitor</Text>
                        </Group>
                    </Stack>
                </div>

                <Divider />

                {/* Description */}
                <div>
                    <Title order={5} mb="sm">Description</Title>
                    <Text size="sm" c="dimmed">
                        {competitor.description}
                    </Text>
                </div>

                {/* Strategies */}
                {competitor.strategies && competitor.strategies.length > 0 && (
                    <>
                        <Divider />
                        <div>
                            <Title order={5} mb="sm">Competitive Strategies</Title>
                            <Stack gap="xs">
                                {competitor.strategies.map((strategy, index) => (
                                    <Group key={index} gap="xs">
                                        <Text size="sm" c="dimmed">•</Text>
                                        <Text size="sm">{strategy}</Text>
                                    </Group>
                                ))}
                            </Stack>
                        </div>
                    </>
                )}

                {/* Enriched Solutions */}
                {hasEnrichedData && (
                    <>
                        <Divider />
                        <div>
                            <Title order={5} mb="sm">Enriched Competitor Intelligence</Title>

                            {/* Company Overview */}
                            {competitorSolutions.Competitor_Name && (
                                <Stack gap="sm" mb="md">
                                    <Group gap="xs">
                                        <Text size="sm" fw={500}>Company:</Text>
                                        <Text size="sm">{competitorSolutions.Competitor_Name}</Text>
                                    </Group>
                                    {competitorSolutions.Company_Size && (
                                        <Group gap="xs">
                                            <Text size="sm" fw={500}>Size:</Text>
                                            <Text size="sm" c="dimmed">{competitorSolutions.Company_Size}</Text>
                                        </Group>
                                    )}
                                    {competitorSolutions.Year_Founded && (
                                        <Group gap="xs">
                                            <Text size="sm" fw={500}>Founded:</Text>
                                            <Text size="sm" c="dimmed">{competitorSolutions.Year_Founded}</Text>
                                        </Group>
                                    )}
                                </Stack>
                            )}

                            {/* Solutions Comparison */}
                            {solutions.length > 0 && (
                                <>
                                    <Title order={6} mb="sm">Solutions ({solutions.length})</Title>
                                    <Stack gap="md">
                                        {solutions.map((solution: any, index: number) => (
                                            <div key={index} style={{
                                                padding: '12px',
                                                border: '1px solid var(--mantine-color-default-border)',
                                                borderRadius: '8px',
                                                backgroundColor: 'var(--mantine-color-body)'
                                            }}>
                                                <Text size="sm" fw={600} mb="xs">{solution.solution_name}</Text>

                                                {solution.most_similar_to && (
                                                    <Text size="xs" c="dimmed" mb="sm">
                                                        Similar to: {solution.most_similar_to}
                                                    </Text>
                                                )}

                                                {solution.we_are_better && solution.we_are_better.length > 0 && (
                                                    <div style={{ marginBottom: '8px' }}>
                                                        <Text size="xs" fw={500} c="green">Our Advantages:</Text>
                                                        <Stack gap={4}>
                                                            {solution.we_are_better.map((advantage: string, i: number) => (
                                                                <Text key={i} size="xs" c="dimmed">• {advantage}</Text>
                                                            ))}
                                                        </Stack>
                                                    </div>
                                                )}

                                                {solution.they_are_better && solution.they_are_better.length > 0 && (
                                                    <div style={{ marginBottom: '8px' }}>
                                                        <Text size="xs" fw={500} c="red">Their Advantages:</Text>
                                                        <Stack gap={4}>
                                                            {solution.they_are_better.map((advantage: string, i: number) => (
                                                                <Text key={i} size="xs" c="dimmed">• {advantage}</Text>
                                                            ))}
                                                        </Stack>
                                                    </div>
                                                )}

                                                {solution.conclusion && solution.conclusion.length > 0 && (
                                                    <div>
                                                        <Text size="xs" fw={500}>Conclusion:</Text>
                                                        <Stack gap={4}>
                                                            {solution.conclusion.map((point: string, i: number) => (
                                                                <Text key={i} size="xs" c="dimmed">• {point}</Text>
                                                            ))}
                                                        </Stack>
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </Stack>
                                </>
                            )}
                        </div>
                    </>
                )}
            </Stack>
        </Modal>
    );
}
