import { Container, Grid } from '@mantine/core';
import { CompareManager } from './CompareManager';

interface UserPreferencesProps {
    customCategories: Array<{ id: string; label: string; description: string; isSystem?: boolean }>;
    onAddCategory: (category: { label: string; description: string }) => void;
    onDeleteCategory: (id: string) => void;
}

export function UserPreferences({ customCategories, onAddCategory, onDeleteCategory }: UserPreferencesProps) {
    return (
        <Container fluid>
            <Grid>
                <Grid.Col span={12}>
                    <CompareManager
                        customCategories={customCategories}
                        onAddCategory={onAddCategory}
                        onDeleteCategory={onDeleteCategory}
                    />
                </Grid.Col>
            </Grid>
        </Container>
    );
}
