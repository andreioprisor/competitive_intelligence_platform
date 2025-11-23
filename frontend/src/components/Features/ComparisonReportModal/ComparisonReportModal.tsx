import { Modal, ScrollArea, Loader, Stack, Text } from '@mantine/core';

interface ComparisonReportModalProps {
    opened: boolean;
    onClose: () => void;
    report: string | null;
    loading: boolean;
    companySolution: string;
    competitorSolution: string;
    competitorDomain: string;
}

export function ComparisonReportModal({
    opened,
    onClose,
    report,
    loading,
    companySolution,
    competitorSolution,
    competitorDomain
}: ComparisonReportModalProps) {
    return (
        <Modal
            opened={opened}
            onClose={onClose}
            title={`Comparison Report: ${companySolution} vs ${competitorSolution}`}
            size="xl"
            centered
        >
            <ScrollArea h={600}>
                {loading ? (
                    <Stack align="center" justify="center" h={400}>
                        <Loader size="lg" />
                        <Text c="dimmed">Generating professional comparison report...</Text>
                        <Text size="sm" c="dimmed">
                            Analyzing {companySolution} vs {competitorDomain}'s {competitorSolution}
                        </Text>
                    </Stack>
                ) : report ? (
                    <div
                        style={{
                            padding: '20px',
                            fontFamily: 'system-ui, -apple-system, sans-serif',
                            lineHeight: '1.6'
                        }}
                        dangerouslySetInnerHTML={{ __html: report }}
                    />
                ) : (
                    <Text c="dimmed" ta="center">No report available</Text>
                )}
            </ScrollArea>
        </Modal>
    );
}
