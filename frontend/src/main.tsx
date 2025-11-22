import React from 'react';
import ReactDOM from 'react-dom/client';
import { MantineProvider, createTheme } from '@mantine/core';
import App from './App.tsx';
import '@mantine/core/styles.css';

const theme = createTheme({
  colors: {
    dark: [
      '#C9C9C9',
      '#B8B8B8',
      '#828282',
      '#696969',
      '#424242',
      '#3B3B3B',
      '#2E2E2E',
      '#121212', // Default body background in dark mode
      '#0A0A0A',
      '#000000',
    ],
  },
  primaryColor: 'orange',
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <MantineProvider theme={theme} defaultColorScheme="dark">
      <App />
    </MantineProvider>
  </React.StrictMode>,
);
