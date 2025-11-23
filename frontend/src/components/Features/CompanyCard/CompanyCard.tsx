import { Card } from '@mantine/core';
import { CompanyHeader } from './CompanyHeader';
import { CompanyContent } from './CompanyContent';
import { CompanyAnalytics } from './CompanyAnalytics';

interface CompanyCardProps {
    data: any;
}

export function CompanyCard({ data }: CompanyCardProps) {
    return (
        <Card withBorder padding="lg" radius="md" bg="var(--mantine-color-body)">
            <CompanyHeader
                domain={data.name || data.domain}
                logoUrl={data.logoUrl}
                domainOfActivity={data.domainOfActivity}
            />
            <CompanyContent
                description={data.description}
                employees={data.employees}
                differentiators={data.differentiators}
                services={data.services}
                businessModel={data.businessModel}
            />
            <CompanyAnalytics
                geography={data.geography}
                industryTrends={data.industryTrends}
            />
        </Card>
    );
}
