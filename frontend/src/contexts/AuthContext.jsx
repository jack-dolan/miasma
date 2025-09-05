import { createContext, useContext, useState, useEffect } from 'react'
import toast from 'react-hot-toast'

const AuthContext = createContext({})

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  // Check if user is logged in on app load
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

      // TODO: Verify token with backend
      // For now, just mock a user if token exists
      if (token === 'demo-token') {
        setUser({
          id: 1,
          email: 'demo@miasma.dev',
          name: 'Demo User',
          createdAt: '2025-01-01T00:00:00Z'
        })
      }
      
      setIsLoading(false)
    } catch (error) {
      console.error('Auth check failed:', error)
      localStorage.removeItem('miasma_access_token')
      setIsLoading(false)
    }
  }

  const login = async (email, password) => {
    try {
      // TODO: Replace with actual API call to backend
      // For now, mock login for development
      if (email === 'demo@miasma.dev' && password === 'demo') {
        const mockUser = {
          id: 1,
          email: 'demo@miasma.dev',
          name: 'Demo User',
          createdAt: '2025-01-01T00:00:00Z'
        }
        
        localStorage.setItem('miasma_access_token', 'demo-token')
        setUser(mockUser)
        toast.success('Successfully logged in!')
        return mockUser
      } else {
        throw new Error('Invalid credentials')
      }
    } catch (error) {
      toast.error(error.message || 'Login failed')
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