import { Group, Text, ActionIcon, useMantineColorScheme } from '@mantine/core';
import { IconSun, IconMoon } from '@tabler/icons-react';

export function Navbar() {
    const { setColorScheme, colorScheme } = useMantineColorScheme();
    const computedColorScheme = colorScheme === 'auto' ? 'dark' : colorScheme;

    const toggleColorScheme = () => {
        setColorScheme(computedColorScheme === 'dark' ? 'light' : 'dark');
    };

    return (
        <Group justify="space-between" h="100%" px="md">
            <Text fw={700} size="lg">Competitor Analysis</Text>
            <ActionIcon
                variant="default"
                onClick={toggleColorScheme}
                size={30}
                aria-label="Toggle color scheme"
            >
                {computedColorScheme === 'dark' ? <IconSun size={18} /> : <IconMoon size={18} />}
            </ActionIcon>
        </Group>
    );
}
