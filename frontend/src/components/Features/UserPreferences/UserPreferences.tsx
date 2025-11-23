import { Container, Grid } from '@mantine/core';
import { CompareManager } from './CompareManager';
import type { CriteriaItem } from '../../../services/api';

interface UserPreferencesProps {
    customCategories: Array<{ id: string; label: string; description: string; isSystem?: boolean }>;
    onAddCategory: (category: { label: string; description: string }) => void;
    onDeleteCategory: (id: string) => void;
    criterias: CriteriaItem[];
}

export function UserPreferences({ customCategories, onAddCategory, onDeleteCategory, criterias }: UserPreferencesProps) {
    return (
        <Container fluid>
            <Grid>
                <Grid.Col span={12}>
                    <CompareManager
                        customCategories={customCategories}
                        onAddCategory={onAddCategory}
                        onDeleteCategory={onDeleteCategory}
                        criterias={criterias}
                    />
                </Grid.Col>
            </Grid>
        </Container>
    );
}
