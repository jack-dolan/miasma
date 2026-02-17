import { useState, useEffect } from 'react'
import { Search, Loader2, AlertCircle, CheckCircle2, History, ExternalLink, Trash2, ChevronDown, ChevronUp } from 'lucide-react'
import { lookupApi } from '../services/api'

export default function LookupPage() {
  const [activeTab, setActiveTab] = useState('search') // 'search' or 'history'
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    city: '',
    state: '',
    age: ''
  })
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)

  // History state
  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyPage, setHistoryPage] = useState(1)
  const [historyTotal, setHistoryTotal] = useState(0)
  const [expandedResult, setExpandedResult] = useState(null)

  // Load history when tab changes
  useEffect(() => {
    if (activeTab === 'history') {
      loadHistory()
    }
  }, [activeTab, historyPage])

  const loadHistory = async () => {
    setHistoryLoading(true)
    try {
      const data = await lookupApi.getResults({ page: historyPage, pageSize: 10 })
      setHistory(data.items)
      setHistoryTotal(data.total)
    } catch (err) {
      console.error('Failed to load history:', err)
    } finally {
      setHistoryLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const response = await lookupApi.search({
        firstName: formData.first_name,
        lastName: formData.last_name,
        city: formData.city,
        state: formData.state,
        age: formData.age
      })

      setResults(response)
    } catch (err) {
      setError(err.response?.data?.detail || 'Search failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const handleDeleteResult = async (id) => {
    if (!confirm('Are you sure you want to delete this result?')) return

    try {
      await lookupApi.deleteResult(id)
      setHistory(history.filter(h => h.id !== id))
      setHistoryTotal(prev => prev - 1)
    } catch (err) {
      console.error('Failed to delete:', err)
    }
  }

  const handleViewResult = async (id) => {
    if (expandedResult?.id === id) {
      setExpandedResult(null)
      return
    }

    try {
      const data = await lookupApi.getResult(id)
      setExpandedResult(data)
    } catch (err) {
      console.error('Failed to load result:', err)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-100">Data Lookup</h1>
        <p className="text-gray-400 mt-2">Search for personal information across data broker sites</p>
      </div>

      {/* Tabs */}
      <div className="flex space-x-1 bg-gray-800 p-1 rounded-lg w-fit">
        <button
          onClick={() => setActiveTab('search')}
          className={`px-4 py-2 rounded-md flex items-center space-x-2 transition-colors ${
            activeTab === 'search'
              ? 'bg-blue-600 text-white'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          <Search className="h-4 w-4" />
          <span>New Search</span>
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={`px-4 py-2 rounded-md flex items-center space-x-2 transition-colors ${
            activeTab === 'history'
              ? 'bg-blue-600 text-white'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          <History className="h-4 w-4" />
          <span>Search History</span>
          {historyTotal > 0 && (
            <span className="bg-gray-700 text-gray-300 text-xs px-2 py-0.5 rounded-full">
              {historyTotal}
            </span>
          )}
        </button>
      </div>

      {/* Search Tab */}
      {activeTab === 'search' && (
        <>
          {/* Search Form */}
          <div className="card p-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="first_name" className="label">
                    First Name *
                  </label>
                  <input
                    id="first_name"
                    name="first_name"
                    type="text"
                    required
                    value={formData.first_name}
                    onChange={handleChange}
                    className="input"
                    placeholder="John"
                  />
                </div>

                <div>
                  <label htmlFor="last_name" className="label">
                    Last Name *
                  </label>
                  <input
                    id="last_name"
                    name="last_name"
                    type="text"
                    required
                    value={formData.last_name}
                    onChange={handleChange}
                    className="input"
                    placeholder="Doe"
                  />
                </div>

                <div>
                  <label htmlFor="city" className="label">
                    City (Optional)
                  </label>
                  <input
                    id="city"
                    name="city"
                    type="text"
                    value={formData.city}
                    onChange={handleChange}
                    className="input"
                    placeholder="Boston"
                  />
                </div>

                <div>
                  <label htmlFor="state" className="label">
                    State (Optional)
                  </label>
                  <input
                    id="state"
                    name="state"
                    type="text"
                    maxLength={2}
                    value={formData.state}
                    onChange={handleChange}
                    className="input"
                    placeholder="MA"
                  />
                </div>

                <div>
                  <label htmlFor="age" className="label">
                    Age (Optional)
                  </label>
                  <input
                    id="age"
                    name="age"
                    type="number"
                    value={formData.age}
                    onChange={handleChange}
                    className="input"
                    placeholder="30"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full md:w-auto flex items-center justify-center disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Searching...
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4 mr-2" />
                    Search
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Error Display */}
          {error && (
            <div className="card p-4 border-red-600 bg-red-900/20">
              <div className="flex items-center">
                <AlertCircle className="h-5 w-5 text-red-400 mr-3" />
                <p className="text-red-400">{error}</p>
              </div>
            </div>
          )}

          {/* Results Display */}
          {results && (
            <div className="space-y-4">
              <div className="card p-4 bg-green-900/20 border-green-600">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <CheckCircle2 className="h-5 w-5 text-green-400 mr-3" />
                    <div>
                      <p className="text-green-400 font-medium">
                        Search completed: {results.total_records_found} records found
                      </p>
                      <p className="text-gray-400 text-sm">
                        Searched {results.sources_searched} sources, {results.sources_successful} successful
                      </p>
                    </div>
                  </div>
                  {results.lookup_result_id && (
                    <span className="text-gray-400 text-sm">
                      Saved as #{results.lookup_result_id}
                    </span>
                  )}
                </div>
              </div>

              {/* Results by Source */}
              {results.results.map((sourceResult, idx) => (
                <div key={idx} className="card">
                  <div className="card-header flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-gray-100">
                      {sourceResult.source}
                    </h3>
                    {sourceResult.success ? (
                      <span className="status-online">
                        {sourceResult.data.results?.length || 0} results
                      </span>
                    ) : (
                      <span className="status-offline">Failed</span>
                    )}
                  </div>

                  {sourceResult.success && sourceResult.data.results?.length > 0 ? (
                    <div className="card-body space-y-4">
                      {sourceResult.data.results.map((person, personIdx) => (
                        <div key={personIdx} className="border border-gray-700 rounded-lg p-4">
                          <div className="flex items-start justify-between">
                            <h4 className="font-semibold text-gray-100">
                              {person.name}
                              {person.age && <span className="text-gray-400 ml-2">({person.age} years old)</span>}
                            </h4>
                            {person.profile_url && (
                              <a
                                href={person.profile_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-400 hover:text-blue-300 flex items-center text-sm"
                              >
                                View Profile
                                <ExternalLink className="h-3 w-3 ml-1" />
                              </a>
                            )}
                          </div>

                          {person.location && (
                            <p className="text-gray-400 text-sm mt-1">{person.location}</p>
                          )}

                          {person.addresses?.length > 0 && !person.location && (
                            <div className="mt-2">
                              <p className="text-sm text-gray-400">Addresses:</p>
                              <ul className="list-disc list-inside text-gray-300 text-sm">
                                {person.addresses.map((addr, addrIdx) => (
                                  <li key={addrIdx}>{addr}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {person.phone_numbers?.length > 0 && (
                            <div className="mt-2">
                              <p className="text-sm text-gray-400">Phone Numbers:</p>
                              <ul className="list-disc list-inside text-gray-300 text-sm">
                                {person.phone_numbers.map((phone, phoneIdx) => (
                                  <li key={phoneIdx}>{phone}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {person.relatives?.length > 0 && (
                            <div className="mt-2">
                              <p className="text-sm text-gray-400">Relatives:</p>
                              <p className="text-gray-300 text-sm">{person.relatives.join(', ')}</p>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="card-body">
                      <p className="text-gray-400">
                        {sourceResult.success ? 'No results found' : `Error: ${sourceResult.error}`}
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div className="space-y-4">
          {historyLoading ? (
            <div className="card p-8 flex items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-blue-400" />
            </div>
          ) : history.length === 0 ? (
            <div className="card p-8 text-center">
              <History className="h-12 w-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">No search history yet</p>
              <p className="text-gray-500 text-sm mt-1">Your searches will appear here</p>
            </div>
          ) : (
            <>
              {history.map((item) => (
                <div key={item.id} className="card">
                  <div
                    className="card-header flex items-center justify-between cursor-pointer hover:bg-gray-800/50"
                    onClick={() => handleViewResult(item.id)}
                  >
                    <div className="flex items-center space-x-4">
                      <div>
                        <h3 className="text-lg font-semibold text-gray-100">
                          {item.first_name} {item.last_name}
                        </h3>
                        <p className="text-gray-400 text-sm">
                          {item.city && `${item.city}, `}{item.state || 'Any state'}
                          {item.age && ` • Age ${item.age}`}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-4">
                      <div className="text-right">
                        <p className="text-gray-300">{item.total_records_found} records</p>
                        <p className="text-gray-500 text-xs">
                          {new Date(item.created_at).toLocaleDateString()} {new Date(item.created_at).toLocaleTimeString()}
                        </p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDeleteResult(item.id)
                        }}
                        className="p-2 text-gray-400 hover:text-red-400 transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                      {expandedResult?.id === item.id ? (
                        <ChevronUp className="h-5 w-5 text-gray-400" />
                      ) : (
                        <ChevronDown className="h-5 w-5 text-gray-400" />
                      )}
                    </div>
                  </div>

                  {/* Expanded Result Details */}
                  {expandedResult?.id === item.id && (
                    <div className="card-body border-t border-gray-700">
                      {expandedResult.person_records?.length > 0 ? (
                        <div className="space-y-3">
                          {expandedResult.person_records.map((record) => (
                            <div key={record.id} className="border border-gray-700 rounded-lg p-3">
                              <div className="flex items-start justify-between">
                                <div>
                                  <p className="font-medium text-gray-200">{record.name}</p>
                                  {record.age && (
                                    <p className="text-gray-400 text-sm">{record.age} years old</p>
                                  )}
                                  {record.location && (
                                    <p className="text-gray-400 text-sm">{record.location}</p>
                                  )}
                                </div>
                                <div className="flex items-center space-x-2">
                                  <span className="text-xs bg-gray-700 text-gray-300 px-2 py-1 rounded">
                                    {record.source}
                                  </span>
                                  {record.profile_url && (
                                    <a
                                      href={record.profile_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-blue-400 hover:text-blue-300"
                                    >
                                      <ExternalLink className="h-4 w-4" />
                                    </a>
                                  )}
                                </div>
                              </div>
                              {record.phone_numbers?.length > 0 && (
                                <p className="text-gray-400 text-sm mt-2">
                                  Phone: {record.phone_numbers.join(', ')}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-gray-400">No records in this search</p>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {/* Pagination */}
              {historyTotal > 10 && (
                <div className="flex items-center justify-center space-x-4">
                  <button
                    onClick={() => setHistoryPage(p => Math.max(1, p - 1))}
                    disabled={historyPage === 1}
                    className="btn-secondary disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <span className="text-gray-400">
                    Page {historyPage} of {Math.ceil(historyTotal / 10)}
                  </span>
                  <button
                    onClick={() => setHistoryPage(p => p + 1)}
                    disabled={historyPage >= Math.ceil(historyTotal / 10)}
                    className="btn-secondary disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
