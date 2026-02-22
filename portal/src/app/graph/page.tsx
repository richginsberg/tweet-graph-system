'use client'

import { useEffect, useState } from 'react'
import dynamic from 'next/dynamic'

const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false })

interface GraphNode {
  id: string
  name: string
  type: string
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
  return process.env.API_URL || 'http://api:8000'
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
  const [hoverNode, setHoverNode] = useState<GraphNode | null>(null)

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
              className="w-4 h-4 rounded-full shadow-lg" 
              style={{ backgroundColor: color, boxShadow: `0 0 10px ${color}50` }}
            />
            <span className="text-sm text-[hsl(var(--muted-foreground))]">{type}</span>
          </div>
        ))}
      </div>

      {/* Graph */}
      <div className="graph-container">
        {typeof window !== 'undefined' && graphData.nodes.length > 0 && (
          <ForceGraph2D
            graphData={graphData}
            nodeLabel={(node: any) => `${node.name} (${node.type})`}
            nodeColor={(node: any) => nodeColors[node.type] || '#666'}
            nodeVal={(node: any) => node.type === 'Tweet' ? 2 : 1}
            linkColor={() => '#444'}
            linkWidth={0.5}
            linkDirectionalParticles={2}
            linkDirectionalParticleWidth={1}
            onNodeHover={(node: any) => setHoverNode(node)}
            cooldownTicks={100}
            nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
              const fontSize = 12 / globalScale
              ctx.font = `${fontSize}px Sans-Serif`
              ctx.fillStyle = nodeColors[node.type] || '#666'
              ctx.beginPath()
              ctx.arc(node.x, node.y, node.type === 'Tweet' ? 6 : 4, 0, 2 * Math.PI)
              ctx.fill()
              
              // Glow effect
              ctx.shadowColor = nodeColors[node.type] || '#666'
              ctx.shadowBlur = 10
              ctx.fill()
              ctx.shadowBlur = 0
            }}
          />
        )}
      </div>

      {graphData.nodes.length === 0 && (
        <div className="card text-center py-16">
          <div className="w-16 h-16 rounded-full bg-[hsl(var(--secondary))] mx-auto mb-4 flex items-center justify-center">
            <svg className="w-8 h-8 text-[hsl(var(--muted-foreground))]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5" />
            </svg>
          </div>
          <p className="text-[hsl(var(--muted-foreground))]">No graph data available</p>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-2">Add some tweets to see the graph!</p>
        </div>
      )}

      {/* Hover Info */}
      {hoverNode && (
        <div className="fixed bottom-6 right-6 card min-w-[200px]">
          <div className="flex items-center gap-3">
            <div 
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: nodeColors[hoverNode.type] || '#666' }}
            />
            <div>
              <p className="font-semibold">{hoverNode.name}</p>
              <p className="text-sm text-[hsl(var(--muted-foreground))]">{hoverNode.type}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
