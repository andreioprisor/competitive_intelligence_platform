import { Text } from '@mantine/core';

interface CompetitorContentProps {
    description: string;
}

export function CompetitorContent({ description }: CompetitorContentProps) {
    return (
        <Text size="sm" c="dimmed" mb="md" style={{ minHeight: '40px' }}>
            {description}
        </Text>
    );
}
