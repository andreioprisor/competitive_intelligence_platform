import { Group, Avatar, Title } from '@mantine/core';

interface CompetitorHeaderProps {
    name: string;
    logoUrl: string;
}

export function CompetitorHeader({ name, logoUrl }: CompetitorHeaderProps) {
    return (
        <Group mb="sm">
            <Avatar src={logoUrl} size="md" radius="sm" />
            <Title order={3}>{name}</Title>
        </Group>
    );
}
