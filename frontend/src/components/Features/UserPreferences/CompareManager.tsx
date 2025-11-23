import { Paper, Title, Text, Table, Button, Group, Modal, TextInput, Textarea, Stack, Badge, ActionIcon, Switch } from '@mantine/core';
import { useState } from 'react';
import { IconTrash } from '@tabler/icons-react';

interface Category {
    id: string;
    label: string;
    description: string;
    isSystem?: boolean;
}

const SYSTEM_CATEGORIES: Category[] = [
    { id: 'sys-1', label: 'Financials', description: 'Revenue, Market Cap, Growth Rate', isSystem: true },
    { id: 'sys-2', label: 'Market Presence', description: 'Market Share, Geography, Customers', isSystem: true },
    { id: 'sys-3', label: 'Employee Stats', description: 'Headcount, Satisfaction, Tenure', isSystem: true },
    { id: 'sys-4', label: 'Technology', description: 'Tech Stack, Patents, R&D', isSystem: true },
];

interface CompareManagerProps {
    customCategories: Array<{ id: string; label: string; description: string; isSystem?: boolean }>;
    onAddCategory: (category: { label: string; description: string }) => void;
    onDeleteCategory: (id: string) => void;
}

export function CompareManager({ customCategories, onAddCategory, onDeleteCategory }: CompareManagerProps) {
    const [opened, setOpened] = useState(false);
    const [newCategory, setNewCategory] = useState({ label: '', description: '' });
    const [monitorCompetitors, setMonitorCompetitors] = useState(true);

    const handleAddCategory = () => {
        if (!newCategory.label) return;

        onAddCategory(newCategory);
        setOpened(false);
        setNewCategory({ label: '', description: '' });
    };

    const allCategories = [...SYSTEM_CATEGORIES, ...customCategories];

    return (
        <Paper withBorder radius="md" p="md" bg="var(--mantine-color-body)">
            <Group justify="space-between" mb="md">
                <div>
                    <Title order={4}>Compare Manager</Title>
                    <Text size="sm" c="dimmed">Manage comparison categories</Text>
                </div>
                <Button onClick={() => setOpened(true)}>Add Category</Button>
            </Group>

            <Table>
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th>Category</Table.Th>
                        <Table.Th>Description</Table.Th>
                        <Table.Th>Type</Table.Th>
                        <Table.Th style={{ width: 50 }}></Table.Th>
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                    {allCategories.map((category) => {
                        return (
                            <Table.Tr key={category.id}>
                                <Table.Td>
                                    <Text fw={500}>{category.label}</Text>
                                </Table.Td>
                                <Table.Td>
                                    <Text size="sm" c="dimmed">{category.description}</Text>
                                </Table.Td>
                                <Table.Td>
                                    <Badge color={category.isSystem ? 'blue' : 'green'} variant="light">
                                        {category.isSystem ? 'System' : 'Custom'}
                                    </Badge>
                                </Table.Td>
                                <Table.Td>
                                    {!category.isSystem && (
                                        <ActionIcon
                                            variant="subtle"
                                            color="red"
                                            onClick={() => onDeleteCategory(category.id)}
                                        >
                                            <IconTrash size={16} />
                                        </ActionIcon>
                                    )}
                                </Table.Td>
                            </Table.Tr>
                        );
                    })}
                </Table.Tbody>
            </Table>

            <Modal opened={opened} onClose={() => setOpened(false)} title="Add Criteria for Analysis">
                <Stack>
                    <Text size="sm" c="dimmed">
                        Adding criteria will trigger AI analysis across all competitors. This may take a few minutes.
                    </Text>

                    <Switch
                        checked={monitorCompetitors}
                        onChange={(event) => setMonitorCompetitors(event.currentTarget.checked)}
                        label="Monitor all competitors for this criteria"
                        description="We will continuously track this criteria across all your competitors"
                        size="md"
                        mt="md"
                    />

                    <TextInput
                        label="Criteria Name"
                        placeholder="e.g., AI Agent Capabilities"
                        value={newCategory.label}
                        onChange={(event) => setNewCategory({ ...newCategory, label: event.currentTarget.value })}
                        data-autofocus
                        mt="md"
                    />
                    <Textarea
                        label="Criteria Definition"
                        placeholder="Describe what to analyze (e.g., Analyze the competitor's AI agent capabilities, automation features, and machine learning integration)"
                        value={newCategory.description}
                        onChange={(event) => setNewCategory({ ...newCategory, description: event.currentTarget.value })}
                        minRows={3}
                    />
                    <Group justify="flex-end" mt="md">
                        <Button variant="default" onClick={() => setOpened(false)}>Cancel</Button>
                        <Button onClick={handleAddCategory}>Analyze Competitors</Button>
                    </Group>
                </Stack>
            </Modal>
        </Paper>
    );
}
