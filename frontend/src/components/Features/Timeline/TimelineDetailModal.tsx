import { Modal, Stack, Text, Badge, Group, Title, Paper, List, ThemeIcon, Divider, Accordion, ScrollArea } from '@mantine/core';
import { IconAlertTriangle, IconBulb, IconTarget, IconBook, IconTool, IconSearch } from '@tabler/icons-react';
import type { TimelineItem } from '../../../services/api';

interface TimelineDetailModalProps {
    opened: boolean;
    onClose: () => void;
    item: TimelineItem | null;
}

const getConcernColor = (level: number) => {
    if (level >= 4) return 'red';
    if (level === 3) return 'orange';
    if (level === 2) return 'yellow';
    return 'green';
};

const getConcernLabel = (level: number) => {
    if (level >= 4) return 'Critical';
    if (level === 3) return 'High';
    if (level === 2) return 'Medium';
    return 'Low';
};

export function TimelineDetailModal({ opened, onClose, item }: TimelineDetailModalProps) {
    if (!item) return null;

    const concernLevel = item.value?.concern_level || 1;
    const confidence = item.value?.confidence || 0;

    return (
        <Modal
            opened={opened}
            onClose={onClose}
            size="xl"
            title={
                <Group gap="sm">
                    <Title order={3}>{item.criteria_name}</Title>
                    <Badge color={getConcernColor(concernLevel)} variant="filled" size="lg">
                        {getConcernLabel(concernLevel)} Concern
                    </Badge>
                </Group>
            }
            scrollAreaComponent={ScrollArea.Autosize}
        >
            <Stack gap="lg">
                {/* Most Important Takeaway - Headline */}
                {item.value?.most_important_takeaway && (
                    <Paper withBorder p="lg" radius="md" style={{ borderLeft: `6px solid var(--mantine-color-${getConcernColor(concernLevel)}-6)` }}>
                        <Text size="xl" fw={700} style={{ lineHeight: 1.4 }}>
                            {item.value.most_important_takeaway}
                        </Text>
                    </Paper>
                )}

                {/* Header Info */}
                <Paper withBorder p="md" radius="md">
                    <Group justify="space-between">
                        <div>
                            <Text size="sm" c="dimmed">Competitor</Text>
                            <Text fw={600} size="lg">{item.competitor_domain}</Text>
                        </div>
                        <div>
                            <Text size="sm" c="dimmed">Analyzed</Text>
                            <Text fw={500}>{new Date(item.created_at).toLocaleDateString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                year: 'numeric'
                            })}</Text>
                        </div>
                        <div>
                            <Text size="sm" c="dimmed">Confidence</Text>
                            <Badge color={confidence >= 0.8 ? 'green' : confidence >= 0.6 ? 'yellow' : 'orange'} variant="outline" size="lg">
                                {(confidence * 100).toFixed(0)}%
                            </Badge>
                        </div>
                    </Group>
                </Paper>

                {/* Concern Rationale */}
                {item.value?.concern_rationale && (
                    <Paper withBorder p="md" radius="md" style={{ borderLeft: `4px solid var(--mantine-color-${getConcernColor(concernLevel)}-6)` }}>
                        <Group gap="xs" mb="xs">
                            <ThemeIcon color={getConcernColor(concernLevel)} variant="outline" size="sm">
                                <IconAlertTriangle size={16} />
                            </ThemeIcon>
                            <Text fw={600} size="sm">Why This Matters</Text>
                        </Group>
                        <Text size="sm">{item.value.concern_rationale}</Text>
                    </Paper>
                )}

                {/* Summary */}
                {item.value?.dp_value && (
                    <div>
                        <Text fw={600} size="sm" mb="xs">Executive Summary</Text>
                        <Paper withBorder p="md" radius="md">
                            <Text size="sm">{item.value.dp_value}</Text>
                        </Paper>
                    </div>
                )}

                {/* Full Answer */}
                {item.value?.answer && (
                    <Accordion variant="contained">
                        <Accordion.Item value="full-answer">
                            <Accordion.Control>
                                <Group gap="xs">
                                    <IconBook size={18} />
                                    <Text fw={500}>Detailed Analysis</Text>
                                </Group>
                            </Accordion.Control>
                            <Accordion.Panel>
                                <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>{item.value.answer}</Text>
                            </Accordion.Panel>
                        </Accordion.Item>
                    </Accordion>
                )}

                {/* Key Insights */}
                {item.value?.insights && item.value.insights.length > 0 && (
                    <div>
                        <Group gap="xs" mb="xs">
                            <ThemeIcon color="blue" variant="outline" size="sm">
                                <IconBulb size={16} />
                            </ThemeIcon>
                            <Text fw={600} size="sm">Key Insights</Text>
                        </Group>
                        <List spacing="xs" size="sm" withPadding>
                            {item.value.insights.map((insight: string, idx: number) => (
                                <List.Item key={idx}>
                                    <Text size="sm">{insight}</Text>
                                </List.Item>
                            ))}
                        </List>
                    </div>
                )}

                <Divider />

                {/* Suggested Actions */}
                {item.value?.suggested_actions && item.value.suggested_actions.length > 0 && (
                    <Paper withBorder p="md" radius="md" style={{ borderLeft: `4px solid var(--mantine-color-green-6)` }}>
                        <Group gap="xs" mb="md">
                            <ThemeIcon color="green" variant="outline" size="md">
                                <IconTarget size={18} />
                            </ThemeIcon>
                            <Text fw={700} size="md">Recommended Actions</Text>
                        </Group>
                        <List spacing="sm" size="sm" withPadding>
                            {item.value.suggested_actions.map((action: string, idx: number) => (
                                <List.Item key={idx}>
                                    <Text size="sm" fw={500}>{action}</Text>
                                </List.Item>
                            ))}
                        </List>
                    </Paper>
                )}

                {/* Evidence Summary */}
                {item.value?.evidence_summary && (
                    <Accordion variant="contained">
                        <Accordion.Item value="evidence">
                            <Accordion.Control>
                                <Group gap="xs">
                                    <IconBook size={18} />
                                    <Text fw={500}>Evidence Summary</Text>
                                </Group>
                            </Accordion.Control>
                            <Accordion.Panel>
                                <Stack gap="md">
                                    {item.value.evidence_summary.key_findings && item.value.evidence_summary.key_findings.length > 0 && (
                                        <div>
                                            <Text fw={600} size="sm" mb="xs">Key Findings</Text>
                                            <List spacing="xs" size="sm" withPadding>
                                                {item.value.evidence_summary.key_findings.map((finding: string, idx: number) => (
                                                    <List.Item key={idx}>
                                                        <Text size="sm">{finding}</Text>
                                                    </List.Item>
                                                ))}
                                            </List>
                                        </div>
                                    )}
                                    {item.value.evidence_summary.limitations && item.value.evidence_summary.limitations.length > 0 && (
                                        <div>
                                            <Text fw={600} size="sm" mb="xs">Limitations</Text>
                                            <List spacing="xs" size="sm" withPadding>
                                                {item.value.evidence_summary.limitations.map((limitation: string, idx: number) => (
                                                    <List.Item key={idx}>
                                                        <Text size="sm" c="dimmed">{limitation}</Text>
                                                    </List.Item>
                                                ))}
                                            </List>
                                        </div>
                                    )}
                                </Stack>
                            </Accordion.Panel>
                        </Accordion.Item>
                    </Accordion>
                )}

                {/* Metadata */}
                <Paper withBorder p="sm" radius="md">
                    <Group gap="lg">
                        {item.value?.tools_used && item.value.tools_used.length > 0 && (
                            <div>
                                <Group gap="xs" mb="xs">
                                    <IconTool size={14} />
                                    <Text size="xs" c="dimmed" fw={600}>Tools Used</Text>
                                </Group>
                                <Group gap="xs">
                                    {item.value.tools_used.map((tool: string, idx: number) => (
                                        <Badge key={idx} variant="outline" size="sm">{tool}</Badge>
                                    ))}
                                </Group>
                            </div>
                        )}
                        {item.value?.queries_made && item.value.queries_made.length > 0 && (
                            <div>
                                <Group gap="xs" mb="xs">
                                    <IconSearch size={14} />
                                    <Text size="xs" c="dimmed" fw={600}>Queries Made</Text>
                                </Group>
                                <Text size="xs" c="dimmed">{item.value.queries_made.length} searches</Text>
                            </div>
                        )}
                    </Group>
                </Paper>
            </Stack>
        </Modal>
    );
}
