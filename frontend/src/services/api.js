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
    if (token) {
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
      localStorage.removeItem('miasma_refresh_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Lookup API
export const lookupApi = {
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

  getSources: async () => {
    const response = await api.get('/lookup/sources')
    return response.data
  },

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

  getResult: async (id) => {
    const response = await api.get(`/lookup/results/${id}`)
    return response.data
  },

  getResultDetail: async (id) => {
    const response = await api.get(`/lookup/results/${id}/detail`)
    return response.data
  },

  deleteResult: async (id) => {
    const response = await api.delete(`/lookup/results/${id}`)
    return response.data
  },
}

// Campaign API
export const campaignApi = {
  list: async (params = {}) => {
    const response = await api.get('/campaigns/', {
      params: {
        page: params.page || 1,
        page_size: params.pageSize || 20,
        status: params.status || null,
      },
    })
    return response.data
  },

  get: async (id) => {
    const response = await api.get(`/campaigns/${id}`)
    return response.data
  },

  create: async (data) => {
    const response = await api.post('/campaigns/', {
      name: data.name,
      description: data.description || null,
      target_sites: data.targetSites || null,
      target_count: data.targetCount || 10,
    })
    return response.data
  },

  update: async (id, data) => {
    const response = await api.patch(`/campaigns/${id}`, data)
    return response.data
  },

  delete: async (id) => {
    const response = await api.delete(`/campaigns/${id}`)
    return response.data
  },
}

// Analytics API
export const analyticsApi = {
  getDashboard: async () => {
    const response = await api.get('/analytics/dashboard')
    return response.data
  },
}

export default api
