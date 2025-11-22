import { Text, Group, Badge } from '@mantine/core';

interface CompetitorStrategiesProps {
    strategies: string[];
}

export function CompetitorStrategies({ strategies }: CompetitorStrategiesProps) {
    return (
        <>
            <Text fw={500} size="sm" mt="md" mb="xs">Strategies:</Text>
            <Group gap="xs">
                {strategies.map((strategy, idx) => (
                    <Badge key={idx} variant="outline" color="teal">
                        {strategy}
                    </Badge>
                ))}
            </Group>
        </>
    );
}
