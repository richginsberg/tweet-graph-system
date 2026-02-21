'use client'

import { useState } from 'react'

interface Tweet {
  id: string
  text: string
  author?: string
  score?: number
  hashtags?: string[]
}

const getApiUrl = () => {
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol
    const hostname = window.location.hostname
    return `${protocol}//${hostname}:8000`
  }
  return 'http://api:8000'
}

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Tweet[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    try {
      const response = await fetch(`${getApiUrl()}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, limit: 10 }),
      })
      const data = await response.json()
      setResults(data.results || [])
      setSearched(true)
    } catch (error) {
      console.error('Search failed:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Semantic Search</h1>
      
      <form onSubmit={handleSearch} className="mb-8">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search for tweets about AI, startups, python..."
            className="flex-1 p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-primary text-white px-6 py-3 rounded-lg hover:opacity-90 disabled:opacity-50"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
      </form>

      {searched && results.length === 0 && (
        <div className="text-center text-accent py-8">
          No results found. Try a different search term.
        </div>
      )}

      <div className="space-y-4">
        {results.map((tweet, index) => (
          <div key={tweet.id} className="bg-white p-4 rounded-lg shadow">
            <div className="flex items-start justify-between">
              <span className="text-sm text-accent">@{tweet.author || 'unknown'}</span>
              {tweet.score !== undefined && (
                <span className="bg-primary/10 text-primary px-2 py-1 rounded text-sm">
                  {(tweet.score * 100).toFixed(0)}% match
                </span>
              )}
            </div>
            <p className="mt-2">{tweet.text}</p>
            {tweet.hashtags && tweet.hashtags.length > 0 && (
              <div className="mt-2 flex gap-2 flex-wrap">
                {tweet.hashtags.map((tag) => (
                  <span key={tag} className="text-primary text-sm">
                    #{tag}
                  </span>
                ))}
              </div>
            )}
            <div className="mt-2 text-xs text-accent">
              ID: {tweet.id}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
