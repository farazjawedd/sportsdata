'use client'

import { useState, useEffect } from 'react'
import footballDataRaw from '../public/data/football_data.json'
const footballData = footballDataRaw as unknown as FootballData

const LEAGUES = [
  { id: 'epl', name: 'Premier League' },
  { id: 'laliga', name: 'La Liga' },
  { id: 'bundesliga', name: 'Bundesliga' },
  { id: 'seriea', name: 'Serie A' },
  { id: 'ligue1', name: 'Ligue 1' },
]

const SEASONS = [
  { id: '2324', name: '2023-24' },
  { id: '2223', name: '2022-23' },
]

const DATA_TYPES = [
  { id: 'team', name: 'Team Stats' },
  { id: 'player', name: 'Player Stats' },
  { id: 'schedule', name: 'Schedule' },
]

const STAT_TYPES: Record<string, { id: string; name: string }[]> = {
  team: [
    { id: 'standard', name: 'Standard' },
    { id: 'shooting', name: 'Shooting' },
    { id: 'passing', name: 'Passing' },
    { id: 'defense', name: 'Defense' },
    { id: 'possession', name: 'Possession' },
  ],
  player: [
    { id: 'standard', name: 'Standard' },
    { id: 'shooting', name: 'Shooting' },
    { id: 'passing', name: 'Passing' },
  ],
  schedule: [],
}

type DataRow = Record<string, unknown>
type StatsData = { columns: string[]; data: DataRow[] }
type FootballData = {
  metadata: { last_updated: string | null; leagues: string[]; seasons: string[] }
  team_stats: Record<string, Record<string, StatsData>>
  player_stats: Record<string, Record<string, StatsData>>
  schedules: Record<string, StatsData>
}

export default function Home() {
  const [league, setLeague] = useState('epl')
  const [season, setSeason] = useState('2324')
  const [dataType, setDataType] = useState('team')
  const [statType, setStatType] = useState('standard')
  const [data, setData] = useState<DataRow[]>([])
  const [columns, setColumns] = useState<string[]>([])
  const [error, setError] = useState('')

  const loadData = () => {
    setError('')
    const key = `${league}_${season}`
    
    try {
      let result: StatsData | null = null
      
      if (dataType === 'team') {
        result = footballData.team_stats[key]?.[statType] || null
      } else if (dataType === 'player') {
        result = footballData.player_stats[key]?.[statType] || null
      } else {
        result = footballData.schedules[key] || null
      }
      
      if (result) {
        setColumns(result.columns)
        setData(result.data)
      } else {
        setError('No data available for this selection. Run the scraper to fetch data.')
        setColumns([])
        setData([])
      }
    } catch (e) {
      setError('Failed to load data')
      console.error(e)
    }
  }

  useEffect(() => {
    loadData()
  }, [league, season, dataType, statType])

  const downloadCSV = () => {
    if (data.length === 0) return
    
    const headers = columns.join(',')
    const rows = data.map(row => 
      columns.map(col => {
        const val = row[col]
        if (typeof val === 'string' && (val.includes(',') || val.includes('"'))) {
          return `"${String(val).replace(/"/g, '""')}"`
        }
        return val ?? ''
      }).join(',')
    )
    
    const csv = [headers, ...rows].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${dataType}_${league}_${season}_${statType || 'schedule'}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const metadata = footballData.metadata

  return (
    <div className="container">
      <header>
        <h1>⚽ Football Stats Hub</h1>
        <p>FBref data for Europe&apos;s top 5 leagues</p>
      </header>

      <div className="controls">
        <select value={league} onChange={e => setLeague(e.target.value)}>
          {LEAGUES.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
        </select>
        
        <select value={season} onChange={e => setSeason(e.target.value)}>
          {SEASONS.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        
        <select value={dataType} onChange={e => { setDataType(e.target.value); setStatType('standard'); }}>
          {DATA_TYPES.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        
        {STAT_TYPES[dataType]?.length > 0 && (
          <select value={statType} onChange={e => setStatType(e.target.value)}>
            {STAT_TYPES[dataType].map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        )}
      </div>

      {error && <div className="error">{error}</div>}

      {data.length > 0 && (
        <>
          <div className="stats">
            <div className="stat-box">
              <div className="value">{data.length}</div>
              <div className="label">Rows</div>
            </div>
            <div className="stat-box">
              <div className="value">{columns.length}</div>
              <div className="label">Columns</div>
            </div>
          </div>

          <div className="table-container">
            <table>
              <thead>
                <tr>
                  {columns.slice(0, 12).map(col => <th key={col}>{col}</th>)}
                  {columns.length > 12 && <th>...</th>}
                </tr>
              </thead>
              <tbody>
                {data.slice(0, 50).map((row, i) => (
                  <tr key={i}>
                    {columns.slice(0, 12).map(col => (
                      <td key={col}>{String(row[col] ?? '')}</td>
                    ))}
                    {columns.length > 12 && <td>...</td>}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button className="download-btn" onClick={downloadCSV}>
            ⬇️ Download CSV ({data.length} rows)
          </button>
        </>
      )}

      <p className="meta">
        Last updated: {metadata?.last_updated ? new Date(metadata.last_updated).toLocaleDateString() : 'Unknown'}
        {' • '}Data from FBref
      </p>
    </div>
  )
}

