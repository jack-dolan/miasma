import { useState, useEffect } from 'react'
import { Zap, Plus, Trash2, Play, Pause, Edit2, X } from 'lucide-react'
import toast from 'react-hot-toast'
import { campaignApi } from '../services/api'

const STATUS_COLORS = {
  draft: 'bg-gray-600/30 text-gray-300',
  scheduled: 'bg-yellow-600/30 text-yellow-300',
  running: 'bg-green-600/30 text-green-300',
  paused: 'bg-orange-600/30 text-orange-300',
  completed: 'bg-blue-600/30 text-blue-300',
  failed: 'bg-red-600/30 text-red-300',
}

function CreateModal({ onClose, onCreated }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [targetCount, setTargetCount] = useState(10)
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!name.trim()) return

    setSaving(true)
    try {
      await campaignApi.create({ name, description, targetCount })
      toast.success('Campaign created')
      onCreated()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create campaign')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-6 w-full max-w-md">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-gray-100">New Campaign</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-200">
            <X className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label">Name</label>
            <input
              type="text"
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. WhitePages Cleanup"
              required
            />
          </div>
          <div>
            <label className="label">Description</label>
            <textarea
              className="input"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this campaign for?"
            />
          </div>
          <div>
            <label className="label">Target submissions</label>
            <input
              type="number"
              className="input"
              min={1}
              max={100}
              value={targetCount}
              onChange={(e) => setTargetCount(parseInt(e.target.value) || 10)}
            />
          </div>
          <div className="flex justify-end space-x-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? 'Creating...' : 'Create Campaign'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)

  const loadCampaigns = async () => {
    try {
      const data = await campaignApi.list()
      setCampaigns(data.items)
    } catch (err) {
      toast.error('Failed to load campaigns')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCampaigns()
  }, [])

  const handleDelete = async (id) => {
    if (!confirm('Delete this campaign?')) return
    try {
      await campaignApi.delete(id)
      toast.success('Campaign deleted')
      loadCampaigns()
    } catch (err) {
      toast.error('Failed to delete campaign')
    }
  }

  const handleStatusChange = async (id, newStatus) => {
    try {
      await campaignApi.update(id, { status: newStatus })
      toast.success(`Campaign ${newStatus}`)
      loadCampaigns()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Status update failed')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner h-8 w-8"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-100">Campaigns</h1>
        <button
          className="btn-primary flex items-center"
          onClick={() => setShowCreate(true)}
        >
          <Plus className="h-4 w-4 mr-2" />
          New Campaign
        </button>
      </div>

      {campaigns.length === 0 ? (
        <div className="card p-8 text-center">
          <Zap className="h-16 w-16 text-primary-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">Data Poisoning Campaigns</h2>
          <p className="text-gray-400 mb-6">
            Create and manage strategic data injection campaigns to protect your privacy.
          </p>
          <button className="btn-primary" onClick={() => setShowCreate(true)}>
            Create First Campaign
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {campaigns.map((campaign) => (
            <div key={campaign.id} className="card p-5">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-1">
                    <h3 className="text-lg font-semibold text-gray-100">
                      {campaign.name}
                    </h3>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[campaign.status] || STATUS_COLORS.draft}`}>
                      {campaign.status}
                    </span>
                  </div>
                  {campaign.description && (
                    <p className="text-sm text-gray-400 mb-2">{campaign.description}</p>
                  )}
                  <div className="flex space-x-6 text-sm text-gray-500">
                    <span>Target: {campaign.target_count} submissions</span>
                    <span>Completed: {campaign.submissions_completed}</span>
                    {campaign.submissions_failed > 0 && (
                      <span className="text-red-400">Failed: {campaign.submissions_failed}</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center space-x-2 ml-4">
                  {campaign.status === 'draft' && (
                    <button
                      onClick={() => handleStatusChange(campaign.id, 'running')}
                      className="p-2 text-green-400 hover:bg-green-900/30 rounded"
                      title="Start campaign"
                    >
                      <Play className="h-4 w-4" />
                    </button>
                  )}
                  {campaign.status === 'running' && (
                    <button
                      onClick={() => handleStatusChange(campaign.id, 'paused')}
                      className="p-2 text-yellow-400 hover:bg-yellow-900/30 rounded"
                      title="Pause campaign"
                    >
                      <Pause className="h-4 w-4" />
                    </button>
                  )}
                  {campaign.status === 'paused' && (
                    <button
                      onClick={() => handleStatusChange(campaign.id, 'running')}
                      className="p-2 text-green-400 hover:bg-green-900/30 rounded"
                      title="Resume campaign"
                    >
                      <Play className="h-4 w-4" />
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(campaign.id)}
                    className="p-2 text-red-400 hover:bg-red-900/30 rounded"
                    title="Delete campaign"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreate && (
        <CreateModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false)
            loadCampaigns()
          }}
        />
      )}
    </div>
  )
}
