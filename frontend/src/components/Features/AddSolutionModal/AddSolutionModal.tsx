import { Modal, TextInput, Textarea, Button, Stack, Group, MultiSelect } from '@mantine/core';
import { useState } from 'react';

interface AddSolutionModalProps {
    opened: boolean;
    onClose: () => void;
    onAdd: (solution: {
        name: string;
        description: string;
        industries: string[];
        features: string[];
        benefits: string[];
        useCases: string[];
    }) => void;
}

const COMMON_INDUSTRIES = [
    'Healthcare',
    'Finance',
    'Retail',
    'Manufacturing',
    'Technology',
    'Education',
    'Government',
    'Transportation',
    'Energy',
    'Telecommunications'
];

export function AddSolutionModal({ opened, onClose, onAdd }: AddSolutionModalProps) {
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [industries, setIndustries] = useState<string[]>([]);
    const [features, setFeatures] = useState('');
    const [benefits, setBenefits] = useState('');
    const [useCases, setUseCases] = useState('');

    const handleSubmit = () => {
        const solution = {
            name,
            description,
            industries,
            features: features.split('\n').filter(f => f.trim()),
            benefits: benefits.split('\n').filter(b => b.trim()),
            useCases: useCases.split('\n').filter(u => u.trim())
        };

        onAdd(solution);
        handleClose();
    };

    const handleClose = () => {
        // Reset form
        setName('');
        setDescription('');
        setIndustries([]);
        setFeatures('');
        setBenefits('');
        setUseCases('');
        onClose();
    };

    const isFormValid = name.trim() && description.trim() && industries.length > 0;

    return (
        <Modal
            opened={opened}
            onClose={handleClose}
            title="Add New Solution"
            size="lg"
            centered
        >
            <Stack gap="md">
                <TextInput
                    label="Solution Name"
                    placeholder="Enter solution name"
                    value={name}
                    onChange={(e) => setName(e.currentTarget.value)}
                    required
                />

                <Textarea
                    label="Description"
                    placeholder="Describe your solution"
                    value={description}
                    onChange={(e) => setDescription(e.currentTarget.value)}
                    minRows={3}
                    required
                />

                <MultiSelect
                    label="Target Industries"
                    placeholder="Select industries"
                    data={COMMON_INDUSTRIES}
                    value={industries}
                    onChange={setIndustries}
                    searchable
                    required
                />

                <Textarea
                    label="Key Features"
                    placeholder="Enter each feature on a new line"
                    value={features}
                    onChange={(e) => setFeatures(e.currentTarget.value)}
                    minRows={3}
                />

                <Textarea
                    label="Benefits"
                    placeholder="Enter each benefit on a new line"
                    value={benefits}
                    onChange={(e) => setBenefits(e.currentTarget.value)}
                    minRows={3}
                />

                <Textarea
                    label="Use Cases"
                    placeholder="Enter each use case on a new line"
                    value={useCases}
                    onChange={(e) => setUseCases(e.currentTarget.value)}
                    minRows={3}
                />

                <Group justify="flex-end" mt="md">
                    <Button variant="subtle" onClick={handleClose}>
                        Cancel
                    </Button>
                    <Button onClick={handleSubmit} disabled={!isFormValid}>
                        Add Solution
                    </Button>
                </Group>
            </Stack>
        </Modal>
    );
}
