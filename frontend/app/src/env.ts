export const env = {
  baseUrl: import.meta.env.VITE_BASE_URL,
}

if (!env.baseUrl) {
  alert('VITE_BASE_URL is not set.')
}
