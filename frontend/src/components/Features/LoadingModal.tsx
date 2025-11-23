import { Modal, Text, Stack, Progress } from '@mantine/core';
import { useState, useEffect } from 'react';

interface LoadingModalProps {
    opened: boolean;
}

const STEPS = [
    "Website Monitoring Agent",
    "Pricing Intelligence Agent",
    "Google Search Ads Agent",
    "News Search Agent",
    "Reddit/X Search Agents",
    "Jobs Posting Agent",
    "Social media Agent"
];

export function LoadingModal({ opened }: LoadingModalProps) {
    const [activeStep, setActiveStep] = useState(0);
    const [progress, setProgress] = useState(0);

    useEffect(() => {
        if (!opened) {
            setActiveStep(0);
            setProgress(0);
            return;
        }

        const stepDuration = 1500; // Time per step in ms

        const timer = setInterval(() => {
            setActiveStep((current) => {
                return (current + 1) % STEPS.length;
            });
        }, stepDuration);

        // Simulate progress for visual feedback, but don't auto-complete
        const progressTimer = setInterval(() => {
            setProgress((current) => {
                if (current >= 90) return 90; // Stall at 90% until real completion
                return current + 1;
            });
        }, 100);

        return () => {
            clearInterval(timer);
            clearInterval(progressTimer);
        };
    }, [opened]);

    return (
        <Modal
            opened={opened}
            onClose={() => { }}
            withCloseButton={false}
            centered
            closeOnClickOutside={false}
            size="lg"
        >
            <Stack gap="md" py="xl" px="md">
                <Text size="xl" fw={700} ta="center">
                    Analyzing Competition
                </Text>

                <Stack gap="xs">
                    <Text size="sm" fw={500} c="dimmed">
                        Current Agent:
                    </Text>
                    <Text size="lg" fw={600} c="orange">
                        {STEPS[activeStep]}
                    </Text>
                </Stack>

                <Progress value={progress} size="xl" radius="xl" />

                <Text c="dimmed" size="xs" ta="right">
                    {Math.round(progress)}% Complete
                </Text>
            </Stack>
        </Modal>
    );
}
