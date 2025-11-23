import { Group, Avatar, Title, ActionIcon } from '@mantine/core';
import { IconTrash } from '@tabler/icons-react';

interface CompetitorHeaderProps {
    name: string;
    logoUrl: string;
    onDelete?: () => void;
}

export function CompetitorHeader({ name, logoUrl, onDelete }: CompetitorHeaderProps) {
    const handleDelete = (e: React.MouseEvent) => {
        e.stopPropagation(); // Prevent card click
        onDelete?.();
    };

    return (
        <Group justify="space-between" mb="sm">
            <Group>
                <Avatar src={logoUrl} size="md" radius="sm" />
                <Title order={3}>{name}</Title>
            </Group>
            {onDelete && (
                <ActionIcon
                    variant="subtle"
                    color="red"
                    onClick={handleDelete}
                    data-delete-button
                    aria-label="Delete competitor"
                >
                    <IconTrash size={18} />
                </ActionIcon>
            )}
        </Group>
    );
}
