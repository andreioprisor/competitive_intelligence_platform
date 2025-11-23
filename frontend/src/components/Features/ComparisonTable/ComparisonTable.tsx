import { Table, Paper, Text, Skeleton, Stack, Group, Button } from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import { IconChartBar } from '@tabler/icons-react';
import { useState } from 'react';
import { GraphModal } from '../GraphModal/GraphModal';

interface ComparisonData {
    name: string;
    employees?: string;
    marketCap?: string;
    revenue?: string;
    foundedYear?: number;
}

interface ComparisonTableProps {
    companyData: ComparisonData;
    competitorData: ComparisonData[];
    customMetrics?: Array<{ key: string; label: string; description: string }>;
    customMetricValues?: Record<string, Record<string, string>>;
    loadingMetrics?: Set<string>;
}

export function ComparisonTable({
    companyData,
    competitorData,
    customMetrics = [],
    customMetricValues = {},
    loadingMetrics = new Set()
}: ComparisonTableProps) {
    const allCompanies = [companyData, ...competitorData];

    // Initialize date range to last 60 days
    const today = new Date();
    const sixtyDaysAgo = new Date();
    sixtyDaysAgo.setDate(today.getDate() - 60);

    const [dateRange, setDateRange] = useState<[Date | null, Date | null]>([sixtyDaysAgo, today]);
    const [graphModalOpened, setGraphModalOpened] = useState(false);

    const handleQuickSelect = (days: number | 'ytd' | 'year') => {
        const end = new Date();
        let start = new Date();

        if (days === 'ytd') {
            start = new Date(end.getFullYear(), 0, 1); // January 1st of current year
        } else if (days === 'year') {
            start.setFullYear(end.getFullYear() - 1);
        } else {
            start.setDate(end.getDate() - days);
        }

        setDateRange([start, end]);
    };

    const defaultMetrics = [
        { key: 'employees', label: 'Employees' },
        { key: 'marketCap', label: 'Market Cap' },
        { key: 'revenue', label: 'Revenue' },
        { key: 'foundedYear', label: 'Founded' }
    ];

    const allMetrics = [...defaultMetrics, ...customMetrics];

    // Prepare data for graph
    const graphData: Record<string, Record<string, any>> = {};
    allCompanies.forEach(company => {
        graphData[company.name] = {};
        allMetrics.forEach(metric => {
            if (metric.key.startsWith('custom-')) {
                graphData[company.name][metric.key] = customMetricValues[metric.key]?.[company.name] || 'N/A';
            } else {
                graphData[company.name][metric.key] = (company as any)[metric.key] || 'N/A';
            }
        });
    });

    return (
        <Stack gap="md">
            <Paper withBorder radius="md" p="md" bg="var(--mantine-color-body)">
                <Stack gap="md">
                    <Group justify="space-between">
                        <Text fw={600} size="sm">Date Range Filter</Text>
                        <Button
                            leftSection={<IconChartBar size={16} />}
                            onClick={() => setGraphModalOpened(true)}
                            variant="filled"
                        >
                            Generate Graph
                        </Button>
                    </Group>
                    <Group>
                        <DatePickerInput
                            type="range"
                            label="Select Date Range"
                            placeholder="Pick dates range"
                            value={dateRange}
                            onChange={(value) => setDateRange(value as [Date | null, Date | null])}
                            clearable
                        />
                        <Group gap="xs" style={{ marginTop: '20px' }}>
                            <Button
                                size="xs"
                                variant="light"
                                onClick={() => handleQuickSelect(7)}
                            >
                                Last 7 days
                            </Button>
                            <Button
                                size="xs"
                                variant="light"
                                onClick={() => handleQuickSelect(30)}
                            >
                                Last 30 days
                            </Button>
                            <Button
                                size="xs"
                                variant="light"
                                onClick={() => handleQuickSelect('year')}
                            >
                                Last year
                            </Button>
                            <Button
                                size="xs"
                                variant="light"
                                onClick={() => handleQuickSelect('ytd')}
                            >
                                Year to date
                            </Button>
                        </Group>
                    </Group>
                </Stack>
            </Paper>

            <Paper withBorder radius="md" p="md" bg="var(--mantine-color-body)">
                <Table striped highlightOnHover withTableBorder withColumnBorders>
                    <Table.Thead>
                        <Table.Tr>
                            <Table.Th>Metric</Table.Th>
                            {allCompanies.map((company, index) => (
                                <Table.Th key={index}>
                                    <Text fw={index === 0 ? 700 : 500}>
                                        {company.name}
                                        {index === 0 && <Text span c="orange" ml={5}>(You)</Text>}
                                    </Text>
                                </Table.Th>
                            ))}
                        </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                        {allMetrics.map((metric) => (
                            <Table.Tr key={metric.key}>
                                <Table.Td>
                                    <Text fw={600}>{metric.label}</Text>
                                    {'description' in metric && (
                                        <Text size="xs" c="dimmed" lineClamp={1}>
                                            {(metric as any).description}
                                        </Text>
                                    )}
                                </Table.Td>
                                {allCompanies.map((company, index) => {
                                    const isLoading = loadingMetrics.has(metric.key);
                                    let value = 'N/A';

                                    if (metric.key.startsWith('custom-')) {
                                        value = customMetricValues[metric.key]?.[company.name] || 'N/A';
                                    } else {
                                        value = (company as any)[metric.key] || 'N/A';
                                    }

                                    return (
                                        <Table.Td
                                            key={index}
                                            bg={index === 0 ? 'var(--mantine-color-orange-light)' : undefined}
                                        >
                                            {isLoading ? (
                                                <Skeleton height={20} radius="sm" />
                                            ) : (
                                                value
                                            )}
                                        </Table.Td>
                                    );
                                })}
                            </Table.Tr>
                        ))}
                    </Table.Tbody>
                </Table>
            </Paper>

            <GraphModal
                opened={graphModalOpened}
                onClose={() => setGraphModalOpened(false)}
                companies={allCompanies.map(c => c.name)}
                metrics={allMetrics}
                data={graphData}
            />
        </Stack>
    );
}
