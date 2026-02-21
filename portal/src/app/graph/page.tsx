'use client'

import { useEffect, useState, useRef } from 'react'
import dynamic from 'next/dynamic'

// Dynamically import ForceGraph to avoid SSR issues
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false })

interface GraphNode {
  id: string
  name: string
  type: string
  val?: number
  color?: string
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

// Get API URL based on context
const getApiUrl = () => {
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol
    const hostname = window.location.hostname
    return `${protocol}//${hostname}:8000`
  }
  return process.env.API_URL || 'http://api:8000'
}

const nodeColors: Record<string, string> = {
  Tweet: '#1DA1F2',
  User: '#657786',
  Hashtag: '#17BF63',
  Theme: '#FFAD1F',
  Entity: '#E0245E',
  URL: '#794BC4',
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
      <div className="flex items-center justify-center h-96">
        <div className="text-xl">Loading graph...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-100 p-4 rounded-lg">
        <p className="text-red-800">Error: {error}</p>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-4">Tweet Graph</h1>
      
      {/* Legend */}
      <div className="flex gap-4 mb-4 flex-wrap">
        {Object.entries(nodeColors).map(([type, color]) => (
          <div key={type} className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full" style={{ backgroundColor: color }}></div>
            <span className="text-sm">{type}</span>
          </div>
        ))}
      </div>

      <div className="graph-container bg-white">
        {typeof window !== 'undefined' && graphData.nodes.length > 0 && (
          <ForceGraph2D
            graphData={graphData}
            nodeLabel={(node: any) => `${node.name} (${node.type})`}
            nodeColor={(node: any) => nodeColors[node.type] || '#999'}
            nodeVal={(node: any) => node.type === 'Tweet' ? 2 : 1}
            linkColor={() => '#ccc'}
            linkWidth={0.5}
            linkDirectionalParticles={2}
            linkDirectionalParticleWidth={1}
            onNodeHover={(node: any) => setHoverNode(node)}
            cooldownTicks={100}
            nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
              const label = node.name?.substring(0, 20) || ''
              const fontSize = 12 / globalScale
              ctx.font = `${fontSize}px Sans-Serif`
              ctx.fillStyle = nodeColors[node.type] || '#999'
              ctx.beginPath()
              ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI)
              ctx.fill()
            }}
          />
        )}
      </div>

      {graphData.nodes.length === 0 && (
        <div className="text-center text-accent mt-8">
          No graph data available. Add some tweets first!
        </div>
      )}

      {/* Hover info */}
      {hoverNode && (
        <div className="fixed bottom-4 right-4 bg-white p-4 rounded-lg shadow-lg">
          <p className="font-bold">{hoverNode.name}</p>
          <p className="text-sm text-accent">{hoverNode.type}</p>
        </div>
      )}
    </div>
  )
}
