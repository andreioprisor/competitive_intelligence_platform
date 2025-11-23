import { Card, Text, Badge, Group, Stack, Title, Collapse } from '@mantine/core';
import { useState } from 'react';

interface SolutionCardProps {
    data: {
        name: string;
        description: string;
        industries: string[];
        features: string[];
        benefits: string[];
        useCases: string[];
    };
}

export function SolutionCard({ data }: SolutionCardProps) {
    const [expanded, setExpanded] = useState(false);

    return (
        <Card
            withBorder
            padding="lg"
            radius="md"
            h="100%"
            bg="var(--mantine-color-body)"
            style={{ cursor: 'pointer' }}
            onClick={() => setExpanded(!expanded)}
        >
            <Stack gap="md">
                <Title order={4}>{data.name}</Title>

                <Text size="sm" c="dimmed" lineClamp={expanded ? undefined : 2}>
                    {data.description}
                </Text>

                <div>
                    <Text size="sm" fw={500} mb={5}>Targeted Industries:</Text>
                    <Group gap="xs">
                        {data.industries.slice(0, 3).map((industry, index) => (
                            <Badge key={index} variant="light" color="blue">
                                {industry}
                            </Badge>
                        ))}
                        {data.industries.length > 3 && (
                            <Badge variant="light" color="gray">
                                +{data.industries.length - 3} more
                            </Badge>
                        )}
                    </Group>
                </div>

                <Collapse in={expanded}>
                    <Stack gap="md">
                        {data.features.length > 0 && (
                            <div>
                                <Text size="sm" fw={500} mb={5}>Key Features:</Text>
                                <Stack gap={4}>
                                    {data.features.map((feature, index) => (
                                        <Text key={index} size="xs" c="dimmed">
                                            • {feature}
                                        </Text>
                                    ))}
                                </Stack>
                            </div>
                        )}

                        {data.benefits.length > 0 && (
                            <div>
                                <Text size="sm" fw={500} mb={5}>Benefits:</Text>
                                <Stack gap={4}>
                                    {data.benefits.map((benefit, index) => (
                                        <Text key={index} size="xs" c="dimmed">
                                            • {benefit}
                                        </Text>
                                    ))}
                                </Stack>
                            </div>
                        )}

                        {data.useCases.length > 0 && (
                            <div>
                                <Text size="sm" fw={500} mb={5}>Use Cases:</Text>
                                <Stack gap={4}>
                                    {data.useCases.map((useCase, index) => (
                                        <Text key={index} size="xs" c="dimmed">
                                            • {useCase}
                                        </Text>
                                    ))}
                                </Stack>
                            </div>
                        )}
                    </Stack>
                </Collapse>

                <Text size="xs" c="dimmed" ta="center">
                    {expanded ? 'Click to collapse' : 'Click to expand'}
                </Text>
            </Stack>
        </Card>
    );
}
