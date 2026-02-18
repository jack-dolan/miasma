import { useState, useEffect, useCallback, useRef } from 'react'
import { Zap, Plus, Trash2, Play, Pause, RotateCcw, X, ChevronDown, ChevronUp, Filter, Eye, Users, AlertCircle, Loader2, Shield, Activity, Clock, TrendingDown, TrendingUp, CheckCircle2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { campaignApi, generateApi } from '../services/api'

const STATUS_COLORS = {
  draft: 'bg-gray-600/30 text-gray-300',
  scheduled: 'bg-yellow-600/30 text-yellow-300',
  running: 'bg-green-600/30 text-green-300',
  paused: 'bg-orange-600/30 text-orange-300',
  completed: 'bg-blue-600/30 text-blue-300',
  failed: 'bg-red-600/30 text-red-300',
}

const SUBMISSION_STATUS_COLORS = {
  pending: 'bg-gray-600/30 text-gray-300',
  submitted: 'bg-blue-600/30 text-blue-300',
  confirmed: 'bg-green-600/30 text-green-300',
  failed: 'bg-red-600/30 text-red-300',
  skipped: 'bg-yellow-600/30 text-yellow-300',
}

const US_STATES = [
  '', 'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
  'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
  'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
  'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
  'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
]

const TARGET_SITES = [
  { key: 'aboutme', label: 'About.me' },
  { key: 'gravatar', label: 'Gravatar' },
  { key: 'linktree', label: 'Linktree' },
  { key: 'directory', label: 'Directories' },
  { key: 'marketing', label: 'Marketing/Surveys' },
  { key: 'manual', label: 'Manual Instructions' },
]

function CreateModal({ onClose, onCreated }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [targetCount, setTargetCount] = useState(10)
  const [targetFirstName, setTargetFirstName] = useState('')
  const [targetLastName, setTargetLastName] = useState('')
  const [targetCity, setTargetCity] = useState('')
  const [targetState, setTargetState] = useState('')
  const [targetAge, setTargetAge] = useState('')
  const [selectedSites, setSelectedSites] = useState([])
  const [saving, setSaving] = useState(false)

  const toggleSite = (key) => {
    setSelectedSites((prev) =>
      prev.includes(key) ? prev.filter((s) => s !== key) : [...prev, key]
    )
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!name.trim() || !targetFirstName.trim() || !targetLastName.trim()) return

    setSaving(true)
    try {
      await campaignApi.create({
        name,
        description,
        targetCount,
        targetFirstName: targetFirstName.trim(),
        targetLastName: targetLastName.trim(),
        targetCity: targetCity.trim() || null,
        targetState: targetState || null,
        targetAge: targetAge ? parseInt(targetAge) : null,
        targetSites: selectedSites.length > 0 ? selectedSites : null,
      })
      toast.success('Campaign created')
      onCreated()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create campaign')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 overflow-y-auto py-8">
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-6 w-full max-w-lg mx-4">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-gray-100">New Campaign</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-200">
            <X className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Campaign info */}
          <div className="space-y-3">
            <div>
              <label className="label">Campaign Name</label>
              <input
                type="text"
                className="input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Q1 Privacy Shield"
                required
              />
            </div>
            <div>
              <label className="label">Description</label>
              <textarea
                className="input"
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What is this campaign for?"
              />
            </div>
          </div>

          {/* Target identity */}
          <div>
            <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center">
              <Shield className="h-4 w-4 mr-1.5 text-blue-400" />
              Who to protect
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">First Name *</label>
                <input
                  type="text"
                  className="input"
                  value={targetFirstName}
                  onChange={(e) => setTargetFirstName(e.target.value)}
                  placeholder="Joe"
                  required
                />
              </div>
              <div>
                <label className="label">Last Name *</label>
                <input
                  type="text"
                  className="input"
                  value={targetLastName}
                  onChange={(e) => setTargetLastName(e.target.value)}
                  placeholder="Smith"
                  required
                />
              </div>
              <div>
                <label className="label">City</label>
                <input
                  type="text"
                  className="input"
                  value={targetCity}
                  onChange={(e) => setTargetCity(e.target.value)}
                  placeholder="Denver"
                />
              </div>
              <div>
                <label className="label">State</label>
                <select
                  className="input"
                  value={targetState}
                  onChange={(e) => setTargetState(e.target.value)}
                >
                  <option value="">Any</option>
                  {US_STATES.filter(Boolean).map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Age</label>
                <input
                  type="number"
                  className="input"
                  min={18}
                  max={120}
                  value={targetAge}
                  onChange={(e) => setTargetAge(e.target.value)}
                  placeholder="35"
                />
              </div>
              <div>
                <label className="label">Target Submissions</label>
                <input
                  type="number"
                  className="input"
                  min={1}
                  max={100}
                  value={targetCount}
                  onChange={(e) => setTargetCount(parseInt(e.target.value) || 10)}
                />
              </div>
            </div>
          </div>

          {/* Target sites */}
          <div>
            <h3 className="text-sm font-medium text-gray-300 mb-3">Target Sites</h3>
            <div className="grid grid-cols-2 gap-2">
              {TARGET_SITES.map((site) => (
                <label
                  key={site.key}
                  className={`flex items-center space-x-2 p-2 rounded border cursor-pointer transition-colors ${
                    selectedSites.includes(site.key)
                      ? 'border-blue-500 bg-blue-900/20'
                      : 'border-gray-700 hover:border-gray-600'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedSites.includes(site.key)}
                    onChange={() => toggleSite(site.key)}
                    className="rounded border-gray-600 bg-gray-800 text-blue-500 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-300">{site.label}</span>
                </label>
              ))}
            </div>
            {selectedSites.length === 0 && (
              <p className="text-xs text-gray-500 mt-1">Leave empty to target all available sites</p>
            )}
          </div>

          <div className="flex justify-end space-x-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || !targetFirstName.trim() || !targetLastName.trim()}
              className="btn-primary"
            >
              {saving ? 'Creating...' : 'Create Campaign'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function ProgressBar({ completed, failed, total }) {
  const processed = completed + failed
  const pctDone = total > 0 ? Math.round((completed / total) * 100) : 0
  const pctFailed = total > 0 ? Math.round((failed / total) * 100) : 0
  const pctProcessed = total > 0 ? Math.round((processed / total) * 100) : 0

  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-gray-400 mb-1">
        <span>{processed} / {total} processed</span>
        <span>{pctProcessed}%</span>
      </div>
      <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
        <div className="h-full flex">
          <div
            className="bg-green-500 transition-all duration-500"
            style={{ width: `${pctDone}%` }}
          />
          <div
            className="bg-red-500 transition-all duration-500"
            style={{ width: `${pctFailed}%` }}
          />
        </div>
      </div>
      {failed > 0 && (
        <p className="text-xs text-red-400 mt-1">{failed} failed</p>
      )}
    </div>
  )
}

function SubmissionsPanel({ campaignId, isRunning }) {
  const [submissions, setSubmissions] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState('')
  const [expandedId, setExpandedId] = useState(null)

  const loadSubmissions = useCallback(async () => {
    try {
      const data = await campaignApi.getSubmissions(campaignId, {
        page,
        pageSize: 15,
        status: statusFilter || undefined,
      })
      setSubmissions(data.items)
      setTotalPages(data.pages)
      setTotal(data.total)
    } catch (err) {
      console.error('Failed to load submissions:', err)
    } finally {
      setLoading(false)
    }
  }, [campaignId, page, statusFilter])

  useEffect(() => {
    setLoading(true)
    loadSubmissions()
  }, [loadSubmissions])

  useEffect(() => {
    if (!isRunning) return
    const interval = setInterval(loadSubmissions, 7000)
    return () => clearInterval(interval)
  }, [isRunning, loadSubmissions])

  if (loading && submissions.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="spinner h-6 w-6" />
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-gray-300">
          Submissions ({total})
        </h4>
        <div className="flex items-center space-x-2">
          <Filter className="h-3 w-3 text-gray-500" />
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
            className="bg-gray-800 border border-gray-600 rounded text-xs text-gray-300 px-2 py-1"
          >
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="submitted">Submitted</option>
            <option value="confirmed">Confirmed</option>
            <option value="failed">Failed</option>
            <option value="skipped">Skipped</option>
          </select>
        </div>
      </div>

      {submissions.length === 0 ? (
        <p className="text-gray-500 text-sm text-center py-4">No submissions yet</p>
      ) : (
        <div className="space-y-2">
          {submissions.map((sub) => (
            <div key={sub.id} className="border border-gray-700 rounded-lg">
              <div
                className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-800/50"
                onClick={() => setExpandedId(expandedId === sub.id ? null : sub.id)}
              >
                <div className="flex items-center space-x-3 min-w-0">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap ${SUBMISSION_STATUS_COLORS[sub.status] || ''}`}>
                    {sub.status}
                  </span>
                  <span className="text-sm text-gray-300 truncate">
                    {sub.site}
                  </span>
                  {sub.profile_data && (
                    <span className="text-sm text-gray-500 truncate hidden md:inline">
                      {sub.profile_data.first_name} {sub.profile_data.last_name}
                    </span>
                  )}
                </div>
                <div className="flex items-center space-x-3">
                  {sub.submitted_at && (
                    <span className="text-xs text-gray-500 hidden sm:inline">
                      {new Date(sub.submitted_at).toLocaleString()}
                    </span>
                  )}
                  {sub.error_message && (
                    <AlertCircle className="h-3.5 w-3.5 text-red-400" />
                  )}
                  {expandedId === sub.id ? (
                    <ChevronUp className="h-4 w-4 text-gray-500" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-gray-500" />
                  )}
                </div>
              </div>

              {expandedId === sub.id && (
                <div className="border-t border-gray-700 p-3 space-y-2">
                  {sub.error_message && (
                    <div className="bg-red-900/20 border border-red-800 rounded p-2">
                      <p className="text-xs text-red-400">{sub.error_message}</p>
                    </div>
                  )}
                  {sub.reference_id && (
                    <p className="text-xs text-gray-400">
                      Ref: <span className="text-gray-300">{sub.reference_id}</span>
                    </p>
                  )}
                  {sub.profile_data && (
                    <div>
                      <p className="text-xs text-gray-400 mb-1">Profile Data:</p>
                      <div className="bg-gray-900 rounded p-3 text-xs font-mono text-gray-300 overflow-x-auto">
                        {Object.entries(sub.profile_data).map(([key, val]) => (
                          <div key={key} className="flex">
                            <span className="text-gray-500 w-28 shrink-0">{key}:</span>
                            <span>{typeof val === 'object' ? JSON.stringify(val) : String(val)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  <p className="text-xs text-gray-500">
                    Created: {new Date(sub.created_at).toLocaleString()}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center space-x-4 pt-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn-secondary btn-sm disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-gray-400 text-xs">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= totalPages}
            className="btn-secondary btn-sm disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}

function AccuracyPanel({ campaignId, status }) {
  const [baselines, setBaselines] = useState([])
  const [accuracy, setAccuracy] = useState(null)
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState(false)

  const loadData = useCallback(async () => {
    try {
      const [baselineData, accuracyData] = await Promise.allSettled([
        campaignApi.getBaselines(campaignId),
        campaignApi.getAccuracy(campaignId),
      ])
      if (baselineData.status === 'fulfilled') {
        setBaselines(Array.isArray(baselineData.value) ? baselineData.value : baselineData.value?.items || [])
      }
      if (accuracyData.status === 'fulfilled') {
        setAccuracy(accuracyData.value)
      }
    } catch {
      // endpoints may not exist yet, that's ok
    } finally {
      setLoading(false)
    }
  }, [campaignId])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleBaseline = async () => {
    setActing(true)
    try {
      await campaignApi.takeBaseline(campaignId)
      toast.success('Baseline snapshot complete')
      await loadData()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to take baseline')
    } finally {
      setActing(false)
    }
  }

  const handleCheck = async () => {
    setActing(true)
    try {
      await campaignApi.takeCheck(campaignId)
      toast.success('Accuracy check started')
      await loadData()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to run check')
    } finally {
      setActing(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-4">
        <div className="spinner h-5 w-5" />
      </div>
    )
  }

  const hasBaseline = baselines.length > 0
  const canCheck = hasBaseline && (status === 'completed' || status === 'running' || status === 'paused')
  const baselineScore = accuracy?.baseline_score
  const latestScore = accuracy?.latest_score
  const scoreDelta = baselineScore != null && latestScore != null ? latestScore - baselineScore : null

  return (
    <div className="space-y-4">
      <h4 className="text-sm font-medium text-gray-300 flex items-center">
        <Activity className="h-4 w-4 mr-1.5 text-purple-400" />
        Accuracy Tracking
      </h4>

      {/* Action buttons */}
      <div className="flex flex-wrap gap-2">
        {!hasBaseline && status === 'draft' && (
          <button
            onClick={handleBaseline}
            disabled={acting}
            className="btn-secondary btn-sm flex items-center"
          >
            {acting ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <Eye className="h-3.5 w-3.5 mr-1.5" />}
            Take Baseline
          </button>
        )}
        {canCheck && (
          <button
            onClick={handleCheck}
            disabled={acting}
            className="btn-secondary btn-sm flex items-center"
          >
            {acting ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" />}
            Run Check
          </button>
        )}
      </div>

      {/* Accuracy scores */}
      {accuracy && (baselineScore != null || latestScore != null) && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {baselineScore != null && (
            <div className="bg-gray-800 rounded-lg p-3">
              <p className="text-xs text-gray-500 mb-1">Baseline</p>
              <p className="text-lg font-semibold text-gray-200">{(baselineScore * 100).toFixed(1)}%</p>
              {accuracy.baseline_date && (
                <p className="text-xs text-gray-500 mt-1">
                  {new Date(accuracy.baseline_date).toLocaleDateString()}
                </p>
              )}
            </div>
          )}
          {latestScore != null && (
            <div className="bg-gray-800 rounded-lg p-3">
              <p className="text-xs text-gray-500 mb-1">Latest Check</p>
              <p className="text-lg font-semibold text-gray-200">{(latestScore * 100).toFixed(1)}%</p>
              {accuracy.latest_date && (
                <p className="text-xs text-gray-500 mt-1">
                  {new Date(accuracy.latest_date).toLocaleDateString()}
                </p>
              )}
            </div>
          )}
          {scoreDelta != null && (
            <div className="bg-gray-800 rounded-lg p-3">
              <p className="text-xs text-gray-500 mb-1">Change</p>
              <div className="flex items-center space-x-1">
                {scoreDelta < 0 ? (
                  <TrendingDown className="h-4 w-4 text-green-400" />
                ) : scoreDelta > 0 ? (
                  <TrendingUp className="h-4 w-4 text-red-400" />
                ) : null}
                <p className={`text-lg font-semibold ${
                  scoreDelta < 0 ? 'text-green-400' : scoreDelta > 0 ? 'text-red-400' : 'text-gray-400'
                }`}>
                  {scoreDelta > 0 ? '+' : ''}{(scoreDelta * 100).toFixed(1)}%
                </p>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {scoreDelta < 0 ? 'Accuracy dropped (good)' : scoreDelta > 0 ? 'Accuracy rose (bad)' : 'No change'}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Snapshot timeline */}
      {baselines.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 mb-2">Snapshots</p>
          <div className="space-y-1.5">
            {baselines.map((bl) => (
              <div key={bl.id} className="flex items-center justify-between text-xs bg-gray-800/50 rounded px-3 py-2">
                <div className="flex items-center space-x-2">
                  <Clock className="h-3 w-3 text-gray-500" />
                  <span className="text-gray-400">
                    {new Date(bl.created_at).toLocaleString()}
                  </span>
                  <span className={`px-1.5 py-0.5 rounded text-xs ${
                    bl.snapshot_type === 'baseline' ? 'bg-blue-900/30 text-blue-300' : 'bg-purple-900/30 text-purple-300'
                  }`}>
                    {bl.snapshot_type || 'baseline'}
                  </span>
                </div>
                {bl.accuracy_score != null && (
                  <span className="text-gray-300 font-medium">
                    {(bl.accuracy_score * 100).toFixed(1)}%
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {!hasBaseline && status !== 'draft' && (
        <p className="text-xs text-gray-500">No baseline was taken before this campaign started.</p>
      )}
    </div>
  )
}

function ProfileCard({ profile }) {
  return (
    <div className="border border-gray-700 rounded-lg p-4 space-y-2">
      <p className="font-medium text-gray-100">
        {profile.first_name} {profile.middle_name ? profile.middle_name + ' ' : ''}{profile.last_name}
      </p>

      {profile.date_of_birth && (
        <p className="text-sm text-gray-400">DOB: {profile.date_of_birth}</p>
      )}
      {profile.gender && (
        <p className="text-sm text-gray-400">Gender: {profile.gender}</p>
      )}

      {profile.addresses?.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Addresses</p>
          {profile.addresses.map((a, i) => (
            <p key={i} className="text-sm text-gray-400">
              {[a.street, a.city, a.state, a.zip].filter(Boolean).join(', ')}
            </p>
          ))}
        </div>
      )}

      {profile.phone_numbers?.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Phones</p>
          {profile.phone_numbers.map((p, i) => (
            <p key={i} className="text-sm text-gray-400">
              {p.number}{p.type ? ` (${p.type})` : ''}
            </p>
          ))}
        </div>
      )}

      {profile.emails?.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Emails</p>
          <p className="text-sm text-gray-400 truncate">{profile.emails.join(', ')}</p>
        </div>
      )}

      {profile.employment && (profile.employment.title || profile.employment.employer) && (
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Employment</p>
          <p className="text-sm text-gray-400">
            {[profile.employment.title, profile.employment.employer].filter(Boolean).join(' at ')}
          </p>
        </div>
      )}

      {profile.relatives?.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Relatives</p>
          <div className="flex flex-wrap gap-1">
            {profile.relatives.map((r, i) => (
              <span key={i} className="text-xs bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded">
                {r.first_name} {r.last_name}{r.relationship ? ` (${r.relationship})` : ''}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function PreviewPanel() {
  const [count, setCount] = useState(5)
  const [targetFirstName, setTargetFirstName] = useState('')
  const [targetLastName, setTargetLastName] = useState('')
  const [state, setState] = useState('')
  const [targetAge, setTargetAge] = useState('')
  const [profiles, setProfiles] = useState([])
  const [loading, setLoading] = useState(false)

  const handleGenerate = async () => {
    setLoading(true)
    try {
      const data = await generateApi.preview({
        count,
        targetFirstName: targetFirstName.trim() || null,
        targetLastName: targetLastName.trim() || null,
        targetState: state || null,
        targetAge: targetAge ? parseInt(targetAge) : null,
      })
      setProfiles(data.profiles)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to generate preview')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="text-lg font-semibold text-gray-100 flex items-center">
          <Users className="h-5 w-5 mr-2 text-purple-400" />
          Preview Fake Profiles
        </h3>
        <p className="text-sm text-gray-400 mt-1">
          See what kind of poisoned data will be generated. Enter a name to see profiles
          that share that identity (how poisoning mode works).
        </p>
      </div>
      <div className="card-body space-y-4">
        {/* Target name for poisoning preview */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Target First Name</label>
            <input
              type="text"
              className="input"
              value={targetFirstName}
              onChange={(e) => setTargetFirstName(e.target.value)}
              placeholder="Joe"
            />
          </div>
          <div>
            <label className="label">Target Last Name</label>
            <input
              type="text"
              className="input"
              value={targetLastName}
              onChange={(e) => setTargetLastName(e.target.value)}
              placeholder="Smith"
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="label">Count</label>
            <input
              type="number"
              className="input"
              min={1}
              max={20}
              value={count}
              onChange={(e) => setCount(parseInt(e.target.value) || 5)}
            />
          </div>
          <div>
            <label className="label">State</label>
            <select
              className="input"
              value={state}
              onChange={(e) => setState(e.target.value)}
            >
              <option value="">Any</option>
              {US_STATES.filter(Boolean).map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Age</label>
            <input
              type="number"
              className="input"
              min={18}
              max={120}
              placeholder="35"
              value={targetAge}
              onChange={(e) => setTargetAge(e.target.value)}
            />
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={loading}
          className="btn-primary flex items-center"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Eye className="h-4 w-4 mr-2" />
              Generate Preview
            </>
          )}
        </button>

        {profiles.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {profiles.map((profile, idx) => (
              <ProfileCard key={idx} profile={profile} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function CampaignCard({ campaign, onRefresh }) {
  const [expanded, setExpanded] = useState(false)
  const [showAccuracy, setShowAccuracy] = useState(false)
  const [acting, setActing] = useState(false)
  const pollRef = useRef(null)
  const [live, setLive] = useState(campaign)

  // poll for updates while running
  useEffect(() => {
    if (live.status !== 'running') {
      if (pollRef.current) clearInterval(pollRef.current)
      return
    }

    pollRef.current = setInterval(async () => {
      try {
        const fresh = await campaignApi.get(live.id)
        setLive(fresh)
        if (fresh.status !== 'running') {
          clearInterval(pollRef.current)
          onRefresh()
        }
      } catch {
        // ignore polling errors
      }
    }, 8000)

    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [live.status, live.id, onRefresh])

  // sync from parent
  useEffect(() => {
    setLive(campaign)
  }, [campaign])

  const handleExecute = async () => {
    setActing(true)
    try {
      await campaignApi.execute(live.id)
      toast.success('Campaign started')
      const fresh = await campaignApi.get(live.id)
      setLive(fresh)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to start campaign')
    } finally {
      setActing(false)
    }
  }

  const handlePause = async () => {
    setActing(true)
    try {
      await campaignApi.pause(live.id)
      toast.success('Campaign paused')
      const fresh = await campaignApi.get(live.id)
      setLive(fresh)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to pause campaign')
    } finally {
      setActing(false)
    }
  }

  const handleResume = async () => {
    setActing(true)
    try {
      await campaignApi.resume(live.id)
      toast.success('Campaign resumed')
      const fresh = await campaignApi.get(live.id)
      setLive(fresh)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to resume campaign')
    } finally {
      setActing(false)
    }
  }

  const handleReset = async () => {
    if (!confirm('Reset this campaign back to draft?')) return
    setActing(true)
    try {
      await campaignApi.update(live.id, { status: 'draft' })
      toast.success('Campaign reset to draft')
      const fresh = await campaignApi.get(live.id)
      setLive(fresh)
      onRefresh()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reset campaign')
    } finally {
      setActing(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm('Delete this campaign?')) return
    try {
      await campaignApi.delete(live.id)
      toast.success('Campaign deleted')
      onRefresh()
    } catch {
      toast.error('Failed to delete campaign')
    }
  }

  const isRunning = live.status === 'running'

  // Build target identity string
  const targetParts = []
  if (live.target_first_name || live.target_last_name) {
    targetParts.push([live.target_first_name, live.target_last_name].filter(Boolean).join(' '))
  }
  if (live.target_city || live.target_state) {
    targetParts.push([live.target_city, live.target_state].filter(Boolean).join(', '))
  }
  if (live.target_age) {
    targetParts.push(`age ${live.target_age}`)
  }
  const targetLabel = targetParts.length > 0 ? targetParts.join(' \u00b7 ') : null

  return (
    <div className="card">
      <div className="p-5">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-3 mb-1">
              <h3 className="text-lg font-semibold text-gray-100 truncate">
                {live.name}
              </h3>
              <span className={`px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap ${STATUS_COLORS[live.status] || STATUS_COLORS.draft}`}>
                {live.status}
                {isRunning && (
                  <span className="inline-block w-1.5 h-1.5 bg-green-400 rounded-full ml-1.5 animate-pulse" />
                )}
              </span>
            </div>

            {/* Target identity */}
            {targetLabel && (
              <p className="text-sm text-blue-400 mb-1 flex items-center">
                <Shield className="h-3.5 w-3.5 mr-1.5 shrink-0" />
                Protecting: {targetLabel}
              </p>
            )}

            {live.description && (
              <p className="text-sm text-gray-400 mb-2">{live.description}</p>
            )}

            <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-gray-500">
              <span>Target: {live.target_count} submissions</span>
            </div>

            {/* Target site badges */}
            {live.target_sites?.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {live.target_sites.map((site) => {
                  const info = TARGET_SITES.find((s) => s.key === site)
                  return (
                    <span
                      key={site}
                      className="px-2 py-0.5 bg-gray-700/50 text-gray-400 text-xs rounded"
                    >
                      {info?.label || site}
                    </span>
                  )
                })}
              </div>
            )}

            {/* progress bar */}
            <div className="mt-3 max-w-md">
              <ProgressBar
                completed={live.submissions_completed || 0}
                failed={live.submissions_failed || 0}
                total={(live.target_count || 1) * (live.target_sites?.length || 1)}
              />
            </div>
          </div>

          <div className="flex items-center space-x-1 ml-4 shrink-0">
            {live.status === 'draft' && (
              <button
                onClick={handleExecute}
                disabled={acting}
                className="p-2 text-green-400 hover:bg-green-900/30 rounded"
                title="Start campaign"
              >
                <Play className="h-4 w-4" />
              </button>
            )}
            {live.status === 'running' && (
              <button
                onClick={handlePause}
                disabled={acting}
                className="p-2 text-yellow-400 hover:bg-yellow-900/30 rounded"
                title="Pause campaign"
              >
                <Pause className="h-4 w-4" />
              </button>
            )}
            {live.status === 'paused' && (
              <button
                onClick={handleResume}
                disabled={acting}
                className="p-2 text-green-400 hover:bg-green-900/30 rounded"
                title="Resume campaign"
              >
                <Play className="h-4 w-4" />
              </button>
            )}
            {(live.status === 'completed' || live.status === 'failed') && (
              <button
                onClick={handleReset}
                disabled={acting}
                className="p-2 text-blue-400 hover:bg-blue-900/30 rounded"
                title="Reset to draft"
              >
                <RotateCcw className="h-4 w-4" />
              </button>
            )}
            <button
              onClick={() => setShowAccuracy(!showAccuracy)}
              className={`p-2 rounded ${showAccuracy ? 'text-purple-400 bg-purple-900/20' : 'text-gray-400 hover:bg-gray-700'}`}
              title="Accuracy tracking"
            >
              <Activity className="h-4 w-4" />
            </button>
            <button
              onClick={() => setExpanded(!expanded)}
              className="p-2 text-gray-400 hover:bg-gray-700 rounded"
              title={expanded ? 'Collapse' : 'View submissions'}
            >
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
            <button
              onClick={handleDelete}
              className="p-2 text-red-400 hover:bg-red-900/30 rounded"
              title="Delete campaign"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Accuracy panel */}
      {showAccuracy && (
        <div className="border-t border-gray-700 p-5">
          <AccuracyPanel campaignId={live.id} status={live.status} />
        </div>
      )}

      {/* Submissions panel */}
      {expanded && (
        <div className="border-t border-gray-700 p-5">
          <SubmissionsPanel campaignId={live.id} isRunning={isRunning} />
        </div>
      )}
    </div>
  )
}

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [activeTab, setActiveTab] = useState('campaigns')

  const loadCampaigns = useCallback(async () => {
    try {
      const data = await campaignApi.list()
      setCampaigns(data.items)
    } catch {
      toast.error('Failed to load campaigns')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadCampaigns()
  }, [loadCampaigns])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner h-8 w-8" />
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

      {/* Tabs */}
      <div className="flex space-x-1 bg-gray-800 p-1 rounded-lg w-fit">
        <button
          onClick={() => setActiveTab('campaigns')}
          className={`px-4 py-2 rounded-md flex items-center space-x-2 transition-colors ${
            activeTab === 'campaigns'
              ? 'bg-blue-600 text-white'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          <Zap className="h-4 w-4" />
          <span>Campaigns</span>
          {campaigns.length > 0 && (
            <span className="bg-gray-700 text-gray-300 text-xs px-2 py-0.5 rounded-full">
              {campaigns.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('preview')}
          className={`px-4 py-2 rounded-md flex items-center space-x-2 transition-colors ${
            activeTab === 'preview'
              ? 'bg-blue-600 text-white'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          <Users className="h-4 w-4" />
          <span>Data Preview</span>
        </button>
      </div>

      {activeTab === 'campaigns' && (
        <>
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
                <CampaignCard
                  key={campaign.id}
                  campaign={campaign}
                  onRefresh={loadCampaigns}
                />
              ))}
            </div>
          )}
        </>
      )}

      {activeTab === 'preview' && <PreviewPanel />}

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
