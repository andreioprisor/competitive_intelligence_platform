import { Paper, Title, Text, Table, Button, Group, Modal, TextInput, Textarea, Stack, Badge, ActionIcon, Switch } from '@mantine/core';
import { useState } from 'react';
import { IconTrash } from '@tabler/icons-react';
import type { CriteriaItem } from '../../../services/api';

interface Category {
    id: string;
    label: string;
    description: string;
    isSystem?: boolean;
}

interface CompareManagerProps {
    customCategories: Array<{ id: string; label: string; description: string; isSystem?: boolean }>;
    onAddCategory: (category: { label: string; description: string }) => void;
    onDeleteCategory: (id: string) => void;
    criterias: CriteriaItem[];
}

export function CompareManager({ customCategories, onAddCategory, onDeleteCategory, criterias }: CompareManagerProps) {
    const [opened, setOpened] = useState(false);
    const [newCategory, setNewCategory] = useState({ label: '', description: '' });
    const [monitorCompetitors, setMonitorCompetitors] = useState(true);

    const handleAddCategory = () => {
        if (!newCategory.label) return;

        onAddCategory(newCategory);
        setOpened(false);
        setNewCategory({ label: '', description: '' });
    };

    return (
        <Paper withBorder radius="md" p="md" bg="var(--mantine-color-body)">
            <Group justify="space-between" mb="md">
                <div>
                    <Title order={4}>Criteria Manager</Title>
                    <Text size="sm" c="dimmed">Manage analysis criteria for competitor monitoring</Text>
                </div>
                <Button onClick={() => setOpened(true)}>Add Criteria</Button>
            </Group>

            <Table>
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th>Criteria Name</Table.Th>
                        <Table.Th>Definition</Table.Th>
                        <Table.Th>Created At</Table.Th>
                        <Table.Th style={{ width: 50 }}></Table.Th>
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                    {criterias.map((criteria) => {
                        const createdDate = new Date(criteria.created_at);
                        const formattedDate = createdDate.toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric'
                        });

                        return (
                            <Table.Tr key={criteria.id}>
                                <Table.Td>
                                    <Text fw={500}>{criteria.name}</Text>
                                </Table.Td>
                                <Table.Td>
                                    <Text size="sm" c="dimmed">{criteria.definition}</Text>
                                </Table.Td>
                                <Table.Td>
                                    <Text size="sm" c="dimmed">{formattedDate}</Text>
                                </Table.Td>
                                <Table.Td>
                                    <ActionIcon
                                        variant="subtle"
                                        color="red"
                                        onClick={() => onDeleteCategory(criteria.id.toString())}
                                    >
                                        <IconTrash size={16} />
                                    </ActionIcon>
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
