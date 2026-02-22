'use client'

import { useEffect, useState, useRef } from 'react'

interface Tweet {
  id: string
  text: string
  author?: string
  hashtags?: string[]
  truncated?: boolean
  themes?: string[]
  entities?: string[]
  relationships?: { type: string; target: string }[]
}

interface FilterState {
  author: string
  hashtag: string
  theme: string
  truncated: boolean | null
}

const getApiUrl = () => {
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol
    const hostname = window.location.hostname
    return `${protocol}//${hostname}:8000`
  }
  return 'http://api:8000'
}

// Relationship colors for git-graph style
const relationshipColors: Record<string, string> = {
  HAS_HASHTAG: '#22c55e',
  MENTIONS: '#8b5cf6',
  ABOUT_THEME: '#f59e0b',
  MENTIONS_ENTITY: '#ef4444',
  CONTAINS_URL: '#6366f1',
  POSTED: '#3b82f6',
  REPLY_TO: '#ec4899',
  QUOTES: '#14b8a6',
}

export default function TweetsPage() {
  const [tweets, setTweets] = useState<Tweet[]>([])
  const [filteredTweets, setFilteredTweets] = useState<Tweet[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<FilterState>({
    author: '',
    hashtag: '',
    theme: '',
    truncated: null,
  })
  const [allHashtags, setAllHashtags] = useState<string[]>([])
  const [allAuthors, setAllAuthors] = useState<string[]>([])

  useEffect(() => {
    async function fetchTweets() {
      try {
        const response = await fetch(`${getApiUrl()}/tweets`)
        if (!response.ok) throw new Error('Failed to fetch tweets')
        const data = await response.json()
        const tweetsData = data.tweets || data || []
        setTweets(tweetsData)
        setFilteredTweets(tweetsData)
        
        // Extract unique values for filters
        const authors = new Set<string>()
        const hashtags = new Set<string>()
        tweetsData.forEach((t: Tweet) => {
          if (t.author) authors.add(t.author)
          t.hashtags?.forEach(h => hashtags.add(h))
        })
        setAllAuthors(Array.from(authors))
        setAllHashtags(Array.from(hashtags))
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }
    fetchTweets()
  }, [])

  useEffect(() => {
    let filtered = tweets
    
    if (filters.author) {
      filtered = filtered.filter(t => t.author === filters.author)
    }
    if (filters.hashtag) {
      filtered = filtered.filter(t => t.hashtags?.includes(filters.hashtag))
    }
    if (filters.truncated !== null) {
      filtered = filtered.filter(t => t.truncated === filters.truncated)
    }
    
    setFilteredTweets(filtered)
  }, [filters, tweets])

  const clearFilters = () => {
    setFilters({ author: '', hashtag: '', theme: '', truncated: null })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="spinner mx-auto mb-4"></div>
          <p className="text-[hsl(var(--muted-foreground))]">Loading tweets...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card border-red-500/50 bg-red-500/10">
        <p className="text-red-400">Error: {error}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2">Tweets</h1>
        <p className="text-[hsl(var(--muted-foreground))]">
          {filteredTweets.length} of {tweets.length} tweets
        </p>
      </div>

      {/* Sticky Filter Header */}
      <div className="sticky top-16 z-40 -mx-4 sm:-mx-6 lg:-mx-8 px-4 sm:px-6 lg:px-8 py-4 bg-[hsl(var(--background)/0.95)] backdrop-blur-xl border-b border-[hsl(var(--border))]">
        <div className="flex flex-wrap gap-3 items-center">
          {/* Author Filter */}
          <select
            value={filters.author}
            onChange={(e) => setFilters(f => ({ ...f, author: e.target.value }))}
            className="input w-auto min-w-[150px]"
          >
            <option value="">All Authors</option>
            {allAuthors.map(author => (
              <option key={author} value={author}>@{author}</option>
            ))}
          </select>

          {/* Hashtag Filter */}
          <select
            value={filters.hashtag}
            onChange={(e) => setFilters(f => ({ ...f, hashtag: e.target.value }))}
            className="input w-auto min-w-[150px]"
          >
            <option value="">All Hashtags</option>
            {allHashtags.map(tag => (
              <option key={tag} value={tag}>#{tag}</option>
            ))}
          </select>

          {/* Truncated Filter */}
          <select
            value={filters.truncated === null ? '' : filters.truncated.toString()}
            onChange={(e) => setFilters(f => ({ 
              ...f, 
              truncated: e.target.value === '' ? null : e.target.value === 'true' 
            }))}
            className="input w-auto min-w-[150px]"
          >
            <option value="">All Status</option>
            <option value="false">Full Text</option>
            <option value="true">Truncated</option>
          </select>

          {/* Clear Filters */}
          {(filters.author || filters.hashtag || filters.truncated !== null) && (
            <button onClick={clearFilters} className="btn btn-secondary text-sm">
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Tweets List with Git-Graph Style */}
      {filteredTweets.length === 0 ? (
        <div className="card text-center py-16">
          <p className="text-[hsl(var(--muted-foreground))]">No tweets match your filters</p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredTweets.map((tweet, index) => (
            <TweetCard 
              key={tweet.id} 
              tweet={tweet} 
              index={index}
              isLast={index === filteredTweets.length - 1}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function TweetCard({ tweet, index, isLast }: { tweet: Tweet; index: number; isLast: boolean }) {
  const [showEmbed, setShowEmbed] = useState(false)
  const iframeRef = useRef<HTMLIFrameElement>(null)

  // Generate random relationship lines for visual effect
  const relationships = [
    ...(tweet.hashtags?.map(h => ({ type: 'HAS_HASHTAG', target: h })) || []),
    ...(tweet.themes?.map(t => ({ type: 'ABOUT_THEME', target: t })) || []),
  ]
  
  // Pick 1-3 relationships to show as colored lines
  const shownRelationships = relationships.slice(0, 3)

  return (
    <div className="flex group">
      {/* Git-Graph Style Left Gutter */}
      <div className="relative flex-shrink-0 w-12 mr-4">
        {/* Main vertical line */}
        <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-[hsl(var(--border))] -translate-x-1/2" />
        
        {/* Connection lines */}
        {shownRelationships.map((rel, i) => (
          <div
            key={i}
            className="absolute left-1/2 w-4 h-0.5"
            style={{
              backgroundColor: relationshipColors[rel.type] || '#666',
              top: `${25 + i * 25}%`,
            }}
          />
        ))}
        
        {/* Node dot */}
        <div 
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-4 h-4 rounded-full border-2 bg-[hsl(var(--background))]"
          style={{ 
            borderColor: shownRelationships[0] 
              ? relationshipColors[shownRelationships[0].type] 
              : 'hsl(var(--primary))'
          }}
        />

        {/* Bottom fade for last item */}
        {isLast && (
          <div className="absolute left-1/2 bottom-0 -translate-x-1/2 w-4 h-8 bg-gradient-to-b from-transparent to-[hsl(var(--background))]" />
        )}
      </div>

      {/* Tweet Card */}
      <div className="flex-1 tweet-card">
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Tweet Content / Embed */}
          <div className="flex-1 min-w-0">
            {/* Author Row */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center flex-shrink-0">
                  <span className="text-white text-sm font-bold">
                    {(tweet.author || 'unknown')[0].toUpperCase()}
                  </span>
                </div>
                <span className="font-semibold">@{tweet.author || 'unknown'}</span>
              </div>
              
              {/* Embed Toggle */}
              <button
                onClick={() => setShowEmbed(!showEmbed)}
                className="btn btn-secondary text-xs px-3 py-1"
              >
                {showEmbed ? 'Hide Embed' : 'Show Embed'}
              </button>
            </div>

            {/* Tweet Embed or Text */}
            {showEmbed ? (
              <div className="rounded-lg overflow-hidden bg-white">
                <iframe
                  ref={iframeRef}
                  src={`https://platform.twitter.com/embed/Tweet.html?d=true&id=${tweet.id}&theme=dark`}
                  className="w-full min-h-[200px]"
                  style={{ border: 'none' }}
                  loading="lazy"
                />
              </div>
            ) : (
              <p className="text-[hsl(var(--foreground))] leading-relaxed whitespace-pre-wrap">
                {tweet.text}
              </p>
            )}

            {/* Hashtags */}
            {tweet.hashtags && tweet.hashtags.length > 0 && (
              <div className="flex gap-2 mt-4 flex-wrap">
                {tweet.hashtags.map((tag) => (
                  <span key={tag} className="badge badge-primary">
                    #{tag}
                  </span>
                ))}
              </div>
            )}

            {/* Tweet ID */}
            <div className="mt-4 pt-3 border-t border-[hsl(var(--border))]">
              <p className="text-xs text-[hsl(var(--muted-foreground))] font-mono">
                ID: {tweet.id}
              </p>
            </div>
          </div>

          {/* Metadata Panel */}
          <div className="lg:w-64 flex-shrink-0 space-y-3">
            {/* Status */}
            <div className="p-3 rounded-lg bg-[hsl(var(--secondary))]">
              <p className="text-xs text-[hsl(var(--muted-foreground))] mb-1">Status</p>
              {tweet.truncated ? (
                <span className="badge badge-warning">Truncated</span>
              ) : (
                <span className="badge badge-primary">Full Text</span>
              )}
            </div>

            {/* Relationships */}
            <div className="p-3 rounded-lg bg-[hsl(var(--secondary))]">
              <p className="text-xs text-[hsl(var(--muted-foreground))] mb-2">Relationships</p>
              <div className="space-y-1">
                {tweet.hashtags && tweet.hashtags.length > 0 && (
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: relationshipColors.HAS_HASHTAG }} />
                    <span className="text-sm">{tweet.hashtags.length} hashtags</span>
                  </div>
                )}
                {tweet.themes && tweet.themes.length > 0 && (
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: relationshipColors.ABOUT_THEME }} />
                    <span className="text-sm">{tweet.themes.length} themes</span>
                  </div>
                )}
                {tweet.entities && tweet.entities.length > 0 && (
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: relationshipColors.MENTIONS_ENTITY }} />
                    <span className="text-sm">{tweet.entities.length} entities</span>
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: relationshipColors.POSTED }} />
                  <span className="text-sm">1 author</span>
                </div>
              </div>
            </div>

            {/* Bookmark Link */}
            <a
              href={`https://x.com/i/status/${tweet.id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-3 rounded-lg bg-[hsl(var(--secondary))] hover:bg-[hsl(var(--muted))] transition-colors"
            >
              <p className="text-xs text-[hsl(var(--muted-foreground))] mb-1">View on X</p>
              <span className="text-sm text-[hsl(var(--primary))]">Open Tweet →</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
