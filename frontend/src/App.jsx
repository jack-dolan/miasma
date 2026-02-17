import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { Shield, Eye, Database, BarChart3 } from 'lucide-react'

// Import pages (we'll create these as placeholders)
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import LookupPage from './pages/LookupPage'
import CampaignsPage from './pages/CampaignsPage'
import AnalyticsPage from './pages/AnalyticsPage'

// Import components
import Navbar from './components/common/Navbar'
import Sidebar from './components/common/Sidebar'
import LoadingSpinner from './components/common/LoadingSpinner'

// Import context/hooks (we'll create these)
import { AuthProvider, useAuth } from './contexts/AuthContext'

// Layout component for authenticated pages
function AuthenticatedLayout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  
  return (
    <div className="flex h-screen bg-gray-950">
      {/* Sidebar */}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      
      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top navbar */}
        <Navbar onMenuClick={() => setSidebarOpen(true)} />
        
        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}

// Protected route component
function ProtectedRoute({ children }) {
  const { user, isLoading } = useAuth()
  
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <LoadingSpinner size="lg" />
      </div>
    )
  }
  
  if (!user) {
    return <Navigate to="/login" replace />
  }
  
  return <AuthenticatedLayout>{children}</AuthenticatedLayout>
}

// Public route (redirects to dashboard if authenticated)
function PublicRoute({ children }) {
  const { user, isLoading } = useAuth()
  
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <LoadingSpinner size="lg" />
      </div>
    )
  }
  
  if (user) {
    return <Navigate to="/dashboard" replace />
  }
  
  return children
}

function App() {
  return (
    <AuthProvider>
      <div className="App">
        <Routes>
          {/* Public routes */}
          <Route 
            path="/" 
            element={
              <PublicRoute>
                <HomePage />
              </PublicRoute>
            } 
          />
          <Route 
            path="/login" 
            element={
              <PublicRoute>
                <LoginPage />
              </PublicRoute>
            } 
          />
          
          {/* Protected routes */}
          <Route 
            path="/dashboard" 
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/lookup" 
            element={
              <ProtectedRoute>
                <LookupPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/campaigns" 
            element={
              <ProtectedRoute>
                <CampaignsPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/analytics" 
            element={
              <ProtectedRoute>
                <AnalyticsPage />
              </ProtectedRoute>
            } 
          />
          
          {/* Catch all route */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </AuthProvider>
  )
}

export default App