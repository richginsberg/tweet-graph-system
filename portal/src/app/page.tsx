import { fetchStats } from '@/lib/api'
import { Stats } from '@/lib/api'
import Link from 'next/link'

// Force dynamic rendering
export const dynamic = 'force-dynamic'

async function StatCard({ title, value, icon }: { title: string; value: number | string; icon: string }) {
  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-accent text-sm">{title}</p>
          <p className="text-3xl font-bold mt-1">{value}</p>
        </div>
        <span className="text-4xl">{icon}</span>
      </div>
    </div>
  )
}

export default async function Dashboard() {
  let stats: Stats = { tweets: 0, users: 0, hashtags: 0, relationships: 0 }
  
  try {
    stats = await fetchStats()
  } catch (error) {
    console.error('Failed to fetch stats:', error)
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard title="Tweets" value={stats.tweets} icon="🐦" />
        <StatCard title="Users" value={stats.users} icon="👤" />
        <StatCard title="Hashtags" value={stats.hashtags} icon="#️⃣" />
        <StatCard title="Relationships" value={stats.relationships} icon="🔗" />
      </div>

      {stats.embedding_provider && (
        <div className="bg-white p-4 rounded-lg shadow mb-6">
          <h2 className="text-lg font-semibold mb-2">Embedding Provider</h2>
          <p className="text-accent">
            {stats.embedding_provider} / {stats.embedding_model}
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Link href="/graph" className="bg-primary text-white p-6 rounded-lg shadow hover:opacity-90 transition">
          <h2 className="text-xl font-bold">View Graph</h2>
          <p className="mt-2 opacity-80">Explore tweet relationships visually</p>
        </Link>
        
        <Link href="/search" className="bg-secondary text-white p-6 rounded-lg shadow hover:opacity-90 transition">
          <h2 className="text-xl font-bold">Search Tweets</h2>
          <p className="mt-2 opacity-80">Find tweets by semantic similarity</p>
        </Link>
        
        <Link href="/tweets" className="bg-accent text-white p-6 rounded-lg shadow hover:opacity-90 transition">
          <h2 className="text-xl font-bold">Browse Tweets</h2>
          <p className="mt-2 opacity-80">View all stored tweets</p>
        </Link>
        
        <Link href="/themes" className="bg-green-600 text-white p-6 rounded-lg shadow hover:opacity-90 transition">
          <h2 className="text-xl font-bold">Themes & Entities</h2>
          <p className="mt-2 opacity-80">Explore extracted themes and proper nouns</p>
        </Link>
      </div>
    </div>
  )
}
