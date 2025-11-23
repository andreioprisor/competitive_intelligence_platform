import { Text, Title, Group, Stack, Textarea, Button, Grid } from '@mantine/core';
import { useState } from 'react';

interface CompanyContentProps {
    description: string;
    employees: string;
    differentiators: string;
    services: string;
    businessModel: string;
    onSave?: (description: string) => Promise<void>;
    isSaved?: boolean;
}

export function CompanyContent({
    description: initialDescription,
    employees,
    differentiators,
    services,
    businessModel,
    onSave,
    isSaved = false
}: CompanyContentProps) {
    const [description, setDescription] = useState(initialDescription);
    const [isEditing, setIsEditing] = useState(false);
    const [draftDescription, setDraftDescription] = useState(description);
    const [isSaving, setIsSaving] = useState(false);

    const handleStartEdit = () => {
        if (isSaved) return; // Prevent editing after save
        setDraftDescription(description);
        setIsEditing(true);
    };

    const handleSave = () => {
        setDescription(draftDescription);
        setIsEditing(false);
    };

    const handleCancel = () => {
        setIsEditing(false);
    };

    const handleSaveProfile = async () => {
        if (!onSave) return;
        setIsSaving(true);
        try {
            await onSave(description);
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <Stack gap="md">
            {isEditing ? (
                <Stack mb="md">
                    <Textarea
                        value={draftDescription}
                        onChange={(event) => setDraftDescription(event.currentTarget.value)}
                        autosize
                        minRows={3}
                    />
                    <Group>
                        <Button size="xs" onClick={handleSave}>Save</Button>
                        <Button size="xs" variant="subtle" onClick={handleCancel}>Cancel</Button>
                    </Group>
                </Stack>
            ) : (
                <Text
                    size="lg"
                    mb="md"
                    onClick={handleStartEdit}
                    style={{
                        cursor: isSaved ? 'default' : 'pointer',
                        border: '1px dashed transparent'
                    }}
                    onMouseEnter={(e) => !isSaved && (e.currentTarget.style.borderColor = 'var(--mantine-color-dimmed)')}
                    onMouseLeave={(e) => e.currentTarget.style.borderColor = 'transparent'}
                    p="xs"
                    title={isSaved ? '' : 'Click to edit description'}
                >
                    {description}
                </Text>
            )}

            {!isSaved && onSave && (
                <Group justify="flex-end" mb="md">
                    <Button
                        onClick={handleSaveProfile}
                        loading={isSaving}
                        size="md"
                    >
                        Save Profile
                    </Button>
                </Group>
            )}

            <Grid>
                <Grid.Col span={6}>
                    <Title order={5}>Employees</Title>
                    <Text size="sm">{employees}</Text>
                </Grid.Col>
                <Grid.Col span={6}>
                    <Title order={5}>Services</Title>
                    <Text size="sm">{services}</Text>
                </Grid.Col>
                <Grid.Col span={12}>
                    <Title order={5}>Differentiators</Title>
                    <Text size="sm">{differentiators}</Text>
                </Grid.Col>
                <Grid.Col span={12}>
                    <Title order={5}>Business Model</Title>
                    <Text size="sm">{businessModel}</Text>
                </Grid.Col>
            </Grid>
        </Stack>
    );
}
