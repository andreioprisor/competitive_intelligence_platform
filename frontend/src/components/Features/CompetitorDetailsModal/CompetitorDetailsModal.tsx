import { Modal, Stack, Group, Text, Title, Badge, Avatar, Grid, Divider } from '@mantine/core';
import { IconMapPin, IconWorld, IconCategory } from '@tabler/icons-react';

interface CompetitorDetailsModalProps {
    opened: boolean;
    onClose: () => void;
    competitor: {
        name: string;
        logoUrl: string;
        description: string;
        strategies: string[];
        category: string;
        website: string;
        location: string;
    } | null;
}

export function CompetitorDetailsModal({ opened, onClose, competitor }: CompetitorDetailsModalProps) {
    if (!competitor) return null;

    return (
        <Modal
            opened={opened}
            onClose={onClose}
            title="Competitor Details"
            size="lg"
            centered
        >
            <Stack gap="lg">
                {/* Header with logo and name */}
                <Group>
                    <Avatar
                        src={competitor.logoUrl}
                        size={64}
                        radius="md"
                    />
                    <div style={{ flex: 1 }}>
                        <Title order={3}>{competitor.name}</Title>
                        <Group gap="xs" mt="xs">
                            <Badge color="blue" variant="light">
                                {competitor.category}
                            </Badge>
                        </Group>
                    </div>
                </Group>

                <Divider />

                {/* Basic Information */}
                <div>
                    <Title order={5} mb="sm">Basic Information</Title>
                    <Stack gap="sm">
                        <Group gap="xs">
                            <IconMapPin size={16} />
                            <Text size="sm" fw={500}>Location:</Text>
                            <Text size="sm" c="dimmed">{competitor.location}</Text>
                        </Group>

                        {competitor.website && (
                            <Group gap="xs">
                                <IconWorld size={16} />
                                <Text size="sm" fw={500}>Website:</Text>
                                <Text
                                    size="sm"
                                    c="blue"
                                    component="a"
                                    href={`https://${competitor.website}`}
                                    target="_blank"
                                    style={{ textDecoration: 'none' }}
                                >
                                    {competitor.website}
                                </Text>
                            </Group>
                        )}

                        <Group gap="xs">
                            <IconCategory size={16} />
                            <Text size="sm" fw={500}>Category:</Text>
                            <Text size="sm" c="dimmed">{competitor.category} Competitor</Text>
                        </Group>
                    </Stack>
                </div>

                <Divider />

                {/* Description */}
                <div>
                    <Title order={5} mb="sm">Description</Title>
                    <Text size="sm" c="dimmed">
                        {competitor.description}
                    </Text>
                </div>

                {/* Strategies */}
                {competitor.strategies && competitor.strategies.length > 0 && (
                    <>
                        <Divider />
                        <div>
                            <Title order={5} mb="sm">Competitive Strategies</Title>
                            <Stack gap="xs">
                                {competitor.strategies.map((strategy, index) => (
                                    <Group key={index} gap="xs">
                                        <Text size="sm" c="dimmed">•</Text>
                                        <Text size="sm">{strategy}</Text>
                                    </Group>
                                ))}
                            </Stack>
                        </div>
                    </>
                )}
            </Stack>
        </Modal>
    );
}
