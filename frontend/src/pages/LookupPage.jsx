import { Search, Globe, Database } from 'lucide-react'

export default function LookupPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-100">Data Lookup</h1>
      <div className="card p-8 text-center">
        <Search className="h-16 w-16 text-primary-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold mb-2">Search Your Digital Footprint</h2>
        <p className="text-gray-400 mb-6">
          Scan major data broker sites to discover what personal information is publicly available about you.
        </p>
        <button className="btn-primary">Start Lookup</button>
      </div>
    </div>
  )
}