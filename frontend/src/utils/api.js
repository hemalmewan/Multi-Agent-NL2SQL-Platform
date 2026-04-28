import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 120_000,
  headers: { 'Content-Type': 'application/json' },
})

export async function sendQuery(query, refinedQuery = null) {
  const { data } = await client.post('/query', {
    query,
    refined_query: refinedQuery,
  })
  return data
}

export async function checkHealth() {
  const { data } = await client.get('/health')
  return data
}
