import { Card } from '@mantine/core';
import { CompetitorHeader } from './CompetitorHeader';
import { CompetitorContent } from './CompetitorContent';
import { CompetitorStrategies } from './CompetitorStrategies';

interface CompetitorCardProps {
    data: any;
}

export function CompetitorCard({ data }: CompetitorCardProps) {
    return (
        <Card withBorder padding="lg" radius="md" h="100%" bg="var(--mantine-color-body)">
            <CompetitorHeader name={data.name} logoUrl={data.logoUrl} />
            <CompetitorContent description={data.description} />
            <CompetitorStrategies strategies={data.strategies} />
        </Card>
    );
}
