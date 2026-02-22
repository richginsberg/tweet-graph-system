'use client'

import { useEffect, useState } from 'react'

interface Theme {
  name: string
  count: number
}

interface Entity {
  name: string
  count: number
}

const getApiUrl = () => {
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol
    const hostname = window.location.hostname
    return `${protocol}//${hostname}:8000`
  }
  return 'http://api:8000'
}

export default function ThemesPage() {
  const [themes, setThemes] = useState<Theme[]>([])
  const [entities, setEntities] = useState<Entity[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
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
    }
    fetchData()
  }, [])

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
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {entities.map((entity) => (
                <div 
                  key={entity.name} 
                  className="flex items-center justify-between p-3 rounded-lg bg-[hsl(var(--secondary))] hover:bg-[hsl(var(--muted))] transition-colors"
                >
                  <span className="font-medium">{entity.name}</span>
                  <span className="badge badge-secondary">{entity.count} mentions</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
