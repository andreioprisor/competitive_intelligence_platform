import { Stack, Title, MultiSelect, Card, Text, Badge, Group, Timeline as MantineTimeline } from '@mantine/core';
import { IconClock, IconBell } from '@tabler/icons-react';
import { useState, useMemo } from 'react';

interface TimelineAlert {
    id: number;
    competitor: string;
    channel: string;
    title: string;
    description: string;
    date: string;
    source: string;
}

interface TimelineProps {
    alerts: TimelineAlert[];
    competitors: string[];
}

const CHANNEL_COLORS: { [key: string]: string } = {
    'Website Monitoring': 'blue',
    'Pricing Intelligence': 'green',
    'Google Search Ads': 'orange',
    'News Search': 'red',
    'Reddit/X Search': 'grape',
    'Jobs Posting': 'cyan',
    'Social Media': 'pink'
};

export function Timeline({ alerts, competitors }: TimelineProps) {
    const [selectedCompetitors, setSelectedCompetitors] = useState<string[]>([]);
    const [selectedChannels, setSelectedChannels] = useState<string[]>([]);

    const channels = useMemo(() => {
        return Array.from(new Set(alerts.map(a => a.channel)));
    }, [alerts]);

    const filteredAlerts = useMemo(() => {
        return alerts.filter(alert => {
            const competitorMatch = selectedCompetitors.length === 0 || selectedCompetitors.includes(alert.competitor);
            const channelMatch = selectedChannels.length === 0 || selectedChannels.includes(alert.channel);
            return competitorMatch && channelMatch;
        }).sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
    }, [alerts, selectedCompetitors, selectedChannels]);

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

        if (diffDays === 0) return 'Today';
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return `${diffDays} days ago`;
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    };

    return (
        <Stack gap="xl">
            <Group grow>
                <MultiSelect
                    label="Filter by Competitor"
                    placeholder="Select competitors"
                    data={competitors}
                    value={selectedCompetitors}
                    onChange={setSelectedCompetitors}
                    searchable
                    clearable
                />
                <MultiSelect
                    label="Filter by Channel"
                    placeholder="Select channels"
                    data={channels}
                    value={selectedChannels}
                    onChange={setSelectedChannels}
                    searchable
                    clearable
                />
            </Group>

            {filteredAlerts.length === 0 ? (
                <Card withBorder p="xl" radius="md">
                    <Text c="dimmed" ta="center">No alerts match your filters</Text>
                </Card>
            ) : (
                <MantineTimeline active={filteredAlerts.length} bulletSize={24} lineWidth={2}>
                    {filteredAlerts.map((alert) => (
                        <MantineTimeline.Item
                            key={alert.id}
                            bullet={<IconBell size={12} />}
                            title={
                                <Card withBorder padding="md" radius="md" bg="var(--mantine-color-body)">
                                    <Stack gap="sm">
                                        <Group justify="space-between">
                                            <Group gap="xs">
                                                <Badge color={CHANNEL_COLORS[alert.channel] || 'gray'} variant="light">
                                                    {alert.channel}
                                                </Badge>
                                                <Badge variant="outline">{alert.competitor}</Badge>
                                                <Badge variant="light" color="gray" size="sm">Source: {alert.source}</Badge>
                                            </Group>
                                            <Group gap="xs">
                                                <IconClock size={14} />
                                                <Text size="xs" c="dimmed">{formatDate(alert.date)}</Text>
                                            </Group>
                                        </Group>
                                        <Title order={5}>{alert.title}</Title>
                                        {/* <Text size="sm" c="dimmed">{alert.description}</Text> */}
                                    </Stack>
                                </Card>
                            }
                        />
                    ))}
                </MantineTimeline>
            )}
        </Stack>
    );
}
