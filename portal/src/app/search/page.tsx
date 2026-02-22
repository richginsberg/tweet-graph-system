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
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2">Search</h1>
        <p className="text-[hsl(var(--muted-foreground))]">
          Find tweets using semantic similarity
        </p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch}>
        <div className="flex gap-3">
          <div className="relative flex-1">
            <svg 
              className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[hsl(var(--muted-foreground))]" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search for AI, machine learning, startups..."
              className="input pl-12"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary"
          >
            {loading ? (
              <div className="spinner w-5 h-5"></div>
            ) : (
              'Search'
            )}
          </button>
        </div>
      </form>

      {/* Results */}
      {searched && results.length === 0 && (
        <div className="card text-center py-12">
          <p className="text-[hsl(var(--muted-foreground))]">No results found</p>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-2">Try a different search term</p>
        </div>
      )}

      <div className="space-y-4">
        {results.map((tweet, index) => (
          <div 
            key={tweet.id}
            className="tweet-card"
            style={{ animationDelay: `${index * 0.05}s` }}
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                  <span className="text-white text-sm font-bold">
                    {(tweet.author || 'unknown')[0].toUpperCase()}
                  </span>
                </div>
                <span className="font-semibold">@{tweet.author || 'unknown'}</span>
              </div>
              {tweet.score !== undefined && (
                <div className="flex items-center gap-2">
                  <div className="h-2 w-24 bg-[hsl(var(--secondary))] rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full"
                      style={{ width: `${tweet.score * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium text-[hsl(var(--primary))]">
                    {(tweet.score * 100).toFixed(0)}%
                  </span>
                </div>
              )}
            </div>

            <p className="leading-relaxed">{tweet.text}</p>

            {tweet.hashtags && tweet.hashtags.length > 0 && (
              <div className="flex gap-2 mt-4 flex-wrap">
                {tweet.hashtags.map((tag) => (
                  <span key={tag} className="badge badge-primary">
                    #{tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
