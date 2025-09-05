import { Eye, Zap, Database, TrendingUp } from 'lucide-react'

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-100">Dashboard</h1>
        <button className="btn-primary">New Campaign</button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card p-6">
          <div className="flex items-center">
            <div className="p-3 rounded-lg bg-blue-600/20">
              <Eye className="h-6 w-6 text-blue-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-400">Data Sources Found</p>
              <p className="text-2xl font-bold text-gray-100">12</p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center">
            <div className="p-3 rounded-lg bg-green-600/20">
              <Zap className="h-6 w-6 text-green-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-400">Active Campaigns</p>
              <p className="text-2xl font-bold text-gray-100">3</p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center">
            <div className="p-3 rounded-lg bg-purple-600/20">
              <Database className="h-6 w-6 text-purple-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-400">Records Injected</p>
              <p className="text-2xl font-bold text-gray-100">247</p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center">
            <div className="p-3 rounded-lg bg-yellow-600/20">
              <TrendingUp className="h-6 w-6 text-yellow-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-400">Success Rate</p>
              <p className="text-2xl font-bold text-gray-100">84%</p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold text-gray-100">Recent Lookups</h3>
          </div>
          <div className="card-body">
            <div className="space-y-4">
              <div className="flex justify-between items-center py-2">
                <span className="text-gray-300">WhitePages.com</span>
                <span className="status-online">Found Data</span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span className="text-gray-300">Spokeo.com</span>
                <span className="status-online">Found Data</span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span className="text-gray-300">TruePeopleSearch.com</span>
                <span className="status-pending">Scanning...</span>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold text-gray-100">Campaign Status</h3>
          </div>
          <div className="card-body">
            <div className="space-y-4">
              <div className="flex justify-between items-center py-2">
                <span className="text-gray-300">Campaign Alpha</span>
                <span className="status-online">Running</span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span className="text-gray-300">Campaign Beta</span>
                <span className="status-pending">Scheduled</span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span className="text-gray-300">Campaign Gamma</span>
                <span className="status-offline">Completed</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}