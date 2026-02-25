'use client'

import { useEffect, useState, useRef, useCallback } from 'react'
import { fetchTweetsPaginated, PaginatedTweets } from '@/lib/api'

interface Tweet {
  id: string
  text: string
  author?: string
  hashtags?: string[]
  truncated?: boolean
  created_at?: string
}

interface FilterState {
  author: string
  hashtag: string
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

const TWEETS_PER_PAGE = 50

export default function TweetsPage() {
  const [tweets, setTweets] = useState<Tweet[]>([])
  const [filteredTweets, setFilteredTweets] = useState<Tweet[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasMore, setHasMore] = useState(true)
  const [offset, setOffset] = useState(0)
  const [total, setTotal] = useState(0)
  const [filters, setFilters] = useState<FilterState>({
    author: '',
    hashtag: '',
    truncated: null,
  })
  const [allHashtags, setAllHashtags] = useState<string[]>([])
  const [allAuthors, setAllAuthors] = useState<string[]>([])
  const [enrichingIds, setEnrichingIds] = useState<Set<string>>(new Set())
  const [enrichmentEnabled, setEnrichmentEnabled] = useState(false)

  // Enrich a truncated tweet
  const enrichTweet = useCallback(async (tweetId: string) => {
    setEnrichingIds(prev => new Set(prev).add(tweetId))
    try {
      const response = await fetch(`${getApiUrl()}/tweets/${tweetId}/enrich`, {
        method: 'POST',
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Enrichment failed')
      }
      const result = await response.json()
      
      // Update the tweet in the list
      setTweets(prev => prev.map(t => 
        t.id === tweetId 
          ? { ...t, truncated: false, text: result.text || t.text, author: result.author || t.author }
          : t
      ))
      
      return result
    } catch (err) {
      console.error('Enrichment failed:', err)
      throw err
    } finally {
      setEnrichingIds(prev => {
        const next = new Set(prev)
        next.delete(tweetId)
        return next
      })
    }
  }, [])

  // Enrich all truncated tweets
  const enrichAllTruncated = useCallback(async () => {
    try {
      const response = await fetch(`${getApiUrl()}/tweets/enrich-all`, {
        method: 'POST',
      })
      if (!response.ok) throw new Error('Batch enrichment failed')
      const result = await response.json()
      
      // Reload tweets to get updated status
      const data = await fetchTweetsPaginated(TWEETS_PER_PAGE, 0)
      setTweets(data.tweets)
      setTotal(data.total)
      
      return result
    } catch (err) {
      console.error('Batch enrichment failed:', err)
      throw err
    }
  }, [])

  // Check enrichment capability on mount
  useEffect(() => {
    async function checkEnrichment() {
      try {
        const response = await fetch(`${getApiUrl()}/health`)
        if (response.ok) {
          const data = await response.json()
          setEnrichmentEnabled(data.enrichment_enabled === true)
        }
      } catch (err) {
        console.error('Failed to check enrichment status:', err)
      }
    }
    checkEnrichment()
  }, [])

  // Initial load
  useEffect(() => {
    async function loadInitial() {
      try {
        setLoading(true)
        const data = await fetchTweetsPaginated(TWEETS_PER_PAGE, 0)
        setTweets(data.tweets)
        setFilteredTweets(data.tweets)
        setTotal(data.total)
        setHasMore(data.has_more)
        setOffset(data.tweets.length)
        
        // Extract unique values for filters from all tweets
        // We need to fetch a sample for filters since we paginate
        const sampleResponse = await fetch(`${getApiUrl()}/tweets?limit=200&offset=0`)
        if (sampleResponse.ok) {
          const sampleData = await sampleResponse.json()
          const sampleTweets = sampleData.tweets || []
          const authors = new Set<string>()
          const hashtags = new Set<string>()
          sampleTweets.forEach((t: Tweet) => {
            if (t.author) authors.add(t.author)
            t.hashtags?.forEach(h => hashtags.add(h))
          })
          setAllAuthors(Array.from(authors).sort())
          setAllHashtags(Array.from(hashtags).sort())
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }
    loadInitial()
  }, [])

  // Apply filters to loaded tweets
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

  // Load more tweets
  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return
    
    try {
      setLoadingMore(true)
      const data = await fetchTweetsPaginated(TWEETS_PER_PAGE, offset)
      
      // Merge new tweets, avoiding duplicates
      const newTweets = data.tweets.filter(
        newTweet => !tweets.some(existing => existing.id === newTweet.id)
      )
      
      setTweets(prev => [...prev, ...newTweets])
      setHasMore(data.has_more)
      setOffset(prev => prev + newTweets.length)
    } catch (err) {
      console.error('Failed to load more:', err)
    } finally {
      setLoadingMore(false)
    }
  }, [offset, hasMore, loadingMore, tweets])

  const clearFilters = () => {
    setFilters({ author: '', hashtag: '', truncated: null })
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
          {filteredTweets.length} of {total} tweets loaded
          {hasMore && ' (more available)'}
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

      {/* Tweets List */}
      {filteredTweets.length === 0 ? (
        <div className="card text-center py-16">
          <p className="text-[hsl(var(--muted-foreground))]">No tweets match your filters</p>
        </div>
      ) : (
        <>
          <div className="space-y-4">
            {filteredTweets.map((tweet, index) => (
              <TweetCard 
                key={tweet.id} 
                tweet={tweet} 
                index={index}
                isLast={index === filteredTweets.length - 1}
                enrichTweet={enrichmentEnabled ? enrichTweet : undefined}
                isEnriching={enrichingIds.has(tweet.id)}
              />
            ))}
          </div>

          {/* Load More Button */}
          {hasMore && (
            <div className="flex justify-center py-8">
              <button
                onClick={loadMore}
                disabled={loadingMore}
                className="btn btn-primary min-w-[200px]"
              >
                {loadingMore ? (
                  <span className="flex items-center gap-2">
                    <span className="spinner"></span>
                    Loading...
                  </span>
                ) : (
                  `Load More (${total - offset} remaining)`
                )}
              </button>
            </div>
          )}

          {/* End of list */}
          {!hasMore && tweets.length > 0 && (
            <div className="text-center py-8 text-[hsl(var(--muted-foreground))]">
              — All {total} tweets loaded —
            </div>
          )}
        </>
      )}
    </div>
  )
}

function TweetCard({ 
  tweet, 
  index, 
  isLast,
  enrichTweet,
  isEnriching
}: { 
  tweet: Tweet; 
  index: number; 
  isLast: boolean;
  enrichTweet?: (id: string) => Promise<any>;
  isEnriching?: boolean;
}) {
  const [showEmbed, setShowEmbed] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)

  // Generate random relationship lines for visual effect
  const relationships = [
    ...(tweet.hashtags?.map(h => ({ type: 'HAS_HASHTAG', target: h })) || []),
  ]
  
  const shownRelationships = relationships.slice(0, 3)

  return (
    <div className="flex group">
      {/* Git-Graph Style Left Gutter */}
      <div className="relative flex-shrink-0 w-12 mr-4">
        <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-[hsl(var(--border))] -translate-x-1/2" />
        
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
        
        <div 
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-4 h-4 rounded-full border-2 bg-[hsl(var(--background))]"
          style={{ 
            borderColor: shownRelationships[0] 
              ? relationshipColors[shownRelationships[0].type] 
              : 'hsl(var(--primary))'
          }}
        />

        {isLast && (
          <div className="absolute left-1/2 bottom-0 -translate-x-1/2 w-4 h-8 bg-gradient-to-b from-transparent to-[hsl(var(--background))]" />
        )}
      </div>

      {/* Tweet Card */}
      <div className="flex-1 tweet-card">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center flex-shrink-0">
              <span className="text-white text-sm font-bold">
                {(tweet.author || 'unknown')[0].toUpperCase()}
              </span>
            </div>
            <span className="font-semibold">@{tweet.author || 'unknown'}</span>
          </div>
          
          <button
            onClick={() => setShowEmbed(!showEmbed)}
            className="btn btn-secondary text-xs px-3 py-1"
          >
            {showEmbed ? 'Show Text' : 'Show Embed'}
          </button>
        </div>

        {showEmbed ? (
          <div className="space-y-4">
            <div 
              className="w-full rounded-xl overflow-hidden relative" 
              style={{ 
                background: 'rgb(22, 28, 37)',
                maxHeight: isExpanded ? '800px' : '400px',
                overflowY: 'auto'
              }}
            >
              <iframe
                src={`https://platform.twitter.com/embed/Tweet.html?d=true&id=${tweet.id}&theme=dark&width=550`}
                className="w-full"
                style={{ 
                  border: 'none',
                  minHeight: isExpanded ? '600px' : '300px',
                  maxWidth: '100%'
                }}
                loading="lazy"
              />
              
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="absolute bottom-2 right-2 btn btn-secondary text-xs px-2 py-1 opacity-80 hover:opacity-100"
                style={{ zIndex: 10 }}
              >
                {isExpanded ? '⬆ Collapse' : '⬇ Expand'}
              </button>
            </div>
            
            <div className="flex flex-wrap gap-3 items-center">
              {tweet.truncated ? (
                <>
                  <span className="badge badge-warning">Truncated</span>
                  {enrichTweet && (
                    <button
                      onClick={() => enrichTweet(tweet.id)}
                      disabled={isEnriching}
                      className="badge badge-warning hover:bg-yellow-600/30 cursor-pointer disabled:opacity-50"
                      title="Fetch full text via X API"
                    >
                      {isEnriching ? 'Enriching...' : '↻ Enrich'}
                    </button>
                  )}
                </>
              ) : (
                <span className="badge badge-primary">Full Text</span>
              )}
              {tweet.hashtags && tweet.hashtags.length > 0 && tweet.hashtags.map((tag) => (
                <span key={tag} className="badge badge-primary">
                  #{tag}
                </span>
              ))}
              <a
                href={`https://x.com/i/status/${tweet.id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-[hsl(var(--primary))] hover:underline ml-auto"
              >
                View on X →
              </a>
            </div>
          </div>
        ) : (
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="flex-1 min-w-0">
              <p className="text-[hsl(var(--foreground))] leading-relaxed whitespace-pre-wrap">
                {tweet.text}
              </p>

              {tweet.hashtags && tweet.hashtags.length > 0 && (
                <div className="flex gap-2 mt-4 flex-wrap">
                  {tweet.hashtags.map((tag) => (
                    <span key={tag} className="badge badge-primary">
                      #{tag}
                    </span>
                  ))}
                </div>
              )}

              <div className="mt-4 pt-3 border-t border-[hsl(var(--border))]">
                <p className="text-xs text-[hsl(var(--muted-foreground))] font-mono">
                  ID: {tweet.id}
                </p>
              </div>
            </div>

            {/* Metadata Panel */}
            <div className="lg:w-64 flex-shrink-0 space-y-3">
              <div className="p-3 rounded-lg bg-[hsl(var(--secondary))]">
                <p className="text-xs text-[hsl(var(--muted-foreground))] mb-1">Status</p>
                {tweet.truncated ? (
                  <div className="space-y-2">
                    <span className="badge badge-warning">Truncated</span>
                    {enrichTweet && (
                      <button
                        onClick={() => enrichTweet(tweet.id)}
                        disabled={isEnriching}
                        className="btn btn-warning text-xs w-full"
                      >
                        {isEnriching ? (
                          <span className="flex items-center justify-center gap-2">
                            <span className="spinner w-3 h-3"></span>
                            Enriching...
                          </span>
                        ) : (
                          '↻ Fetch Full Text via X'
                        )}
                      </button>
                    )}
                  </div>
                ) : (
                  <span className="badge badge-primary">Full Text</span>
                )}
              </div>

              <div className="p-3 rounded-lg bg-[hsl(var(--secondary))]">
                <p className="text-xs text-[hsl(var(--muted-foreground))] mb-2">Relationships</p>
                <div className="space-y-1">
                  {tweet.hashtags && tweet.hashtags.length > 0 && (
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full" style={{ backgroundColor: relationshipColors.HAS_HASHTAG }} />
                      <span className="text-sm">{tweet.hashtags.length} hashtags</span>
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: relationshipColors.POSTED }} />
                    <span className="text-sm">1 author</span>
                  </div>
                </div>
              </div>

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
        )}
      </div>
    </div>
  )
}
