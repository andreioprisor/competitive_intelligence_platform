import { Modal, Stack, Checkbox, Button, Group, Text, Title, Grid, ScrollArea, Badge, Divider } from '@mantine/core';
import { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface GraphModalProps {
    opened: boolean;
    onClose: () => void;
    companies: string[];
    metrics: Array<{ key: string; label: string }>;
    data: Record<string, Record<string, any>>;
}

export function GraphModal({ opened, onClose, companies, metrics, data }: GraphModalProps) {
    const [selectedCompanies, setSelectedCompanies] = useState<string[]>([companies[0] || '']);
    const [selectedMetrics, setSelectedMetrics] = useState<string[]>([metrics[0]?.key || '']);
    const [showGraph, setShowGraph] = useState(false);

    const handleCompanyToggle = (company: string) => {
        setSelectedCompanies(prev =>
            prev.includes(company)
                ? prev.filter(c => c !== company)
                : [...prev, company]
        );
    };

    const handleMetricToggle = (metricKey: string) => {
        setSelectedMetrics(prev =>
            prev.includes(metricKey)
                ? prev.filter(m => m !== metricKey)
                : [...prev, metricKey]
        );
    };

    const handleGenerateGraph = () => {
        setShowGraph(true);
    };

    const handleBack = () => {
        setShowGraph(false);
    };

    const handleReset = () => {
        setShowGraph(false);
        setSelectedCompanies([companies[0] || '']);
        setSelectedMetrics([metrics[0]?.key || '']);
        onClose();
    };

    // Helper function to check if a value is numeric
    const isNumeric = (value: any): boolean => {
        if (typeof value === 'number') return true;
        if (typeof value === 'string') {
            const numValue = parseFloat(value.replace(/[^0-9.-]/g, ''));
            return !isNaN(numValue) && numValue !== 0;
        }
        return false;
    };

    // Helper function to check if a metric is numeric across all selected companies
    const isMetricNumeric = (metricKey: string): boolean => {
        return selectedCompanies.every(company => {
            const value = data[company]?.[metricKey];
            return isNumeric(value) || value === 'N/A';
        });
    };

    // Separate metrics into numeric and categorical
    const numericMetrics = selectedMetrics.filter(metricKey => isMetricNumeric(metricKey));
    const categoricalMetrics = selectedMetrics.filter(metricKey => !isMetricNumeric(metricKey));

    const hasNumeric = numericMetrics.length > 0;
    const hasCategorical = categoricalMetrics.length > 0;

    const COLORS = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7', '#dfe6e9', '#74b9ff'];

    // Prepare chart data for numeric metrics
    const numericChartData = numericMetrics.map(metricKey => {
        const metric = metrics.find(m => m.key === metricKey);
        const dataPoint: any = { metric: metric?.label || metricKey };

        selectedCompanies.forEach(company => {
            const value = data[company]?.[metricKey];
            // Convert string values to numbers if possible
            if (typeof value === 'string') {
                const numValue = parseFloat(value.replace(/[^0-9.-]/g, ''));
                dataPoint[company] = isNaN(numValue) ? 0 : numValue;
            } else if (typeof value === 'number') {
                dataPoint[company] = value;
            } else {
                dataPoint[company] = 0;
            }
        });

        return dataPoint;
    });

    // Prepare chart data for categorical metrics
    const categoricalChartData = selectedCompanies.map(company => {
        const dataPoint: any = { company };

        categoricalMetrics.forEach(metricKey => {
            const metric = metrics.find(m => m.key === metricKey);
            const value = data[company]?.[metricKey];
            dataPoint[metric?.label || metricKey] = value || 'N/A';
        });

        return dataPoint;
    });

    return (
        <Modal
            opened={opened}
            onClose={handleReset}
            title={showGraph ? "Comparison Graph" : "Select Data for Graph"}
            size={showGraph ? "xl" : "lg"}
            centered
        >
            {!showGraph ? (
                <Stack gap="md">
                    <div>
                        <Title order={5} mb="xs">Select Companies</Title>
                        <Grid>
                            {companies.map((company, index) => (
                                <Grid.Col key={company} span={6}>
                                    <Checkbox
                                        label={company}
                                        checked={selectedCompanies.includes(company)}
                                        onChange={() => handleCompanyToggle(company)}
                                        color={COLORS[index % COLORS.length]}
                                    />
                                </Grid.Col>
                            ))}
                        </Grid>
                    </div>

                    <div>
                        <Title order={5} mb="xs">Select Metrics</Title>
                        <ScrollArea h={200}>
                            <Stack gap="xs">
                                {metrics.map(metric => (
                                    <Checkbox
                                        key={metric.key}
                                        label={metric.label}
                                        checked={selectedMetrics.includes(metric.key)}
                                        onChange={() => handleMetricToggle(metric.key)}
                                    />
                                ))}
                            </Stack>
                        </ScrollArea>
                    </div>

                    <Group justify="flex-end" mt="md">
                        <Button variant="subtle" onClick={handleReset}>
                            Cancel
                        </Button>
                        <Button
                            onClick={handleGenerateGraph}
                            disabled={selectedCompanies.length === 0 || selectedMetrics.length === 0}
                        >
                            Generate Graph
                        </Button>
                    </Group>
                </Stack>
            ) : (
                <Stack gap="md">
                    <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                            Comparing {selectedMetrics.length} metric(s) across {selectedCompanies.length} company/companies
                        </Text>
                        <Group gap="xs">
                            {hasNumeric && (
                                <Badge color="green" variant="light">
                                    {numericMetrics.length} Numeric
                                </Badge>
                            )}
                            {hasCategorical && (
                                <Badge color="blue" variant="light">
                                    {categoricalMetrics.length} Categorical
                                </Badge>
                            )}
                        </Group>
                    </Group>

                    {hasNumeric && (
                        <div>
                            <Title order={5} mb="md">Numeric Metrics</Title>
                            <ResponsiveContainer width="100%" height={300}>
                                <BarChart data={numericChartData}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="metric" />
                                    <YAxis />
                                    <Tooltip />
                                    <Legend />
                                    {selectedCompanies.map((company, index) => (
                                        <Bar
                                            key={company}
                                            dataKey={company}
                                            fill={COLORS[index % COLORS.length]}
                                        />
                                    ))}
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    )}

                    {hasNumeric && hasCategorical && <Divider />}

                    {hasCategorical && (
                        <div>
                            <Title order={5} mb="md">Categorical Metrics</Title>
                            <Stack gap="md">
                                {categoricalChartData.map((companyData, index) => (
                                    <div key={companyData.company}>
                                        <Group gap="xs" mb="xs">
                                            <div
                                                style={{
                                                    width: 12,
                                                    height: 12,
                                                    borderRadius: '50%',
                                                    backgroundColor: COLORS[index % COLORS.length]
                                                }}
                                            />
                                            <Text fw={600}>{companyData.company}</Text>
                                        </Group>
                                        <Grid>
                                            {categoricalMetrics.map(metricKey => {
                                                const metric = metrics.find(m => m.key === metricKey);
                                                const value = companyData[metric?.label || metricKey];
                                                return (
                                                    <Grid.Col key={metricKey} span={6}>
                                                        <Text size="xs" c="dimmed">{metric?.label}</Text>
                                                        <Badge
                                                            variant="light"
                                                            color={COLORS[index % COLORS.length]}
                                                            size="lg"
                                                            fullWidth
                                                        >
                                                            {value}
                                                        </Badge>
                                                    </Grid.Col>
                                                );
                                            })}
                                        </Grid>
                                    </div>
                                ))}
                            </Stack>
                        </div>
                    )}

                    <Group justify="space-between" mt="md">
                        <Button variant="subtle" onClick={handleBack}>
                            Back to Selection
                        </Button>
                        <Button onClick={handleReset}>
                            Close
                        </Button>
                    </Group>
                </Stack>
            )}
        </Modal>
    );
}
