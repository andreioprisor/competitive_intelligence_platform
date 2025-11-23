import { Card } from '@mantine/core';
import { CompetitorHeader } from './CompetitorHeader';
import { CompetitorContent } from './CompetitorContent';
import { CompetitorStrategies } from './CompetitorStrategies';

interface CompetitorCardProps {
    data: any;
    onClick?: () => void;
    onDelete?: () => void;
}

export function CompetitorCard({ data, onClick, onDelete }: CompetitorCardProps) {
    const handleCardClick = (e: React.MouseEvent) => {
        // Don't trigger onClick if clicking on delete button
        if (!(e.target as HTMLElement).closest('[data-delete-button]')) {
            onClick?.();
        }
    };

    return (
        <Card
            withBorder
            padding="lg"
            radius="md"
            h="100%"
            bg="var(--mantine-color-body)"
            style={{ cursor: onClick ? 'pointer' : 'default' }}
            onClick={handleCardClick}
        >
            <CompetitorHeader name={data.name} logoUrl={data.logoUrl} onDelete={onDelete} />
            <CompetitorContent description={data.description} />
            <CompetitorStrategies strategies={data.strategies} />
        </Card>
    );
}
