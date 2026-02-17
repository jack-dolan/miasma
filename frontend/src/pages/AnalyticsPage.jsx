import { BarChart3, TrendingUp } from 'lucide-react'

export default function AnalyticsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-100">Analytics</h1>
      <div className="card p-8 text-center">
        <BarChart3 className="h-16 w-16 text-primary-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold mb-2">Campaign Analytics</h2>
        <p className="text-gray-400 mb-6">
          Track the effectiveness of your data protection campaigns with detailed metrics.
        </p>
        <button className="btn-primary">View Reports</button>
      </div>
    </div>
  )
}