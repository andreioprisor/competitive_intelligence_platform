import { Card } from '@mantine/core';
import { CompetitorHeader } from './CompetitorHeader';
import { CompetitorContent } from './CompetitorContent';
import { CompetitorStrategies } from './CompetitorStrategies';

interface CompetitorCardProps {
    data: any;
    onClick?: () => void;
}

export function CompetitorCard({ data, onClick }: CompetitorCardProps) {
    return (
        <Card
            withBorder
            padding="lg"
            radius="md"
            h="100%"
            bg="var(--mantine-color-body)"
            style={{ cursor: onClick ? 'pointer' : 'default' }}
            onClick={onClick}
        >
            <CompetitorHeader name={data.name} logoUrl={data.logoUrl} />
            <CompetitorContent description={data.description} />
            <CompetitorStrategies strategies={data.strategies} />
        </Card>
    );
}
