import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  use: {
    baseURL: 'http://localhost:49752',
  },
  webServer: {
    command: 'hugo server --disableFastRender --port 49752',
    url: 'http://localhost:49752',
    reuseExistingServer: true,
    timeout: 30000,
  },
});
