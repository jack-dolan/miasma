import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, Zap, Database, TrendingUp } from 'lucide-react'
import { analyticsApi } from '../services/api'

const STATUS_COLORS = {
  draft: 'text-gray-400',
  scheduled: 'status-pending',
  running: 'status-online',
  paused: 'text-yellow-400',
  completed: 'status-offline',
  failed: 'text-red-400',
}

export default function DashboardPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    const load = async () => {
      try {
        const result = await analyticsApi.getDashboard()
        setData(result)
      } catch (err) {
        console.error('Failed to load dashboard:', err)
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

  const stats = data || {
    sources_found: 0,
    active_campaigns: 0,
    total_submissions: 0,
    success_rate: 0,
    recent_lookups: [],
    recent_campaigns: [],
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-100">Dashboard</h1>
        <button className="btn-primary" onClick={() => navigate('/campaigns')}>
          New Campaign
        </button>
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
              <p className="text-2xl font-bold text-gray-100">{stats.sources_found}</p>
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
              <p className="text-2xl font-bold text-gray-100">{stats.active_campaigns}</p>
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
              <p className="text-2xl font-bold text-gray-100">{stats.total_submissions}</p>
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
              <p className="text-2xl font-bold text-gray-100">{stats.success_rate}%</p>
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
            {stats.recent_lookups.length === 0 ? (
              <p className="text-gray-500 text-sm py-4 text-center">No lookups yet</p>
            ) : (
              <div className="space-y-4">
                {stats.recent_lookups.map((lookup) => (
                  <div key={lookup.id} className="flex justify-between items-center py-2">
                    <span className="text-gray-300">{lookup.name}</span>
                    <span className="text-sm text-gray-500">
                      {lookup.records_found} record{lookup.records_found !== 1 ? 's' : ''}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold text-gray-100">Campaign Status</h3>
          </div>
          <div className="card-body">
            {stats.recent_campaigns.length === 0 ? (
              <p className="text-gray-500 text-sm py-4 text-center">No campaigns yet</p>
            ) : (
              <div className="space-y-4">
                {stats.recent_campaigns.map((campaign) => (
                  <div key={campaign.id} className="flex justify-between items-center py-2">
                    <span className="text-gray-300">{campaign.name}</span>
                    <span className={STATUS_COLORS[campaign.status] || 'text-gray-400'}>
                      {campaign.status.charAt(0).toUpperCase() + campaign.status.slice(1)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
