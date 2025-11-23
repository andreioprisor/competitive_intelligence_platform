import { Stack, Title, MultiSelect, Card, Text, Badge, Group, Timeline as MantineTimeline, Avatar, Loader, Center } from '@mantine/core';
import { IconClock, IconBell } from '@tabler/icons-react';
import { useState, useMemo, useEffect } from 'react';
import { api } from '../../../services/api';
import type { TimelineItem } from '../../../services/api';
import { TimelineDetailModal } from './TimelineDetailModal';

interface TimelineProps {
    domain?: string;
    isActive?: boolean;
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

const CONCERN_LEVEL_COLORS: { [key: number]: string } = {
    5: 'red',
    4: 'orange',
    3: 'yellow',
    2: 'blue',
    1: 'gray'
};

export function Timeline({ domain, isActive }: TimelineProps) {
    const [timelineData, setTimelineData] = useState<TimelineItem[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedCompetitors, setSelectedCompetitors] = useState<string[]>([]);
    const [selectedCriteria, setSelectedCriteria] = useState<string[]>([]);
    const [selectedConcernLevels, setSelectedConcernLevels] = useState<string[]>([]);
    const [selectedItem, setSelectedItem] = useState<TimelineItem | null>(null);
    const [modalOpened, setModalOpened] = useState(false);

    const competitors = useMemo(() => {
        return Array.from(new Set(timelineData.map(item => item.competitor_domain)));
    }, [timelineData]);

    const criteria = useMemo(() => {
        return Array.from(new Set(timelineData.map(item => item.criteria_name)));
    }, [timelineData]);

    const concernLevelOptions = ['5 - Critical', '4 - High', '3 - Medium', '2 - Low', '1 - Minimal'];

    useEffect(() => {
        // Only fetch when tab becomes active
        if (!isActive) {
            return;
        }

        const fetchTimeline = async () => {
            if (!domain) {
                console.warn('No domain provided to Timeline component');
                setLoading(false);
                return;
            }

            try {
                setLoading(true);
                const filters: any = {
                    company_domain: domain
                };

                if (selectedCompetitors.length > 0) {
                    filters.competitor_domains = selectedCompetitors;
                }
                if (selectedCriteria.length > 0) {
                    filters.criteria_names = selectedCriteria;
                }
                if (selectedConcernLevels.length > 0) {
                    filters.concern_levels = selectedConcernLevels.map(opt => parseInt(opt.split(' ')[0]));
                }

                const response = await api.getTimeline(filters);
                setTimelineData(response.items);
            } catch (error) {
                console.error('Failed to fetch timeline:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchTimeline();
    }, [isActive, domain, selectedCompetitors, selectedCriteria, selectedConcernLevels]);

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

    const getCompetitorLogoUrl = (domain: string) => {
        return `https://logo.clearbit.com/${domain}`;
    };

    if (loading) {
        return (
            <Center p="xl">
                <Loader size="lg" />
            </Center>
        );
    }

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
                    label="Filter by Criteria"
                    placeholder="Select criteria"
                    data={criteria}
                    value={selectedCriteria}
                    onChange={setSelectedCriteria}
                    searchable
                    clearable
                />
                <MultiSelect
                    label="Filter by Concern Level"
                    placeholder="Select concern levels"
                    data={concernLevelOptions}
                    value={selectedConcernLevels}
                    onChange={setSelectedConcernLevels}
                    clearable
                />
            </Group>

            {timelineData.length === 0 ? (
                <Card withBorder p="xl" radius="md">
                    <Text c="dimmed" ta="center">No timeline items found</Text>
                </Card>
            ) : (
                <MantineTimeline active={timelineData.length} bulletSize={24} lineWidth={2}>
                    {timelineData.map((item) => {
                        const concernLevel = item.value?.concern_level || 1;
                        const answer = item.value?.answer || 'No details available';

                        return (
                            <MantineTimeline.Item
                                key={item.id}
                                bullet={<IconBell size={12} />}
                                title={
                                    <Card
                                        withBorder
                                        padding="md"
                                        radius="md"
                                        bg="var(--mantine-color-body)"
                                        style={{ cursor: 'pointer' }}
                                        onClick={() => {
                                            setSelectedItem(item);
                                            setModalOpened(true);
                                        }}
                                    >
                                        <Group gap="md" align="flex-start" wrap="nowrap">
                                            <Avatar
                                                src={getCompetitorLogoUrl(item.competitor_domain)}
                                                size={48}
                                                radius="md"
                                            />
                                            <Stack gap="sm" style={{ flex: 1 }}>
                                                <Group justify="space-between">
                                                    <Group gap="xs">
                                                        <Badge color={CONCERN_LEVEL_COLORS[concernLevel]} variant="light">
                                                            Level {concernLevel}
                                                        </Badge>
                                                        <Badge variant="outline">{item.competitor_domain}</Badge>
                                                    </Group>
                                                    <Group gap="xs">
                                                        <IconClock size={14} />
                                                        <Text size="xs" c="dimmed">{formatDate(item.created_at)}</Text>
                                                    </Group>
                                                </Group>
                                                <Title order={5} lineClamp={2}>
                                                    {item.value?.most_important_takeaway || item.criteria_name}
                                                </Title>
                                                <Text size="xs" c="dimmed">
                                                    {item.criteria_name}
                                                </Text>
                                            </Stack>
                                        </Group>
                                    </Card>
                                }
                            />
                        );
                    })}
                </MantineTimeline>
            )}

            <TimelineDetailModal
                opened={modalOpened}
                onClose={() => {
                    setModalOpened(false);
                    setSelectedItem(null);
                }}
                item={selectedItem}
            />
        </Stack>
    );
}
