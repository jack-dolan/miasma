import { useState } from 'react'
import { Search, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export default function LookupPage() {
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

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const response = await axios.post(`${API_URL}/lookup/search`, {
        first_name: formData.first_name,
        last_name: formData.last_name,
        city: formData.city || null,
        state: formData.state || null,
        age: formData.age ? parseInt(formData.age) : null
      })
      
      setResults(response.data)
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-100">Data Lookup</h1>
        <p className="text-gray-400 mt-2">Search for your personal information across data broker sites</p>
      </div>

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
                      <h4 className="font-semibold text-gray-100 mb-2">
                        {person.name}
                        {person.age && <span className="text-gray-400 ml-2">({person.age} years old)</span>}
                      </h4>

                      {person.addresses?.length > 0 && (
                        <div className="mb-2">
                          <p className="text-sm text-gray-400">Addresses:</p>
                          <ul className="list-disc list-inside text-gray-300 text-sm">
                            {person.addresses.map((addr, addrIdx) => (
                              <li key={addrIdx}>{addr}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {person.phone_numbers?.length > 0 && (
                        <div className="mb-2">
                          <p className="text-sm text-gray-400">Phone Numbers:</p>
                          <ul className="list-disc list-inside text-gray-300 text-sm">
                            {person.phone_numbers.map((phone, phoneIdx) => (
                              <li key={phoneIdx}>{phone}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {person.relatives?.length > 0 && (
                        <div className="mb-2">
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
    </div>
  )
}