import { Card, Text, Badge, Group, Stack, Title } from '@mantine/core';

interface SolutionCardProps {
    data: {
        name: string;
        industries: string[];
        partners: string[];
    };
}

export function SolutionCard({ data }: SolutionCardProps) {
    return (
        <Card withBorder padding="lg" radius="md" h="100%" bg="var(--mantine-color-body)">
            <Stack gap="md">
                <Title order={4}>{data.name}</Title>

                <div>
                    <Text size="sm" fw={500} mb={5}>Targeted Industries:</Text>
                    <Group gap="xs">
                        {data.industries.map((industry, index) => (
                            <Badge key={index} variant="light" color="blue">
                                {industry}
                            </Badge>
                        ))}
                    </Group>
                </div>

                <div>
                    <Text size="sm" fw={500} mb={5}>Notable Partners:</Text>
                    <Group gap="xs">
                        {data.partners.map((partner, index) => (
                            <Badge key={index} variant="outline" color="gray">
                                {partner}
                            </Badge>
                        ))}
                    </Group>
                </div>
            </Stack>
        </Card>
    );
}
