'use client'

import { useEffect, useState, useCallback } from 'react'

interface Theme {
  name: string
  count: number
}

interface Entity {
  name: string
  count: number
}

interface EntityTweet {
  id: string
  text: string
  author: string
  posted_at: string
}

interface EntityGraph {
  entity: string
  tweets: EntityTweet[]
  count: number
}

interface EditPreview {
  old_name: string
  new_name: string
  target_exists: boolean
  is_merge: boolean
  source_tweets: EntityTweet[]
  source_count: number
  target_tweets: EntityTweet[]
  target_count: number
}

const getApiUrl = () => {
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol
    const hostname = window.location.hostname
    return `${protocol}//${hostname}:8000`
  }
  return 'http://api:8000'
}

// Highlight text matching entity names
function highlightEntityText(text: string, entityNames: string[]): React.ReactNode {
  if (!entityNames.length || !text) return text
  
  // Create regex pattern for all entity names (case-insensitive)
  const pattern = new RegExp(`(${entityNames.map(n => n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi')
  const parts = text.split(pattern)
  
  return parts.map((part, i) => {
    const isMatch = entityNames.some(name => part.toLowerCase() === name.toLowerCase())
    return isMatch ? (
      <mark key={i} className="bg-yellow-300 text-black px-0.5 rounded">{part}</mark>
    ) : (
      <span key={i}>{part}</span>
    )
  })
}

export default function ThemesPage() {
  const [themes, setThemes] = useState<Theme[]>([])
  const [entities, setEntities] = useState<Entity[]>([])
  const [loading, setLoading] = useState(true)
  const [deleteModal, setDeleteModal] = useState<{ open: boolean; entity: Entity | null }>({
    open: false,
    entity: null
  })
  const [entityGraph, setEntityGraph] = useState<EntityGraph | null>(null)
  const [loadingGraph, setLoadingGraph] = useState(false)
  const [deleting, setDeleting] = useState(false)
  
  // Edit modal state
  const [editModal, setEditModal] = useState<{ open: boolean; entity: Entity | null }>({
    open: false,
    entity: null
  })
  const [newEntityName, setNewEntityName] = useState('')
  const [editPreview, setEditPreview] = useState<EditPreview | null>(null)
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [saving, setSaving] = useState(false)

  const fetchData = useCallback(async () => {
    try {
      const themesRes = await fetch(`${getApiUrl()}/themes`)
      if (themesRes.ok) {
        const data = await themesRes.json()
        setThemes(data.themes || data || [])
      }

      const entitiesRes = await fetch(`${getApiUrl()}/entities`)
      if (entitiesRes.ok) {
        const data = await entitiesRes.json()
        setEntities(data.entities || data || [])
      }
    } catch (error) {
      console.error('Failed to fetch data:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Fetch entity graph for delete modal
  const openDeleteModal = async (entity: Entity) => {
    setDeleteModal({ open: true, entity })
    setLoadingGraph(true)
    setEntityGraph(null)
    
    try {
      const res = await fetch(`${getApiUrl()}/entities/${encodeURIComponent(entity.name)}/graph?limit=10`)
      if (res.ok) {
        const data = await res.json()
        setEntityGraph(data)
      }
    } catch (error) {
      console.error('Failed to fetch entity graph:', error)
    } finally {
      setLoadingGraph(false)
    }
  }

  // Open edit modal and fetch preview
  const openEditModal = async (entity: Entity) => {
    setEditModal({ open: true, entity })
    setNewEntityName(entity.name)
    setEditPreview(null)
    await fetchEditPreview(entity.name, entity.name)
  }

  // Fetch edit preview
  const fetchEditPreview = async (oldName: string, newName: string) => {
    if (!newName.trim()) {
      setEditPreview(null)
      return
    }
    
    setLoadingPreview(true)
    try {
      const res = await fetch(`${getApiUrl()}/entities/${encodeURIComponent(oldName)}/edit-preview?new_name=${encodeURIComponent(newName)}`)
      if (res.ok) {
        const data = await res.json()
        setEditPreview(data)
      }
    } catch (error) {
      console.error('Failed to fetch edit preview:', error)
    } finally {
      setLoadingPreview(false)
    }
  }

  // Handle new name change
  useEffect(() => {
    if (editModal.entity && newEntityName !== editModal.entity.name) {
      const timer = setTimeout(() => {
        fetchEditPreview(editModal.entity!.name, newEntityName)
      }, 300)
      return () => clearTimeout(timer)
    }
  }, [newEntityName, editModal.entity])

  const handleDeleteEntity = async (entityName: string) => {
    setDeleting(true)
    try {
      const res = await fetch(`${getApiUrl()}/entities/${encodeURIComponent(entityName)}`, {
        method: 'DELETE'
      })
      
      if (res.ok) {
        await fetchData()
        setDeleteModal({ open: false, entity: null })
        setEntityGraph(null)
      } else {
        const error = await res.json()
        alert(`Failed to delete: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Delete failed:', error)
      alert('Failed to delete entity')
    } finally {
      setDeleting(false)
    }
  }

  const handleSaveEntity = async () => {
    if (!editModal.entity || !newEntityName.trim()) return
    
    setSaving(true)
    try {
      const res = await fetch(
        `${getApiUrl()}/entities/${encodeURIComponent(editModal.entity.name)}?new_name=${encodeURIComponent(newEntityName.trim())}`,
        { method: 'PUT' }
      )
      
      if (res.ok) {
        const result = await res.json()
        await fetchData()
        setEditModal({ open: false, entity: null })
        setEditPreview(null)
        setNewEntityName('')
      } else {
        const error = await res.json()
        alert(`Failed to save: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Save failed:', error)
      alert('Failed to save entity')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="spinner mx-auto mb-4"></div>
          <p className="text-[hsl(var(--muted-foreground))]">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <>
      {/* Delete Confirmation Modal */}
      {deleteModal.open && deleteModal.entity && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-[hsl(var(--card))] rounded-lg max-w-2xl w-full max-h-[90vh] overflow-hidden shadow-xl flex flex-col">
            <div className="p-6 border-b border-[hsl(var(--border))]">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-red-500 to-pink-500 flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-xl font-bold">Delete Entity?</h3>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">This action cannot be undone</p>
                </div>
              </div>
            </div>

            <div className="p-6 border-b border-[hsl(var(--border))] bg-[hsl(var(--muted))]">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">Entity</p>
                  <p className="text-lg font-bold">{deleteModal.entity.name}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">Mentions</p>
                  <p className="text-2xl font-bold text-purple-500">{deleteModal.entity.count}</p>
                </div>
              </div>
            </div>

            <div className="p-6 flex-1 overflow-y-auto">
              <h4 className="text-sm font-semibold text-[hsl(var(--muted-foreground))] mb-3">
                Connected Tweets (will preserve)
              </h4>
              
              {loadingGraph ? (
                <div className="text-center py-8">
                  <div className="spinner mx-auto mb-2"></div>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">Loading graph...</p>
                </div>
              ) : entityGraph && entityGraph.tweets.length > 0 ? (
                <div className="space-y-2">
                  {entityGraph.tweets.map((tweet) => (
                    <div 
                      key={tweet.id}
                      className="p-3 rounded-lg bg-[hsl(var(--secondary))] text-sm"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-purple-400">@{tweet.author}</span>
                        <span className="text-xs text-[hsl(var(--muted-foreground))]">
                          {tweet.posted_at ? new Date(tweet.posted_at).toLocaleDateString() : ''}
                        </span>
                      </div>
                      <p className="text-[hsl(var(--foreground))] whitespace-pre-wrap">
                        {highlightEntityText(tweet.text, [deleteModal.entity!.name])}
                      </p>
                    </div>
                  ))}
                  {entityGraph.count > 10 && (
                    <p className="text-xs text-center text-[hsl(var(--muted-foreground))] pt-2">
                      +{entityGraph.count - 10} more tweets
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-center py-8 text-[hsl(var(--muted-foreground))]">No connected tweets found</p>
              )}
            </div>

            <div className="p-6 border-t border-[hsl(var(--border))] flex gap-3 justify-end">
              <button
                onClick={() => {
                  setDeleteModal({ open: false, entity: null })
                  setEntityGraph(null)
                }}
                className="btn btn-secondary"
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                onClick={() => handleDeleteEntity(deleteModal.entity!.name)}
                className="btn btn-danger"
                disabled={deleting}
              >
                {deleting ? 'Deleting...' : `Delete Entity (${deleteModal.entity.count} relationships)`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit/Rename Modal */}
      {editModal.open && editModal.entity && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-[hsl(var(--card))] rounded-lg max-w-3xl w-full max-h-[90vh] overflow-hidden shadow-xl flex flex-col">
            <div className="p-6 border-b border-[hsl(var(--border))]">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-xl font-bold">Edit Entity</h3>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">Rename or merge with existing entity</p>
                </div>
              </div>
            </div>

            <div className="p-6 border-b border-[hsl(var(--border))]">
              <label className="block text-sm font-medium mb-2">Entity Name</label>
              <input
                type="text"
                value={newEntityName}
                onChange={(e) => setNewEntityName(e.target.value)}
                className="w-full p-3 rounded-lg bg-[hsl(var(--secondary))] border border-[hsl(var(--border))] text-[hsl(var(--foreground))] focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter new entity name..."
              />
              {editPreview?.is_merge && (
                <p className="mt-2 text-sm text-amber-500 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  This will merge &quot;{editPreview.old_name}&quot; into existing &quot;{editPreview.new_name}&quot;
                </p>
              )}
            </div>

            <div className="p-6 flex-1 overflow-y-auto">
              {loadingPreview ? (
                <div className="text-center py-8">
                  <div className="spinner mx-auto mb-2"></div>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">Analyzing changes...</p>
                </div>
              ) : editPreview ? (
                <div className="space-y-6">
                  {/* Source tweets (being renamed/merged) */}
                  <div>
                    <h4 className="text-sm font-semibold text-[hsl(var(--muted-foreground))] mb-3 flex items-center gap-2">
                      <span className="w-3 h-3 border-2 border-dashed border-purple-500 rounded"></span>
                      Tweets with &quot;{editPreview.old_name}&quot; ({editPreview.source_count})
                    </h4>
                    <div className="space-y-2">
                      {editPreview.source_tweets.slice(0, 5).map((tweet) => (
                        <div 
                          key={tweet.id}
                          className="p-3 rounded-lg border-2 border-dashed border-purple-500/50 bg-[hsl(var(--secondary))] text-sm"
                        >
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-purple-400">@{tweet.author}</span>
                            <span className="text-xs text-[hsl(var(--muted-foreground))]">
                              {tweet.posted_at ? new Date(tweet.posted_at).toLocaleDateString() : ''}
                            </span>
                          </div>
                          <p className="text-[hsl(var(--foreground))] whitespace-pre-wrap">
                            {highlightEntityText(tweet.text, [editPreview.old_name, editPreview.new_name])}
                          </p>
                        </div>
                      ))}
                      {editPreview.source_count > 5 && (
                        <p className="text-xs text-center text-[hsl(var(--muted-foreground))]">
                          +{editPreview.source_count - 5} more tweets
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Target tweets (existing entity) */}
                  {editPreview.is_merge && editPreview.target_tweets.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-[hsl(var(--muted-foreground))] mb-3 flex items-center gap-2">
                        <span className="w-3 h-3 border-2 border-solid border-green-500 rounded"></span>
                        Existing tweets with &quot;{editPreview.new_name}&quot; ({editPreview.target_count})
                      </h4>
                      <div className="space-y-2">
                        {editPreview.target_tweets.slice(0, 5).map((tweet) => (
                          <div 
                            key={tweet.id}
                            className="p-3 rounded-lg border-2 border-solid border-green-500/50 bg-[hsl(var(--secondary))] text-sm"
                          >
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-medium text-green-400">@{tweet.author}</span>
                              <span className="text-xs text-[hsl(var(--muted-foreground))]">
                                {tweet.posted_at ? new Date(tweet.posted_at).toLocaleDateString() : ''}
                              </span>
                            </div>
                            <p className="text-[hsl(var(--foreground))] whitespace-pre-wrap">
                              {highlightEntityText(tweet.text, [editPreview.old_name, editPreview.new_name])}
                            </p>
                          </div>
                        ))}
                        {editPreview.target_count > 5 && (
                          <p className="text-xs text-center text-[hsl(var(--muted-foreground))]">
                            +{editPreview.target_count - 5} more tweets
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-center py-8 text-[hsl(var(--muted-foreground))]">Enter a new name to preview changes</p>
              )}
            </div>

            <div className="p-6 border-t border-[hsl(var(--border))] flex gap-3 justify-end">
              <button
                onClick={() => {
                  setEditModal({ open: false, entity: null })
                  setEditPreview(null)
                  setNewEntityName('')
                }}
                className="btn btn-secondary"
                disabled={saving}
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEntity}
                className="btn btn-primary"
                disabled={saving || !newEntityName.trim() || newEntityName === editModal.entity?.name}
              >
                {saving ? 'Saving...' : editPreview?.is_merge ? 'Merge Entities' : 'Rename Entity'}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold mb-2">Themes & Entities</h1>
          <p className="text-[hsl(var(--muted-foreground))]">
            Automatically extracted topics and proper nouns from your tweets
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Themes */}
          <div className="card">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                </svg>
              </div>
              <div>
                <h2 className="text-xl font-bold">Themes</h2>
                <p className="text-sm text-[hsl(var(--muted-foreground))]">{themes.length} topics detected</p>
              </div>
            </div>

            {themes.length === 0 ? (
              <p className="text-[hsl(var(--muted-foreground))] text-center py-8">No themes extracted yet</p>
            ) : (
              <div className="space-y-2">
                {themes.map((theme) => (
                  <div 
                    key={theme.name} 
                    className="flex items-center justify-between p-3 rounded-lg bg-[hsl(var(--secondary))] hover:bg-[hsl(var(--muted))] transition-colors"
                  >
                    <span className="font-medium capitalize">{theme.name}</span>
                    <span className="badge badge-primary">{theme.count} tweets</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Entities */}
          <div className="card">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <div>
                <h2 className="text-xl font-bold">Entities</h2>
                <p className="text-sm text-[hsl(var(--muted-foreground))]">{entities.length} proper nouns detected</p>
              </div>
            </div>

            {entities.length === 0 ? (
              <p className="text-[hsl(var(--muted-foreground))] text-center py-8">No entities extracted yet</p>
            ) : (
              <div className="space-y-2 max-h-[600px] overflow-y-auto">
                {entities.map((entity) => (
                  <div 
                    key={entity.name} 
                    className="flex items-center justify-between p-3 rounded-lg bg-[hsl(var(--secondary))] hover:bg-[hsl(var(--muted))] transition-colors group"
                  >
                    <span className="font-medium">{entity.name}</span>
                    <div className="flex items-center gap-1">
                      <span className="badge badge-secondary">{entity.count}</span>
                      <button
                        onClick={() => openEditModal(entity)}
                        className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded hover:bg-blue-500/20 text-blue-400"
                        title="Edit entity"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => openDeleteModal(entity)}
                        className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded bg-red-500/10 hover:bg-red-500/30 text-red-500 border border-red-500/30"
                        title="Delete entity"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
