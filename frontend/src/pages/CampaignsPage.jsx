import { Zap, Plus } from 'lucide-react'

export default function CampaignsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-100">Campaigns</h1>
        <button className="btn-primary flex items-center">
          <Plus className="h-4 w-4 mr-2" />
          New Campaign
        </button>
      </div>
      <div className="card p-8 text-center">
        <Zap className="h-16 w-16 text-primary-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold mb-2">Data Poisoning Campaigns</h2>
        <p className="text-gray-400 mb-6">
          Create and manage strategic data injection campaigns to protect your privacy.
        </p>
        <button className="btn-primary">Create First Campaign</button>
      </div>
    </div>
  )
}
