import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Link from 'next/link'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Tweet Graph Portal',
  description: 'Visualize and explore your tweet graph database',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <nav className="bg-secondary text-white p-4">
          <div className="container mx-auto flex items-center justify-between">
            <Link href="/" className="text-xl font-bold text-primary">
              Tweet Graph
            </Link>
            <div className="flex gap-6">
              <Link href="/" className="hover:text-primary">Dashboard</Link>
              <Link href="/graph" className="hover:text-primary">Graph</Link>
              <Link href="/tweets" className="hover:text-primary">Tweets</Link>
              <Link href="/search" className="hover:text-primary">Search</Link>
              <Link href="/themes" className="hover:text-primary">Themes</Link>
            </div>
          </div>
        </nav>
        <main className="container mx-auto p-4">
          {children}
        </main>
      </body>
    </html>
  )
}
