import { Table, Paper, Text, Skeleton } from '@mantine/core';

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

    const defaultMetrics = [
        { key: 'employees', label: 'Employees' },
        { key: 'marketCap', label: 'Market Cap' },
        { key: 'revenue', label: 'Revenue' },
        { key: 'foundedYear', label: 'Founded' }
    ];

    const allMetrics = [...defaultMetrics, ...customMetrics];

    return (
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
    );
}
