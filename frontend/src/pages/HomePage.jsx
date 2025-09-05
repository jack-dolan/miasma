import { Link } from 'react-router-dom'
import { Shield, Eye, Database, Zap, Lock, Users } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center space-x-2">
              <Shield className="h-8 w-8 text-primary-500" />
              <h1 className="text-2xl font-bold text-gradient">Miasma</h1>
            </div>
            <Link
              to="/login"
              className="btn-primary"
            >
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto text-center">
          <h2 className="text-5xl font-bold mb-6 text-gradient">
            Protect Your Digital Privacy
          </h2>
          <p className="text-xl text-gray-300 mb-8 max-w-3xl mx-auto">
            Take control of your personal data by strategically introducing misleading 
            information into commercial data broker networks. Reduce the accuracy of 
            profiles built about you without your consent.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/login" className="btn-primary btn-lg">
              Start Protecting Your Data
            </Link>
            <button className="btn-outline btn-lg">
              Learn How It Works
            </button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gray-900/50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h3 className="text-3xl font-bold mb-4">How Miasma Works</h3>
            <p className="text-gray-300 max-w-2xl mx-auto">
              A comprehensive approach to data privacy through strategic information management
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <div className="card p-6 text-center">
              <Eye className="h-12 w-12 text-primary-500 mx-auto mb-4" />
              <h4 className="text-xl font-semibold mb-3">Data Discovery</h4>
              <p className="text-gray-400">
                Scan major data broker sites to see what personal information 
                is publicly available about you.
              </p>
            </div>
            
            <div className="card p-6 text-center">
              <Zap className="h-12 w-12 text-primary-500 mx-auto mb-4" />
              <h4 className="text-xl font-semibold mb-3">Strategic Injection</h4>
              <p className="text-gray-400">
                Generate realistic but false information and strategically 
                submit it to reduce data accuracy.
              </p>
            </div>
            
            <div className="card p-6 text-center">
              <Database className="h-12 w-12 text-primary-500 mx-auto mb-4" />
              <h4 className="text-xl font-semibold mb-3">Campaign Management</h4>
              <p className="text-gray-400">
                Track and manage your data poisoning campaigns with 
                detailed analytics and success metrics.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Privacy Notice */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 border-t border-gray-800">
        <div className="max-w-4xl mx-auto text-center">
          <Lock className="h-12 w-12 text-primary-500 mx-auto mb-4" />
          <h3 className="text-2xl font-bold mb-4">Privacy First</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 text-left">
            <div>
              <h4 className="font-semibold mb-2 text-green-400">What We Do</h4>
              <ul className="text-gray-300 space-y-1 text-sm">
                <li>• Target only commercial data brokers</li>
                <li>• Help you protect your own data</li>
                <li>• Respect terms of service</li>
                <li>• Provide transparency in our methods</li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-2 text-red-400">What We Don't Do</h4>
              <ul className="text-gray-300 space-y-1 text-sm">
                <li>• Target government databases</li>
                <li>• Interfere with official records</li>
                <li>• Store your personal information</li>
                <li>• Share data with third parties</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto text-center text-gray-400">
          <p>&copy; 2025 Miasma. Built for personal privacy protection.</p>
          <p className="text-sm mt-2">
            Use responsibly and in compliance with applicable laws.
          </p>
        </div>
      </footer>
    </div>
  )
}