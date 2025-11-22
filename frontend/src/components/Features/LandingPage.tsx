import { Container, Title, TextInput, Button, Stack, Center } from '@mantine/core';
import { useState } from 'react';

interface LandingPageProps {
    onSearch: (domain: string) => void;
}

export function LandingPage({ onSearch }: LandingPageProps) {
    const [domain, setDomain] = useState('');

    return (
        <Center style={{ height: 'calc(100vh - 60px)' }}>
            <Container size="sm">
                <Stack align="center" gap="xl">
                    <Title order={1} size="3rem" style={{ textAlign: 'center' }}>
                        Analyze Your Competition
                    </Title>
                    <TextInput
                        placeholder="Enter company domain (e.g., uipath.com)"
                        size="xl"
                        style={{ width: '100%', maxWidth: '500px' }}
                        value={domain}
                        onChange={(event) => setDomain(event.currentTarget.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && domain) {
                                onSearch(domain);
                            }
                        }}
                    />
                    <Button
                        size="xl"
                        onClick={() => domain && onSearch(domain)}
                        disabled={!domain}
                    >
                        Get Started
                    </Button>
                </Stack>
            </Container>
        </Center>
    );
}
