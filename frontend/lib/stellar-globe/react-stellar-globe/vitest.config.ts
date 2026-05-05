import { defineConfig } from 'vite'

export default defineConfig({
  test: {
    include: ['./tests/**/*.{ts,tsx}'],
    environment: 'jsdom',
    coverage: {
      reporter: ['html'],
      reportsDirectory: './coverage'
    },
  },
})
