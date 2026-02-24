'use client'

import { useEffect, useState, useRef } from 'react'
import dynamic from 'next/dynamic'

const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false })

interface GraphNode {
  id: string
  name: string
  type: string
  properties?: Record<string, any>
  x?: number
  y?: number
}

interface GraphLink {
  source: string
  target: string
  type: string
}

interface GraphData {
  nodes: GraphNode[]
  links: GraphLink[]
}

const getApiUrl = () => {
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol
    const hostname = window.location.hostname
    return `${protocol}//${hostname}:8000`
  }
  return 'http://api:8000'
}

const nodeColors: Record<string, string> = {
  Tweet: '#3b82f6',
  User: '#8b5cf6',
  Hashtag: '#22c55e',
  Theme: '#f59e0b',
  Entity: '#ef4444',
  URL: '#6366f1',
}

export default function GraphPage() {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 })

  useEffect(() => {
    async function fetchData() {
      try {
        const response = await fetch(`${getApiUrl()}/graph`)
        if (!response.ok) throw new Error('Failed to fetch graph data')
        const data = await response.json()
        setGraphData(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  // Update dimensions on resize
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        setDimensions({
          width: rect.width || 800,
          height: Math.max(400, Math.min(600, window.innerHeight - 300))
        })
      }
    }
    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    return () => window.removeEventListener('resize', updateDimensions)
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="spinner mx-auto mb-4"></div>
          <p className="text-[hsl(var(--muted-foreground))]">Loading graph...</p>
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
        <h1 className="text-3xl font-bold mb-2">Graph</h1>
        <p className="text-[hsl(var(--muted-foreground))]">
          {graphData.nodes.length} nodes, {graphData.links.length} relationships
        </p>
      </div>

      {/* Legend */}
      <div className="flex gap-4 flex-wrap">
        {Object.entries(nodeColors).map(([type, color]) => (
          <div key={type} className="flex items-center gap-2">
            <div 
              className="w-3 h-3 rounded-full" 
              style={{ backgroundColor: color }}
            />
            <span className="text-sm text-[hsl(var(--muted-foreground))]">{type}</span>
          </div>
        ))}
      </div>

      {/* Graph Container */}
      <div 
        ref={containerRef}
        className="w-full rounded-xl overflow-hidden border border-[hsl(var(--border))]"
        style={{ height: dimensions.height, background: 'hsl(var(--card))' }}
      >
        {typeof window !== 'undefined' && graphData.nodes.length > 0 && (
          <ForceGraph2D
            graphData={graphData}
            width={dimensions.width}
            height={dimensions.height}
            nodeLabel={(node: any) => `${node.name} (${node.type})`}
            nodeColor={(node: any) => nodeColors[node.type] || '#666'}
            nodeVal={(node: any) => node.type === 'Tweet' ? 2 : 1}
            linkColor={() => '#444'}
            linkWidth={0.5}
            onNodeClick={(node: any) => setSelectedNode(node)}
            cooldownTicks={100}
          />
        )}
      </div>

      {/* No data message */}
      {graphData.nodes.length === 0 && (
        <div className="card text-center py-16">
          <p className="text-[hsl(var(--muted-foreground))]">No graph data available</p>
        </div>
      )}

      {/* Node Detail Card */}
      {selectedNode && (
        <div className="card space-y-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div 
                className="w-4 h-4 rounded-full"
                style={{ backgroundColor: nodeColors[selectedNode.type] || '#666' }}
              />
              <div>
                <span className="text-xs text-[hsl(var(--muted-foreground))] uppercase">
                  {selectedNode.type}
                </span>
                <h3 className="font-semibold">
                  {selectedNode.type === 'Tweet' ? 'Tweet' : selectedNode.name}
                </h3>
              </div>
            </div>
            <button 
              onClick={() => setSelectedNode(null)}
              className="text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] p-1"
            >
              ✕
            </button>
          </div>

          {/* Tweet content */}
          {selectedNode.type === 'Tweet' && selectedNode.properties?.text && (
            <div className="p-3 rounded-lg bg-[hsl(var(--secondary))]">
              <p className="text-sm leading-relaxed whitespace-pre-wrap">
                {selectedNode.properties.text.length > 400 
                  ? selectedNode.properties.text.slice(0, 400) + '...' 
                  : selectedNode.properties.text}
              </p>
            </div>
          )}

          {/* Author */}
          {selectedNode.properties?.author_username && (
            <p className="text-sm">
              <span className="text-[hsl(var(--muted-foreground))]">Author: </span>
              <span className="text-[hsl(var(--primary))]">@{selectedNode.properties.author_username}</span>
            </p>
          )}

          {/* Status */}
          {selectedNode.type === 'Tweet' && (
            <p className="text-sm">
              <span className="text-[hsl(var(--muted-foreground))]">Status: </span>
              {selectedNode.properties?.truncated ? (
                <span className="text-yellow-500">Truncated</span>
              ) : (
                <span className="text-green-500">Full Text</span>
              )}
            </p>
          )}

          {/* Link */}
          {selectedNode.properties?.bookmark_url && (
            <a
              href={selectedNode.properties.bookmark_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-primary w-full text-center text-sm"
            >
              View on X →
            </a>
          )}

          {/* Hashtag/Entity links */}
          {selectedNode.type === 'Hashtag' && (
            <a
              href={`https://x.com/search?q=%23${selectedNode.properties?.tag || selectedNode.name}`}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-primary w-full text-center text-sm"
            >
              Search #{selectedNode.properties?.tag || selectedNode.name} on X →
            </a>
          )}

          {selectedNode.type === 'User' && (
            <a
              href={`https://x.com/${selectedNode.properties?.username || selectedNode.name}`}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-primary w-full text-center text-sm"
            >
              View Profile →
            </a>
          )}
        </div>
      )}
    </div>
  )
}
