import axios from 'axios'

// Use relative URL in production, absolute in development
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 
  (import.meta.env.PROD ? '/api' : 'http://localhost:8000/api')

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
  },
})

export const sendChatMessage = async (question) => {
  const formData = new URLSearchParams()
  formData.append('question', question)
  
  const response = await apiClient.post('/chat/', formData)
  return response.data
}

export const getChatHistory = async () => {
  const response = await apiClient.get('/history/')
  return response.data
}

