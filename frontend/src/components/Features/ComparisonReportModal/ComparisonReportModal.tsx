import { Modal, ScrollArea, Loader, Stack, Text, Button, Group, Paper, Badge, ActionIcon, Tooltip } from '@mantine/core';
import { IconDownload, IconCopy, IconMail, IconCheck, IconAlertCircle } from '@tabler/icons-react';
import { useState } from 'react';

interface ComparisonReportModalProps {
    opened: boolean;
    onClose: () => void;
    report: string | null;
    loading: boolean;
    companySolution: string;
    competitorSolution: string;
    competitorDomain: string;
}

interface ParsedComparison {
    ourSolution: string;
    theirSolution: string;
    competitor: string;
    weAreBetter: string[];
    theyAreBetter: string[];
    conclusion: string[];
}

export function ComparisonReportModal({
    opened,
    onClose,
    report,
    loading,
    companySolution,
    competitorSolution,
    competitorDomain
}: ComparisonReportModalProps) {
    const [copied, setCopied] = useState(false);

    // Parse the HTML report to extract structured data
    const parseReport = (htmlReport: string): ParsedComparison | null => {
        if (!htmlReport) return null;

        const parser = new DOMParser();
        const doc = parser.parseFromString(htmlReport, 'text/html');

        const extractListItems = (selector: string): string[] => {
            const items = doc.querySelectorAll(selector);
            return Array.from(items).map(item => item.textContent?.trim() || '');
        };

        // Extract data from the HTML structure
        const ourSolutionEl = doc.querySelector('span[style*="color: #27AE60"]');
        const theirSolutionEl = doc.querySelector('span[style*="color: #E74C3C"]');

        return {
            ourSolution: ourSolutionEl?.textContent?.trim() || companySolution,
            theirSolution: theirSolutionEl?.textContent?.trim() || competitorSolution,
            competitor: competitorDomain,
            weAreBetter: extractListItems('li[style*="#E8F8F5"]'),
            theyAreBetter: extractListItems('li[style*="#FADBD8"]'),
            conclusion: extractListItems('li[style*="#EBF5FB"]')
        };
    };

    const parsedData = report ? parseReport(report) : null;

    const handleCopy = () => {
        if (!parsedData) return;

        const text = `
COMPETITIVE BATTLE CARD
${parsedData.ourSolution} vs ${parsedData.theirSolution}

OUR ADVANTAGES:
${parsedData.weAreBetter.map((item, i) => `${i + 1}. ${item}`).join('\n')}

THEIR ADVANTAGES:
${parsedData.theyAreBetter.map((item, i) => `${i + 1}. ${item}`).join('\n')}

KEY TAKEAWAYS:
${parsedData.conclusion.map((item, i) => `${i + 1}. ${item}`).join('\n')}
        `.trim();

        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleExportPDF = () => {
        window.print();
    };

    const handleEmail = () => {
        if (!parsedData) return;

        const subject = encodeURIComponent(`Battle Card: ${parsedData.ourSolution} vs ${parsedData.theirSolution}`);
        const body = encodeURIComponent(`
OUR ADVANTAGES:
${parsedData.weAreBetter.map((item, i) => `${i + 1}. ${item}`).join('\n')}

THEIR ADVANTAGES:
${parsedData.theyAreBetter.map((item, i) => `${i + 1}. ${item}`).join('\n')}

KEY TAKEAWAYS:
${parsedData.conclusion.map((item, i) => `${i + 1}. ${item}`).join('\n')}
        `);

        window.location.href = `mailto:?subject=${subject}&body=${body}`;
    };

    return (
        <Modal
            opened={opened}
            onClose={onClose}
            title={
                <Group gap="sm">
                    <Text fw={600} size="lg">Battle Card</Text>
                    {parsedData && (
                        <Badge size="lg" variant="gradient" gradient={{ from: 'orange', to: 'red' }}>
                            Competitive Intelligence
                        </Badge>
                    )}
                </Group>
            }
            size="95%"
            centered
            styles={{
                body: { padding: 0 }
            }}
        >
            {loading ? (
                <Stack align="center" justify="center" h={400} p="xl">
                    <Loader size="lg" />
                    <Text c="dimmed">Analyzing competitive landscape...</Text>
                    <Text size="sm" c="dimmed">
                        Building battle card for {companySolution} vs {competitorDomain}'s {competitorSolution}
                    </Text>
                </Stack>
            ) : parsedData ? (
                <>
                    {/* Quick Actions Bar */}
                    <Paper p="md" bg="gray.1" style={{ borderBottom: '2px solid #dee2e6' }}>
                        <Group justify="space-between">
                            <Group gap="xs">
                                <Button
                                    leftSection={<IconDownload size={16} />}
                                    variant="light"
                                    size="sm"
                                    onClick={handleExportPDF}
                                >
                                    Export PDF
                                </Button>
                                <Button
                                    leftSection={copied ? <IconCheck size={16} /> : <IconCopy size={16} />}
                                    variant="light"
                                    size="sm"
                                    color={copied ? 'green' : 'blue'}
                                    onClick={handleCopy}
                                >
                                    {copied ? 'Copied!' : 'Copy Text'}
                                </Button>
                                <Button
                                    leftSection={<IconMail size={16} />}
                                    variant="light"
                                    size="sm"
                                    onClick={handleEmail}
                                >
                                    Email
                                </Button>
                            </Group>
                            <Badge size="lg" color="gray" variant="dot">
                                Sales Battle Sheet
                            </Badge>
                        </Group>
                    </Paper>

                    <ScrollArea h={600} p="xl">
                        <Stack gap="xl">
                            {/* Battle Header */}
                            <Paper p="xl" bg="gradient-to-r" style={{
                                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                color: 'white',
                                borderRadius: '12px'
                            }}>
                                <Stack gap="sm" align="center">
                                    <Text size="sm" opacity={0.9} fw={500}>HEAD-TO-HEAD COMPARISON</Text>
                                    <Group gap="xl" align="center">
                                        <Stack align="center" gap={4}>
                                            <Badge size="xl" color="green" variant="filled">YOUR SOLUTION</Badge>
                                            <Text size="xl" fw={700}>{parsedData.ourSolution}</Text>
                                        </Stack>
                                        <Text size="40px" fw={700} opacity={0.7}>VS</Text>
                                        <Stack align="center" gap={4}>
                                            <Badge size="xl" color="red" variant="filled">COMPETITOR</Badge>
                                            <Text size="xl" fw={700}>{parsedData.theirSolution}</Text>
                                        </Stack>
                                    </Group>
                                    <Text size="sm" opacity={0.8}>{parsedData.competitor}</Text>
                                </Stack>
                            </Paper>

                            {/* Two-Column Battle Layout */}
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
                                {/* Left Column - Our Advantages */}
                                <Paper
                                    p="xl"
                                    style={{
                                        background: 'linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%)',
                                        border: '3px solid #28a745',
                                        borderRadius: '12px',
                                        boxShadow: '0 4px 12px rgba(40, 167, 69, 0.15)'
                                    }}
                                >
                                    <Stack gap="md">
                                        <Group gap="xs">
                                            <IconCheck size={28} color="#155724" stroke={3} />
                                            <Text size="xl" fw={700} c="#155724">OUR ADVANTAGES</Text>
                                        </Group>
                                        <Badge size="lg" color="green" variant="filled">
                                            {parsedData.weAreBetter.length} Competitive Strengths
                                        </Badge>
                                        <Stack gap="sm" mt="sm">
                                            {parsedData.weAreBetter.map((item, index) => (
                                                <Paper
                                                    key={index}
                                                    p="md"
                                                    bg="white"
                                                    style={{
                                                        border: '2px solid #28a745',
                                                        borderRadius: '8px',
                                                        boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
                                                    }}
                                                >
                                                    <Group align="flex-start" gap="sm">
                                                        <Badge color="green" size="lg" circle>
                                                            {index + 1}
                                                        </Badge>
                                                        <Text size="sm" style={{ flex: 1 }} fw={500}>
                                                            {item}
                                                        </Text>
                                                    </Group>
                                                </Paper>
                                            ))}
                                        </Stack>
                                    </Stack>
                                </Paper>

                                {/* Right Column - Their Advantages */}
                                <Paper
                                    p="xl"
                                    style={{
                                        background: 'linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%)',
                                        border: '3px solid #dc3545',
                                        borderRadius: '12px',
                                        boxShadow: '0 4px 12px rgba(220, 53, 69, 0.15)'
                                    }}
                                >
                                    <Stack gap="md">
                                        <Group gap="xs">
                                            <IconAlertCircle size={28} color="#721c24" stroke={3} />
                                            <Text size="xl" fw={700} c="#721c24">THEIR ADVANTAGES</Text>
                                        </Group>
                                        <Badge size="lg" color="red" variant="filled">
                                            {parsedData.theyAreBetter.length} Areas to Watch
                                        </Badge>
                                        <Stack gap="sm" mt="sm">
                                            {parsedData.theyAreBetter.map((item, index) => (
                                                <Paper
                                                    key={index}
                                                    p="md"
                                                    bg="white"
                                                    style={{
                                                        border: '2px solid #dc3545',
                                                        borderRadius: '8px',
                                                        boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
                                                    }}
                                                >
                                                    <Group align="flex-start" gap="sm">
                                                        <Badge color="red" size="lg" circle>
                                                            {index + 1}
                                                        </Badge>
                                                        <Text size="sm" style={{ flex: 1 }} fw={500}>
                                                            {item}
                                                        </Text>
                                                    </Group>
                                                </Paper>
                                            ))}
                                        </Stack>
                                    </Stack>
                                </Paper>
                            </div>

                            {/* Strategic Insights Section */}
                            <Paper
                                p="xl"
                                style={{
                                    background: 'linear-gradient(135deg, #cfe2ff 0%, #b6d4fe 100%)',
                                    border: '3px solid #0d6efd',
                                    borderRadius: '12px',
                                    boxShadow: '0 4px 12px rgba(13, 110, 253, 0.15)'
                                }}
                            >
                                <Stack gap="md">
                                    <Group gap="xs">
                                        <Text size="24px">📊</Text>
                                        <Text size="xl" fw={700} c="#084298">STRATEGIC INSIGHTS</Text>
                                    </Group>
                                    <Badge size="lg" color="blue" variant="filled">
                                        {parsedData.conclusion.length} Key Takeaways
                                    </Badge>
                                    <Stack gap="sm" mt="sm">
                                        {parsedData.conclusion.map((item, index) => (
                                            <Paper
                                                key={index}
                                                p="md"
                                                bg="white"
                                                style={{
                                                    border: '2px solid #0d6efd',
                                                    borderRadius: '8px',
                                                    boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
                                                }}
                                            >
                                                <Group align="flex-start" gap="sm">
                                                    <Badge color="blue" size="lg" circle>
                                                        {index + 1}
                                                    </Badge>
                                                    <Text size="sm" style={{ flex: 1 }} fw={500}>
                                                        {item}
                                                    </Text>
                                                </Group>
                                            </Paper>
                                        ))}
                                    </Stack>
                                </Stack>
                            </Paper>
                        </Stack>
                    </ScrollArea>
                </>
            ) : (
                <Stack align="center" justify="center" h={400}>
                    <Text c="dimmed" ta="center">No comparison data available</Text>
                </Stack>
            )}
        </Modal>
    );
}
