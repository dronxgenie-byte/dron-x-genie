import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export const sendMessage = (query, agent = 'x') => api.post('/chat', { query, agent })

export const getFamily = () => api.get('/bank/family')

export const createTransaction = (data) => api.post('/bank/transaction', data)

export const getTreasury = () => api.get('/bank/treasury')

export default api
