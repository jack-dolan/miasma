import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Shield, Mail, Lock, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [errors, setErrors] = useState({})

  const { login } = useAuth()
  const navigate = useNavigate()

  const validateForm = () => {
    const newErrors = {}

    if (!email) {
      newErrors.email = 'Email is required'
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      newErrors.email = 'Email is invalid'
    }

    if (!password) {
      newErrors.password = 'Password is required'
    } else if (password.length < 4) {
      newErrors.password = 'Password must be at least 6 characters'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }

    setIsLoading(true)
    setErrors({})

    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (error) {
      setErrors({ submit: error.message || 'Login failed' })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <Link to="/" className="inline-flex items-center space-x-2 mb-6">
            <Shield className="h-12 w-12 text-primary-500" />
            <h1 className="text-3xl font-bold text-gradient">Miasma</h1>
          </Link>
          <h2 className="text-2xl font-bold text-gray-100">
            Sign in to your account
          </h2>
          <p className="mt-2 text-gray-400">
            Protect your data privacy with strategic information management
          </p>
        </div>

        {/* Demo credentials info */}
        <div className="bg-blue-900/20 border border-blue-800 rounded-md p-4">
          <h3 className="text-sm font-medium text-blue-400 mb-2">Demo Credentials</h3>
          <p className="text-xs text-blue-300 mb-1">Email: demo@miasma.dev</p>
          <p className="text-xs text-blue-300">Password: demo</p>
        </div>

        {/* Login Form */}
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {errors.submit && (
            <div className="bg-red-900/20 border border-red-800 text-red-400 px-4 py-3 rounded-md text-sm">
              {errors.submit}
            </div>
          )}

          <div className="space-y-4">
            {/* Email field */}
            <div>
              <label htmlFor="email" className="label">
                Email address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={`input pl-10 ${errors.email ? 'input-error' : ''}`}
                  placeholder="Enter your email"
                  disabled={isLoading}
                />
              </div>
              {errors.email && (
                <p className="error-message">{errors.email}</p>
              )}
            </div>

            {/* Password field */}
            <div>
              <label htmlFor="password" className="label">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={`input pl-10 pr-10 ${errors.password ? 'input-error' : ''}`}
                  placeholder="Enter your password"
                  disabled={isLoading}
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  onClick={() => setShowPassword(!showPassword)}
                  disabled={isLoading}
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-300" />
                  ) : (
                    <Eye className="h-5 w-5 text-gray-400 hover:text-gray-300" />
                  )}
                </button>
              </div>
              {errors.password && (
                <p className="error-message">{errors.password}</p>
              )}
            </div>
          </div>

          {/* Remember me and forgot password */}
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <input
                id="remember-me"
                type="checkbox"
                className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-600 bg-gray-800 rounded"
              />
              <label htmlFor="remember-me" className="ml-2 text-sm text-gray-300">
                Remember me
              </label>
            </div>

            <div className="text-sm">
              <Link 
                to="/forgot-password" 
                className="text-primary-400 hover:text-primary-300 transition-colors"
              >
                Forgot your password?
              </Link>
            </div>
          </div>

          {/* Submit button */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full btn-primary btn-lg flex justify-center disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <div className="spinner h-5 w-5"></div>
            ) : (
              'Sign In'
            )}
          </button>

          {/* Back to home */}
          <div className="text-center">
            <Link 
              to="/" 
              className="text-sm text-gray-400 hover:text-gray-300 transition-colors"
            >
              ← Back to home
            </Link>
          </div>
        </form>
      </div>
    </div>
  )
}