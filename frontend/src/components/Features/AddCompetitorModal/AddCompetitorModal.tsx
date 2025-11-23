import { Modal, TextInput, Textarea, Button, Stack, Group, Select } from '@mantine/core';
import { useState } from 'react';

interface AddCompetitorModalProps {
    opened: boolean;
    onClose: () => void;
    onAdd: (competitor: {
        name: string;
        domain: string;
        description: string;
        category: string;
        location: string;
        website: string;
    }) => void;
}

const COMPETITOR_CATEGORIES = [
    { value: 'Direct', label: 'Direct Competitor' },
    { value: 'Indirect', label: 'Indirect Competitor' },
    { value: 'Emerging', label: 'Emerging Competitor' }
];

export function AddCompetitorModal({ opened, onClose, onAdd }: AddCompetitorModalProps) {
    const [name, setName] = useState('');
    const [domain, setDomain] = useState('');
    const [description, setDescription] = useState('');
    const [category, setCategory] = useState<string>('Direct');
    const [location, setLocation] = useState('');
    const [website, setWebsite] = useState('');

    const handleSubmit = () => {
        const competitor = {
            name: name || domain,
            domain,
            description,
            category,
            location,
            website: website || domain
        };

        onAdd(competitor);
        handleClose();
    };

    const handleClose = () => {
        // Reset form
        setName('');
        setDomain('');
        setDescription('');
        setCategory('Direct');
        setLocation('');
        setWebsite('');
        onClose();
    };

    const isFormValid = domain.trim() && description.trim();

    return (
        <Modal
            opened={opened}
            onClose={handleClose}
            title="Add New Competitor"
            size="lg"
            centered
        >
            <Stack gap="md">
                <TextInput
                    label="Domain"
                    placeholder="example.com"
                    value={domain}
                    onChange={(e) => setDomain(e.currentTarget.value)}
                    required
                    description="Competitor's website domain"
                />

                <TextInput
                    label="Company Name (Optional)"
                    placeholder="Enter company name"
                    value={name}
                    onChange={(e) => setName(e.currentTarget.value)}
                    description="If not provided, domain will be used"
                />

                <Textarea
                    label="Description"
                    placeholder="Describe the competitor and their offerings"
                    value={description}
                    onChange={(e) => setDescription(e.currentTarget.value)}
                    minRows={3}
                    required
                />

                <Select
                    label="Category"
                    placeholder="Select competitor category"
                    data={COMPETITOR_CATEGORIES}
                    value={category}
                    onChange={(value) => setCategory(value || 'Direct')}
                    required
                />

                <TextInput
                    label="Location"
                    placeholder="e.g., San Francisco, CA"
                    value={location}
                    onChange={(e) => setLocation(e.currentTarget.value)}
                />

                <TextInput
                    label="Website (Optional)"
                    placeholder="https://example.com"
                    value={website}
                    onChange={(e) => setWebsite(e.currentTarget.value)}
                    description="If not provided, domain will be used"
                />

                <Group justify="flex-end" mt="md">
                    <Button variant="subtle" onClick={handleClose}>
                        Cancel
                    </Button>
                    <Button onClick={handleSubmit} disabled={!isFormValid}>
                        Add Competitor
                    </Button>
                </Group>
            </Stack>
        </Modal>
    );
}
