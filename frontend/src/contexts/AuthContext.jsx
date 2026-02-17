import { createContext, useContext, useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import api from '../services/api'

const AuthContext = createContext({})

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    checkAuth()
  }, [])

  const checkAuth = async () => {
    try {
      const token = localStorage.getItem('miasma_access_token')
      if (!token) {
        setIsLoading(false)
        return
      }

      const response = await api.get('/auth/me')
      setUser(response.data)
      setIsLoading(false)
    } catch (error) {
      console.error('Auth check failed:', error)
      localStorage.removeItem('miasma_access_token')
      localStorage.removeItem('miasma_refresh_token')
      setIsLoading(false)
    }
  }

  const login = async (email, password) => {
    try {
      const response = await api.post('/auth/login', { email, password })
      const { access_token, refresh_token, user: userData } = response.data

      localStorage.setItem('miasma_access_token', access_token)
      localStorage.setItem('miasma_refresh_token', refresh_token)
      setUser(userData)
      toast.success('Successfully logged in!')
      return userData
    } catch (error) {
      const message = error.response?.data?.detail || 'Login failed'
      toast.error(message)
      throw new Error(message)
    }
  }

  const register = async (email, password, fullName) => {
    try {
      await api.post('/auth/register', {
        email,
        password,
        full_name: fullName,
      })

      // Auto-login after registration
      return await login(email, password)
    } catch (error) {
      const detail = error.response?.data?.detail
      let message = 'Registration failed'
      if (typeof detail === 'string') {
        message = detail
      } else if (detail?.message) {
        message = detail.message
      }
      toast.error(message)
      throw new Error(message)
    }
  }

  const demoLogin = async () => {
    try {
      const response = await api.post('/auth/demo-login')
      const { access_token, refresh_token, user: userData } = response.data

      localStorage.setItem('miasma_access_token', access_token)
      localStorage.setItem('miasma_refresh_token', refresh_token)
      setUser(userData)
      toast.success('Logged in as demo user')
      return userData
    } catch (error) {
      toast.error('Demo login failed')
      throw error
    }
  }

  const logout = async () => {
    try {
      localStorage.removeItem('miasma_access_token')
      localStorage.removeItem('miasma_refresh_token')
      setUser(null)
      toast.success('Successfully logged out')
    } catch (error) {
      toast.error('Logout failed')
      throw error
    }
  }

  const value = {
    user,
    isLoading,
    login,
    register,
    demoLogin,
    logout,
    checkAuth,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
