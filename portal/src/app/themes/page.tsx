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
        // Fetch themes
        const themesRes = await fetch(`${getApiUrl()}/themes`)
        if (themesRes.ok) {
          const data = await themesRes.json()
          setThemes(data.themes || data || [])
        }

        // Fetch entities
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

  if (loading) return <div className="text-xl">Loading...</div>

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Themes & Entities</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Themes */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <span className="text-2xl">🏷️</span> Themes
          </h2>
          {themes.length === 0 ? (
            <p className="text-accent">No themes extracted yet</p>
          ) : (
            <div className="space-y-2">
              {themes.map((theme) => (
                <div key={theme.name} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                  <span className="font-medium">{theme.name}</span>
                  <span className="bg-primary/10 text-primary px-2 py-1 rounded text-sm">
                    {theme.count} tweets
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Entities */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <span className="text-2xl">👤</span> Entities (Proper Nouns)
          </h2>
          {entities.length === 0 ? (
            <p className="text-accent">No entities extracted yet</p>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {entities.map((entity) => (
                <div key={entity.name} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                  <span className="font-medium">{entity.name}</span>
                  <span className="bg-secondary/10 text-secondary px-2 py-1 rounded text-sm">
                    {entity.count} mentions
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
