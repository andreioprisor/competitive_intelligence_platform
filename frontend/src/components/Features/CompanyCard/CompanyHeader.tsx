import { Group, Avatar, Title, Badge } from '@mantine/core';

interface CompanyHeaderProps {
    domain: string;
    logoUrl: string;
    domainOfActivity: string;
}

export function CompanyHeader({ domain, logoUrl, domainOfActivity }: CompanyHeaderProps) {
    return (
        <Group justify="space-between" mb="md">
            <Group>
                <Avatar src={logoUrl} size="lg" radius="md" />
                <Title order={2}>{domain}</Title>
            </Group>
            <Badge size="lg" variant="light">{domainOfActivity}</Badge>
        </Group>
    );
}
