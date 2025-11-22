import { Text, Title, Grid, Paper, Group, ThemeIcon, Stack } from '@mantine/core';
import { IconTrendingUp, IconMap } from '@tabler/icons-react';

interface CompanyAnalyticsProps {
    geography: string;
    industryTrends: string[];
}

export function CompanyAnalytics({ geography, industryTrends }: CompanyAnalyticsProps) {
    return (
        <Paper p="md" radius="md" withBorder mt="lg">
            <Title order={4} mb="md">Analytics & Reach</Title>
            <Grid>
                <Grid.Col span={12}>
                    <Group>
                        <ThemeIcon color="teal" variant="light">
                            <IconMap size={18} />
                        </ThemeIcon>
                        <div>
                            <Text size="xs" c="dimmed">Geography</Text>
                            <Text size="sm" fw={500}>{geography}</Text>
                        </div>
                    </Group>
                </Grid.Col>
                <Grid.Col span={12}>
                    <Stack gap="xs">
                        <Group>
                            <ThemeIcon color="blue" variant="light">
                                <IconTrendingUp size={18} />
                            </ThemeIcon>
                            <Text size="xs" c="dimmed">Industry Trends</Text>
                        </Group>
                        <div style={{ paddingLeft: '36px' }}>
                            {industryTrends.map((trend, index) => (
                                <Text key={index} size="sm" fw={500} style={{ lineHeight: 1.4, marginBottom: '4px' }}>
                                    • {trend}
                                </Text>
                            ))}
                        </div>
                    </Stack>
                </Grid.Col>
            </Grid>
        </Paper>
    );
}
