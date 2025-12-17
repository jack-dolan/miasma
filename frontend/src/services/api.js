import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

// Create axios instance with default config
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('miasma_access_token')
    if (token && token !== 'demo-token') {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('miasma_access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Lookup API
export const lookupApi = {
  // Search for a person
  search: async (params) => {
    const response = await api.post('/lookup/search', {
      first_name: params.firstName,
      last_name: params.lastName,
      city: params.city || null,
      state: params.state || null,
      age: params.age ? parseInt(params.age) : null,
      sources: params.sources || null,
      save_results: params.saveResults !== false,
    })
    return response.data
  },

  // Get list of available sources
  getSources: async () => {
    const response = await api.get('/lookup/sources')
    return response.data
  },

  // Get paginated list of lookup results
  getResults: async (params = {}) => {
    const response = await api.get('/lookup/results', {
      params: {
        page: params.page || 1,
        page_size: params.pageSize || 20,
        first_name: params.firstName || null,
        last_name: params.lastName || null,
      },
    })
    return response.data
  },

  // Get single lookup result by ID
  getResult: async (id) => {
    const response = await api.get(`/lookup/results/${id}`)
    return response.data
  },

  // Get detailed lookup result (includes raw data)
  getResultDetail: async (id) => {
    const response = await api.get(`/lookup/results/${id}/detail`)
    return response.data
  },

  // Delete a lookup result
  deleteResult: async (id) => {
    const response = await api.delete(`/lookup/results/${id}`)
    return response.data
  },
}

export default api
