import { useState, useEffect } from 'react'
import { BarChart3, Search, Zap, Database } from 'lucide-react'
import { analyticsApi } from '../services/api'

export default function AnalyticsPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const result = await analyticsApi.getDashboard()
        setData(result)
      } catch (err) {
        console.error('Failed to load analytics:', err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner h-8 w-8"></div>
      </div>
    )
  }

  const stats = data || {}

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-100">Analytics</h1>

      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card p-6">
          <div className="flex items-center mb-3">
            <Search className="h-5 w-5 text-blue-400 mr-2" />
            <h3 className="text-sm font-medium text-gray-400">Total Lookups</h3>
          </div>
          <p className="text-3xl font-bold text-gray-100">{stats.total_lookups || 0}</p>
          <p className="text-sm text-gray-500 mt-1">
            {stats.total_records || 0} records found
          </p>
        </div>

        <div className="card p-6">
          <div className="flex items-center mb-3">
            <Zap className="h-5 w-5 text-green-400 mr-2" />
            <h3 className="text-sm font-medium text-gray-400">Campaign Activity</h3>
          </div>
          <p className="text-3xl font-bold text-gray-100">{stats.active_campaigns || 0}</p>
          <p className="text-sm text-gray-500 mt-1">active campaigns</p>
        </div>

        <div className="card p-6">
          <div className="flex items-center mb-3">
            <Database className="h-5 w-5 text-purple-400 mr-2" />
            <h3 className="text-sm font-medium text-gray-400">Data Sources</h3>
          </div>
          <p className="text-3xl font-bold text-gray-100">{stats.sources_found || 0}</p>
          <p className="text-sm text-gray-500 mt-1">unique sources with data</p>
        </div>
      </div>

      {/* Submission stats */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">Submission Overview</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div>
            <p className="text-sm text-gray-400">Total Submitted</p>
            <p className="text-2xl font-bold text-gray-100">{stats.total_submissions || 0}</p>
          </div>
          <div>
            <p className="text-sm text-gray-400">Success Rate</p>
            <p className="text-2xl font-bold text-gray-100">{stats.success_rate || 0}%</p>
          </div>
          <div>
            <p className="text-sm text-gray-400">Total Lookups</p>
            <p className="text-2xl font-bold text-gray-100">{stats.total_lookups || 0}</p>
          </div>
          <div>
            <p className="text-sm text-gray-400">Records Found</p>
            <p className="text-2xl font-bold text-gray-100">{stats.total_records || 0}</p>
          </div>
        </div>
      </div>

      {/* Recent activity */}
      {stats.recent_lookups && stats.recent_lookups.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold text-gray-100">Recent Lookup Activity</h3>
          </div>
          <div className="card-body">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-400 border-b border-gray-800">
                    <th className="text-left py-2">Name</th>
                    <th className="text-left py-2">Sources</th>
                    <th className="text-left py-2">Records</th>
                    <th className="text-left py-2">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.recent_lookups.map((lookup) => (
                    <tr key={lookup.id} className="border-b border-gray-800/50">
                      <td className="py-2 text-gray-300">{lookup.name}</td>
                      <td className="py-2 text-gray-400">{lookup.sources_searched}</td>
                      <td className="py-2 text-gray-400">{lookup.records_found}</td>
                      <td className="py-2 text-gray-500">
                        {lookup.created_at ? new Date(lookup.created_at).toLocaleDateString() : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
