'use client'

import { useEffect, useState } from 'react'

interface Tweet {
  id: string
  text: string
  author?: string
  hashtags?: string[]
  truncated?: boolean
}

const getApiUrl = () => {
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol
    const hostname = window.location.hostname
    return `${protocol}//${hostname}:8000`
  }
  return 'http://api:8000'
}

export default function TweetsPage() {
  const [tweets, setTweets] = useState<Tweet[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchTweets() {
      try {
        const response = await fetch(`${getApiUrl()}/tweets`)
        if (!response.ok) throw new Error('Failed to fetch tweets')
        const data = await response.json()
        setTweets(data.tweets || data || [])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }
    fetchTweets()
  }, [])

  if (loading) return <div className="text-xl">Loading tweets...</div>
  if (error) return <div className="text-red-500">Error: {error}</div>

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">All Tweets ({tweets.length})</h1>
      
      {tweets.length === 0 ? (
        <div className="text-center text-accent py-8">
          No tweets stored yet. Run the bookmark fetcher to add some!
        </div>
      ) : (
        <div className="space-y-4">
          {tweets.map((tweet) => (
            <div key={tweet.id} className="bg-white p-4 rounded-lg shadow">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold">@{tweet.author || 'unknown'}</span>
                <div className="flex gap-2">
                  {tweet.truncated && (
                    <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-xs">
                      Truncated
                    </span>
                  )}
                </div>
              </div>
              <p className="text-gray-800">{tweet.text}</p>
              {tweet.hashtags && tweet.hashtags.length > 0 && (
                <div className="mt-2 flex gap-2 flex-wrap">
                  {tweet.hashtags.map((tag) => (
                    <span key={tag} className="text-primary text-sm">#{tag}</span>
                  ))}
                </div>
              )}
              <div className="mt-2 text-xs text-accent">
                ID: {tweet.id}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
