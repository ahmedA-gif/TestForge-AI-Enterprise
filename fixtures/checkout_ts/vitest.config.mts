import { defineConfig } from 'vitest/config';
export default defineConfig({test:{include:['fixtures/checkout_ts/*.test.ts'],environment:'node'}});
