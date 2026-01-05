#!/usr/bin/env python3
"""
Football Stats Web App - Vercel Serverless Entry Point
"""

import os

# Configure soccerdata to use /tmp for cache (Vercel's writable directory)
# Must be set BEFORE importing soccerdata
SOCCERDATA_DIR = "/tmp/soccerdata"
os.environ["SOCCERDATA_DIR"] = SOCCERDATA_DIR

# Create all necessary directories
for subdir in ["data", "data/FBref", "config", "logs"]:
    os.makedirs(os.path.join(SOCCERDATA_DIR, subdir), exist_ok=True)

# Create empty config files that soccerdata expects
config_files = {
    "config/teamname_replacements.json": "{}",
    "config/league_dict.json": "{}",
}

for filepath, content in config_files.items():
    full_path = os.path.join(SOCCERDATA_DIR, filepath)
    if not os.path.exists(full_path):
        with open(full_path, "w") as f:
            f.write(content)

from flask import Flask, request, Response, jsonify
import json
import traceback
import sys

app = Flask(__name__)

# League identifiers for soccerdata
LEAGUES = {
    "epl": {
        "name": "Premier League",
        "country": "England",
        "id": "ENG-Premier League",
        "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    },
    "laliga": {
        "name": "La Liga",
        "country": "Spain",
        "id": "ESP-La Liga",
        "flag": "🇪🇸",
    },
    "bundesliga": {
        "name": "Bundesliga",
        "country": "Germany",
        "id": "GER-Bundesliga",
        "flag": "🇩🇪",
    },
    "seriea": {
        "name": "Serie A",
        "country": "Italy",
        "id": "ITA-Serie A",
        "flag": "🇮🇹",
    },
    "ligue1": {
        "name": "Ligue 1",
        "country": "France",
        "id": "FRA-Ligue 1",
        "flag": "🇫🇷",
    },
}

SEASONS = [
    {"value": "2425", "label": "2024-25"},
    {"value": "2324", "label": "2023-24"},
    {"value": "2223", "label": "2022-23"},
    {"value": "2122", "label": "2021-22"},
    {"value": "2021", "label": "2020-21"},
]

DATA_TYPES = {
    "team": {
        "name": "Team Season Stats",
        "description": "Aggregated team statistics for the entire season",
        "stats": [
            {
                "value": "standard",
                "label": "Standard Stats",
                "desc": "Goals, assists, xG, possession",
            },
            {
                "value": "shooting",
                "label": "Shooting",
                "desc": "Shots, shot accuracy, goals per shot",
            },
            {
                "value": "passing",
                "label": "Passing",
                "desc": "Pass completion, progressive passes",
            },
            {
                "value": "passing_types",
                "label": "Pass Types",
                "desc": "Crosses, through balls, switches",
            },
            {
                "value": "goal_shot_creation",
                "label": "Shot Creation",
                "desc": "SCA, GCA actions",
            },
            {
                "value": "defense",
                "label": "Defense",
                "desc": "Tackles, interceptions, blocks",
            },
            {
                "value": "possession",
                "label": "Possession",
                "desc": "Touches, carries, dribbles",
            },
            {
                "value": "misc",
                "label": "Miscellaneous",
                "desc": "Cards, fouls, aerials",
            },
        ],
    },
    "player": {
        "name": "Player Season Stats",
        "description": "Individual player statistics aggregated over the season",
        "stats": [
            {
                "value": "standard",
                "label": "Standard Stats",
                "desc": "Goals, assists, minutes played",
            },
            {
                "value": "shooting",
                "label": "Shooting",
                "desc": "Shots, xG, shot distance",
            },
            {
                "value": "passing",
                "label": "Passing",
                "desc": "Pass completion, key passes",
            },
            {
                "value": "passing_types",
                "label": "Pass Types",
                "desc": "Crosses, through balls",
            },
            {
                "value": "goal_shot_creation",
                "label": "Shot Creation",
                "desc": "SCA, GCA per 90",
            },
            {
                "value": "defense",
                "label": "Defense",
                "desc": "Tackles, pressures, blocks",
            },
            {
                "value": "possession",
                "label": "Possession",
                "desc": "Touches, dribbles, carries",
            },
            {
                "value": "playing_time",
                "label": "Playing Time",
                "desc": "Minutes, starts, subs",
            },
            {
                "value": "misc",
                "label": "Miscellaneous",
                "desc": "Cards, fouls, recoveries",
            },
            {
                "value": "keeper",
                "label": "Goalkeeper",
                "desc": "Saves, clean sheets, GA",
            },
            {
                "value": "keeper_adv",
                "label": "GK Advanced",
                "desc": "PSxG, crosses, sweeper",
            },
        ],
    },
    "schedule": {
        "name": "Match Schedule",
        "description": "Match fixtures, results, and scores",
        "stats": [],
    },
    "player_match": {
        "name": "Player Match Stats",
        "description": "Individual player stats for each match",
        "stats": [
            {
                "value": "summary",
                "label": "Summary",
                "desc": "Overall match performance",
            },
            {"value": "passing", "label": "Passing", "desc": "Pass stats per match"},
            {
                "value": "passing_types",
                "label": "Pass Types",
                "desc": "Pass type breakdown",
            },
            {"value": "defense", "label": "Defense", "desc": "Defensive actions"},
            {
                "value": "possession",
                "label": "Possession",
                "desc": "Ball control stats",
            },
            {"value": "misc", "label": "Miscellaneous", "desc": "Cards, fouls"},
            {"value": "keeper", "label": "Goalkeeper", "desc": "GK stats per match"},
        ],
    },
}

# Lazy load modules to improve cold start
_FBref = None
_pd = None
_import_error = None


def get_fbref_class():
    global _FBref, _import_error
    if _FBref is None and _import_error is None:
        try:
            # Try direct import first
            from soccerdata import FBref

            _FBref = FBref
        except ImportError as e1:
            try:
                # Fallback: try importing the module differently
                from soccerdata.fbref import FBref

                _FBref = FBref
            except ImportError as e2:
                try:
                    # Another fallback
                    import soccerdata

                    _FBref = soccerdata.FBref
                except Exception as e3:
                    _import_error = f"Failed to import FBref: {e1}, {e2}, {e3}"

    if _import_error:
        raise ImportError(_import_error)
    return _FBref


def get_pandas():
    global _pd
    if _pd is None:
        import pandas as pd

        _pd = pd
    return _pd


# HTML Template (embedded for Vercel)
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Football Stats Lab</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a25;
            --bg-card-hover: #222230;
            --accent-primary: #00ff88;
            --accent-secondary: #00cc6a;
            --accent-glow: rgba(0, 255, 136, 0.15);
            --text-primary: #ffffff;
            --text-secondary: #8888aa;
            --text-muted: #555566;
            --border-color: #2a2a3a;
            --error: #ff4466;
            --warning: #ffaa00;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'DM Sans', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
        }
        body::before {
            content: '';
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: 
                radial-gradient(circle at 20% 80%, var(--accent-glow) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(0, 100, 255, 0.08) 0%, transparent 50%),
                linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
            z-index: -1;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 2rem; }
        header { text-align: center; padding: 3rem 0 4rem; }
        .logo { display: inline-flex; align-items: center; gap: 1rem; margin-bottom: 1rem; }
        .logo-icon {
            width: 56px; height: 56px;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            border-radius: 16px;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.8rem;
            box-shadow: 0 8px 32px var(--accent-glow);
        }
        h1 { font-size: 2.5rem; font-weight: 700; letter-spacing: -0.02em; }
        .subtitle { color: var(--text-secondary); font-size: 1.1rem; max-width: 500px; margin: 0.5rem auto 0; }
        .main-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }
        @media (max-width: 1024px) { .main-grid { grid-template-columns: 1fr; } }
        .section {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 1.75rem;
            transition: all 0.3s ease;
            animation: fadeInUp 0.5s ease forwards;
            opacity: 0;
        }
        .section:hover { border-color: var(--accent-primary); box-shadow: 0 0 40px var(--accent-glow); }
        .section:nth-child(1) { animation-delay: 0.1s; }
        .section:nth-child(2) { animation-delay: 0.2s; }
        .section:nth-child(3) { animation-delay: 0.25s; }
        .section:nth-child(4) { animation-delay: 0.3s; }
        .section:nth-child(5) { animation-delay: 0.35s; }
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .section-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.5rem; }
        .section-number {
            width: 32px; height: 32px;
            background: var(--accent-primary);
            color: var(--bg-primary);
            border-radius: 8px;
            display: flex; align-items: center; justify-content: center;
            font-weight: 700; font-size: 0.9rem;
        }
        .section-title { font-size: 1.1rem; font-weight: 600; }
        .section-subtitle { font-size: 0.8rem; color: var(--text-muted); margin-left: auto; }
        .league-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 0.75rem; }
        .league-card {
            background: var(--bg-secondary);
            border: 2px solid transparent;
            border-radius: 12px;
            padding: 1rem;
            cursor: pointer;
            transition: all 0.2s ease;
            text-align: center;
        }
        .league-card:hover { background: var(--bg-card-hover); transform: translateY(-2px); }
        .league-card.selected { border-color: var(--accent-primary); background: rgba(0, 255, 136, 0.08); }
        .league-flag { font-size: 2rem; margin-bottom: 0.5rem; }
        .league-name { font-weight: 600; font-size: 0.9rem; margin-bottom: 0.25rem; }
        .league-country { color: var(--text-muted); font-size: 0.75rem; }
        .season-grid { display: flex; flex-wrap: wrap; gap: 0.5rem; }
        .season-pill {
            background: var(--bg-secondary);
            border: 2px solid transparent;
            border-radius: 100px;
            padding: 0.6rem 1.2rem;
            cursor: pointer;
            transition: all 0.2s ease;
            font-weight: 500; font-size: 0.9rem;
        }
        .season-pill:hover { background: var(--bg-card-hover); }
        .season-pill.selected { border-color: var(--accent-primary); background: rgba(0, 255, 136, 0.08); color: var(--accent-primary); }
        .team-filter-section { grid-column: 1 / -1; }
        .team-search-wrapper { position: relative; margin-bottom: 1rem; }
        .team-search {
            width: 100%;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 0.75rem 1rem 0.75rem 2.5rem;
            font-family: 'DM Sans', sans-serif;
            font-size: 0.9rem;
            color: var(--text-primary);
            outline: none;
            transition: all 0.2s ease;
        }
        .team-search:focus { border-color: var(--accent-primary); box-shadow: 0 0 0 3px var(--accent-glow); }
        .team-search::placeholder { color: var(--text-muted); }
        .search-icon { position: absolute; left: 0.85rem; top: 50%; transform: translateY(-50%); color: var(--text-muted); }
        .team-grid { display: flex; flex-wrap: wrap; gap: 0.5rem; max-height: 200px; overflow-y: auto; padding-right: 0.5rem; }
        .team-grid::-webkit-scrollbar { width: 6px; }
        .team-grid::-webkit-scrollbar-track { background: var(--bg-secondary); border-radius: 3px; }
        .team-grid::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 3px; }
        .team-chip {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 100px;
            padding: 0.4rem 0.9rem;
            cursor: pointer;
            transition: all 0.2s ease;
            font-size: 0.8rem;
            white-space: nowrap;
        }
        .team-chip:hover { background: var(--bg-card-hover); border-color: var(--text-secondary); }
        .team-chip.selected { background: rgba(0, 255, 136, 0.15); border-color: var(--accent-primary); color: var(--accent-primary); }
        .team-loading { color: var(--text-muted); font-size: 0.85rem; padding: 1rem; text-align: center; }
        .clear-teams-btn {
            background: transparent;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 0.4rem 0.8rem;
            color: var(--text-secondary);
            font-size: 0.75rem;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .clear-teams-btn:hover { border-color: var(--error); color: var(--error); }
        .data-type-grid { display: grid; gap: 0.75rem; }
        .data-type-card {
            background: var(--bg-secondary);
            border: 2px solid transparent;
            border-radius: 12px;
            padding: 1rem 1.25rem;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        .data-type-card:hover { background: var(--bg-card-hover); }
        .data-type-card.selected { border-color: var(--accent-primary); background: rgba(0, 255, 136, 0.08); }
        .data-type-icon {
            width: 40px; height: 40px;
            background: var(--bg-card);
            border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.2rem;
        }
        .data-type-info h3 { font-size: 0.95rem; font-weight: 600; margin-bottom: 0.2rem; }
        .data-type-info p { color: var(--text-muted); font-size: 0.8rem; }
        .stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 0.6rem; }
        .stat-card {
            background: var(--bg-secondary);
            border: 2px solid transparent;
            border-radius: 10px;
            padding: 0.8rem 1rem;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .stat-card:hover { background: var(--bg-card-hover); }
        .stat-card.selected { border-color: var(--accent-primary); background: rgba(0, 255, 136, 0.08); }
        .stat-card h4 { font-size: 0.85rem; font-weight: 600; margin-bottom: 0.2rem; }
        .stat-card p { color: var(--text-muted); font-size: 0.7rem; }
        .no-stats { color: var(--text-muted); font-style: italic; padding: 1rem; text-align: center; }
        .actions { grid-column: 1 / -1; display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; padding-top: 1rem; }
        .btn {
            padding: 1rem 2.5rem;
            border-radius: 12px;
            border: none;
            font-family: 'DM Sans', sans-serif;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }
        .btn-primary {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: var(--bg-primary);
            box-shadow: 0 4px 20px var(--accent-glow);
        }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 30px var(--accent-glow); }
        .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .btn-secondary { background: var(--bg-card); color: var(--text-primary); border: 1px solid var(--border-color); }
        .btn-secondary:hover { background: var(--bg-card-hover); border-color: var(--text-secondary); }
        .progress-section { grid-column: 1 / -1; display: none; }
        .progress-section.active { display: block; }
        .progress-bar-wrapper { background: var(--bg-secondary); border-radius: 100px; height: 12px; overflow: hidden; margin-bottom: 0.75rem; }
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
            border-radius: 100px;
            width: 0%;
            transition: width 0.3s ease;
            position: relative;
        }
        .progress-bar::after {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.2) 50%, transparent 100%);
            animation: shimmer 1.5s infinite;
        }
        @keyframes shimmer { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }
        .progress-info { display: flex; justify-content: space-between; align-items: center; }
        .progress-message { color: var(--text-secondary); font-size: 0.9rem; }
        .progress-percent { font-family: 'JetBrains Mono', monospace; font-size: 1.1rem; font-weight: 700; color: var(--accent-primary); }
        .progress-stages { display: flex; gap: 0.5rem; margin-top: 1rem; }
        .progress-stage {
            flex: 1;
            text-align: center;
            padding: 0.5rem;
            background: var(--bg-secondary);
            border-radius: 8px;
            font-size: 0.75rem;
            color: var(--text-muted);
            transition: all 0.3s ease;
        }
        .progress-stage.active { background: rgba(0, 255, 136, 0.1); color: var(--accent-primary); }
        .progress-stage.complete { background: rgba(0, 255, 136, 0.2); color: var(--accent-primary); }
        .progress-stage-icon { font-size: 1.2rem; margin-bottom: 0.25rem; }
        .preview-section { grid-column: 1 / -1; margin-top: 1rem; }
        .preview-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
        .preview-stats { display: flex; gap: 1.5rem; }
        .preview-stat { text-align: center; }
        .preview-stat-value { font-family: 'JetBrains Mono', monospace; font-size: 1.5rem; font-weight: 700; color: var(--accent-primary); }
        .preview-stat-label { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
        .table-wrapper { overflow-x: auto; border-radius: 12px; border: 1px solid var(--border-color); }
        table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
        th { background: var(--bg-secondary); padding: 0.75rem 1rem; text-align: left; font-weight: 600; color: var(--text-secondary); white-space: nowrap; position: sticky; top: 0; }
        td { padding: 0.6rem 1rem; border-top: 1px solid var(--border-color); white-space: nowrap; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; }
        tr:hover td { background: var(--bg-card-hover); }
        .error-message { background: rgba(255, 68, 102, 0.1); border: 1px solid var(--error); border-radius: 12px; padding: 1rem 1.5rem; color: var(--error); display: none; margin-top: 1rem; }
        .error-message.active { display: block; }
        footer { text-align: center; padding: 3rem 0; color: var(--text-muted); font-size: 0.85rem; }
        footer a { color: var(--accent-primary); text-decoration: none; }
        footer a:hover { text-decoration: underline; }
        .warning-banner { background: rgba(255, 170, 0, 0.1); border: 1px solid var(--warning); border-radius: 12px; padding: 1rem; margin-bottom: 2rem; text-align: center; color: var(--warning); }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">
                <div class="logo-icon">⚽</div>
                <h1>Football Stats Lab</h1>
            </div>
            <p class="subtitle">Fetch and download comprehensive statistics for Europe's top 5 leagues</p>
        </header>
        <div class="warning-banner">
            ⚠️ <strong>Note:</strong> Large requests may timeout on serverless. For best results, select only 1 league and 1 season at a time.
        </div>
        <div class="main-grid">
            <div class="section">
                <div class="section-header">
                    <span class="section-number">1</span>
                    <span class="section-title">Select League</span>
                    <span class="section-subtitle" id="leagueCount">0 selected</span>
                </div>
                <div class="league-grid" id="leagueGrid"></div>
            </div>
            <div class="section">
                <div class="section-header">
                    <span class="section-number">2</span>
                    <span class="section-title">Select Season</span>
                    <span class="section-subtitle" id="seasonCount">0 selected</span>
                </div>
                <div class="season-grid" id="seasonGrid"></div>
            </div>
            <div class="section team-filter-section">
                <div class="section-header">
                    <span class="section-number">3</span>
                    <span class="section-title">Filter by Teams</span>
                    <span class="section-subtitle">(optional)</span>
                    <button class="clear-teams-btn" id="clearTeamsBtn" onclick="clearTeams()" style="display: none;">Clear All</button>
                </div>
                <div class="team-search-wrapper">
                    <span class="search-icon">🔍</span>
                    <input type="text" class="team-search" id="teamSearch" placeholder="Search teams..." oninput="filterTeams()">
                </div>
                <div class="team-grid" id="teamGrid">
                    <p class="team-loading">Select a league and season to load teams</p>
                </div>
            </div>
            <div class="section">
                <div class="section-header">
                    <span class="section-number">4</span>
                    <span class="section-title">Select Data Type</span>
                </div>
                <div class="data-type-grid" id="dataTypeGrid"></div>
            </div>
            <div class="section">
                <div class="section-header">
                    <span class="section-number">5</span>
                    <span class="section-title">Select Stat Type</span>
                </div>
                <div class="stat-grid" id="statGrid">
                    <p class="no-stats">Select a data type first</p>
                </div>
            </div>
            <div class="actions">
                <button class="btn btn-secondary" id="previewBtn" onclick="previewData()">
                    <span>👁️</span> Preview Data
                </button>
                <button class="btn btn-primary" id="downloadBtn" onclick="downloadData()">
                    <span>📥</span> Download CSV
                </button>
            </div>
            <div class="section progress-section" id="progressSection">
                <div class="section-header">
                    <span class="section-number">⏳</span>
                    <span class="section-title">Fetching Data</span>
                </div>
                <div class="progress-container">
                    <div class="progress-bar-wrapper">
                        <div class="progress-bar" id="progressBar"></div>
                    </div>
                    <div class="progress-info">
                        <span class="progress-message" id="progressMessage">Initializing...</span>
                        <span class="progress-percent" id="progressPercent">0%</span>
                    </div>
                </div>
                <div class="progress-stages">
                    <div class="progress-stage" id="stageInit"><div class="progress-stage-icon">🔧</div><div>Initialize</div></div>
                    <div class="progress-stage" id="stageConnect"><div class="progress-stage-icon">🌐</div><div>Connect</div></div>
                    <div class="progress-stage" id="stageFetch"><div class="progress-stage-icon">📥</div><div>Fetch</div></div>
                    <div class="progress-stage" id="stageProcess"><div class="progress-stage-icon">⚙️</div><div>Process</div></div>
                    <div class="progress-stage" id="stageComplete"><div class="progress-stage-icon">✅</div><div>Complete</div></div>
                </div>
            </div>
            <div class="section preview-section" id="previewSection" style="display: none;">
                <div class="preview-header">
                    <h2>Data Preview</h2>
                    <div class="preview-stats">
                        <div class="preview-stat">
                            <div class="preview-stat-value" id="totalRows">0</div>
                            <div class="preview-stat-label">Rows</div>
                        </div>
                        <div class="preview-stat">
                            <div class="preview-stat-value" id="totalCols">0</div>
                            <div class="preview-stat-label">Columns</div>
                        </div>
                    </div>
                </div>
                <div class="table-wrapper" id="tableWrapper" style="display: none;">
                    <table id="dataTable">
                        <thead id="tableHead"></thead>
                        <tbody id="tableBody"></tbody>
                    </table>
                </div>
                <div class="error-message" id="errorMessage"></div>
            </div>
        </div>
        <footer>
            <p>Data sourced from <a href="https://fbref.com" target="_blank">FBref</a> via the soccerdata package</p>
        </footer>
    </div>
    <script>
        const leagues = LEAGUES_DATA;
        const seasons = SEASONS_DATA;
        const statTypes = DATA_TYPES_DATA;
        const state = { leagues: [], seasons: [], teams: [], availableTeams: [], dataType: null, statType: null };

        document.addEventListener('DOMContentLoaded', () => {
            renderLeagues();
            renderSeasons();
            renderDataTypes();
            selectLeague('epl');
            selectSeason('2324');
            selectDataType('team');
        });

        function renderLeagues() {
            const grid = document.getElementById('leagueGrid');
            grid.innerHTML = Object.entries(leagues).map(([key, league]) => `
                <div class="league-card" data-league="${key}" onclick="selectLeague('${key}')">
                    <div class="league-flag">${league.flag}</div>
                    <div class="league-name">${league.name}</div>
                    <div class="league-country">${league.country}</div>
                </div>
            `).join('');
        }

        function renderSeasons() {
            const grid = document.getElementById('seasonGrid');
            grid.innerHTML = seasons.map(s => `
                <div class="season-pill" data-season="${s.value}" onclick="selectSeason('${s.value}')">${s.label}</div>
            `).join('');
        }

        function renderDataTypes() {
            const icons = { team: '🏆', player: '👤', schedule: '📅', player_match: '📊' };
            const grid = document.getElementById('dataTypeGrid');
            grid.innerHTML = Object.entries(statTypes).map(([key, dt]) => `
                <div class="data-type-card" data-type="${key}" onclick="selectDataType('${key}')">
                    <div class="data-type-icon">${icons[key]}</div>
                    <div class="data-type-info">
                        <h3>${dt.name}</h3>
                        <p>${dt.description}</p>
                    </div>
                </div>
            `).join('');
        }

        function selectLeague(league) {
            // Only allow single selection for serverless
            state.leagues = [league];
            document.querySelectorAll('.league-card').forEach(c => c.classList.remove('selected'));
            document.querySelector(`.league-card[data-league="${league}"]`).classList.add('selected');
            document.getElementById('leagueCount').textContent = '1 selected';
            loadTeams();
        }

        function selectSeason(season) {
            // Only allow single selection for serverless
            state.seasons = [season];
            document.querySelectorAll('.season-pill').forEach(c => c.classList.remove('selected'));
            document.querySelector(`.season-pill[data-season="${season}"]`).classList.add('selected');
            document.getElementById('seasonCount').textContent = '1 selected';
            loadTeams();
        }

        async function loadTeams() {
            const teamGrid = document.getElementById('teamGrid');
            const clearBtn = document.getElementById('clearTeamsBtn');
            if (state.leagues.length === 0 || state.seasons.length === 0) {
                teamGrid.innerHTML = '<p class="team-loading">Select a league and season to load teams</p>';
                clearBtn.style.display = 'none';
                state.availableTeams = []; state.teams = [];
                return;
            }
            teamGrid.innerHTML = '<p class="team-loading">Loading teams...</p>';
            try {
                const response = await fetch(`/api/teams?league=${state.leagues[0]}&season=${state.seasons[0]}`);
                const data = await response.json();
                if (data.error) throw new Error(data.error);
                state.availableTeams = data.teams || []; state.teams = [];
                renderTeams();
                clearBtn.style.display = state.availableTeams.length > 0 ? 'block' : 'none';
            } catch (error) { 
                teamGrid.innerHTML = '<p class="team-loading">Failed to load teams: ' + error.message + '</p>'; 
            }
        }

        function renderTeams(filter = '') {
            const teamGrid = document.getElementById('teamGrid');
            const filteredTeams = filter ? state.availableTeams.filter(t => t.toLowerCase().includes(filter.toLowerCase())) : state.availableTeams;
            if (filteredTeams.length === 0) { teamGrid.innerHTML = '<p class="team-loading">No teams found</p>'; return; }
            teamGrid.innerHTML = filteredTeams.map(team => `
                <div class="team-chip ${state.teams.includes(team) ? 'selected' : ''}" data-team="${team}" onclick="toggleTeam('${team.replace(/'/g, "\\\\'")}')">
                    ${team}
                </div>
            `).join('');
        }

        function toggleTeam(team) {
            const index = state.teams.indexOf(team);
            if (index > -1) state.teams.splice(index, 1); else state.teams.push(team);
            const chip = document.querySelector(`.team-chip[data-team="${team}"]`);
            if (chip) chip.classList.toggle('selected');
            document.getElementById('clearTeamsBtn').style.display = state.teams.length > 0 ? 'block' : 'none';
        }

        function filterTeams() { renderTeams(document.getElementById('teamSearch').value); }
        function clearTeams() {
            state.teams = [];
            document.querySelectorAll('.team-chip.selected').forEach(c => c.classList.remove('selected'));
            document.getElementById('clearTeamsBtn').style.display = 'none';
        }

        function selectDataType(type) {
            document.querySelectorAll('.data-type-card').forEach(c => c.classList.remove('selected'));
            document.querySelector(`.data-type-card[data-type="${type}"]`).classList.add('selected');
            state.dataType = type; state.statType = null;
            updateStatGrid(type);
        }

        function updateStatGrid(dataType) {
            const grid = document.getElementById('statGrid');
            const stats = statTypes[dataType].stats;
            if (stats.length === 0) { grid.innerHTML = '<p class="no-stats">No stat types available</p>'; return; }
            grid.innerHTML = stats.map((stat, i) => `
                <div class="stat-card ${i === 0 ? 'selected' : ''}" data-stat="${stat.value}" onclick="selectStat('${stat.value}')">
                    <h4>${stat.label}</h4><p>${stat.desc}</p>
                </div>
            `).join('');
            state.statType = stats[0].value;
        }

        function selectStat(stat) {
            document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('selected'));
            document.querySelector(`.stat-card[data-stat="${stat}"]`).classList.add('selected');
            state.statType = stat;
        }

        function updateProgress(progress, message, stage) {
            document.getElementById('progressBar').style.width = `${progress}%`;
            document.getElementById('progressPercent').textContent = `${progress}%`;
            document.getElementById('progressMessage').textContent = message;
            const stages = ['init', 'connect', 'fetch', 'process', 'complete'];
            const stageIndex = stages.indexOf(stage);
            stages.forEach((s, i) => {
                const el = document.getElementById(`stage${s.charAt(0).toUpperCase() + s.slice(1)}`);
                el.classList.remove('active', 'complete');
                if (i < stageIndex) el.classList.add('complete');
                else if (i === stageIndex) el.classList.add('active');
            });
        }

        function showProgress() {
            document.getElementById('progressSection').classList.add('active');
            document.getElementById('previewSection').style.display = 'none';
            updateProgress(0, 'Starting...', 'init');
        }
        function hideProgress() { document.getElementById('progressSection').classList.remove('active'); }

        async function previewData() {
            if (state.leagues.length === 0 || state.seasons.length === 0 || !state.dataType) {
                alert('Please select a league, season, and data type'); return;
            }
            showProgress();
            document.getElementById('errorMessage').classList.remove('active');
            document.getElementById('progressSection').scrollIntoView({ behavior: 'smooth' });
            
            updateProgress(10, 'Initializing...', 'init');
            await new Promise(r => setTimeout(r, 200));
            updateProgress(25, 'Connecting to FBref...', 'connect');
            
            try {
                const response = await fetch('/api/preview', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ leagues: state.leagues, seasons: state.seasons, data_type: state.dataType, stat_type: state.statType, teams: state.teams })
                });
                
                updateProgress(60, 'Fetching data...', 'fetch');
                const data = await response.json();
                updateProgress(85, 'Processing...', 'process');
                
                if (data.success) {
                    updateProgress(100, 'Complete!', 'complete');
                    await new Promise(r => setTimeout(r, 500));
                    hideProgress();
                    
                    document.getElementById('previewSection').style.display = 'block';
                    document.getElementById('totalRows').textContent = data.total_rows.toLocaleString();
                    document.getElementById('totalCols').textContent = data.total_cols;
                    
                    const thead = document.getElementById('tableHead');
                    const tbody = document.getElementById('tableBody');
                    thead.innerHTML = '<tr>' + data.columns.map(c => `<th>${c}</th>`).join('') + '</tr>';
                    tbody.innerHTML = data.preview.map(row => '<tr>' + data.columns.map(c => `<td>${row[c] ?? ''}</td>`).join('') + '</tr>').join('');
                    document.getElementById('tableWrapper').style.display = 'block';
                    document.getElementById('previewSection').scrollIntoView({ behavior: 'smooth' });
                } else { throw new Error(data.error); }
            } catch (error) {
                hideProgress();
                document.getElementById('previewSection').style.display = 'block';
                document.getElementById('tableWrapper').style.display = 'none';
                document.getElementById('errorMessage').textContent = `Error: ${error.message}`;
                document.getElementById('errorMessage').classList.add('active');
            }
        }

        async function downloadData() {
            if (state.leagues.length === 0 || state.seasons.length === 0 || !state.dataType) {
                alert('Please select a league, season, and data type'); return;
            }
            const btn = document.getElementById('downloadBtn');
            btn.disabled = true; btn.innerHTML = '<span>⏳</span> Preparing...';
            showProgress();
            
            updateProgress(20, 'Preparing download...', 'connect');
            
            try {
                const response = await fetch('/api/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ leagues: state.leagues, seasons: state.seasons, data_type: state.dataType, stat_type: state.statType, teams: state.teams })
                });
                
                updateProgress(70, 'Downloading...', 'fetch');
                
                if (response.ok) {
                    updateProgress(100, 'Complete!', 'complete');
                    const blob = await response.blob();
                    const cd = response.headers.get('Content-Disposition');
                    const filename = cd ? cd.split('filename=')[1] : 'football_stats.csv';
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a'); a.href = url; a.download = filename;
                    document.body.appendChild(a); a.click();
                    window.URL.revokeObjectURL(url); a.remove();
                } else {
                    const data = await response.json();
                    throw new Error(data.error);
                }
            } catch (error) { alert(`Download failed: ${error.message}`); }
            finally {
                hideProgress();
                btn.disabled = false; btn.innerHTML = '<span>📥</span> Download CSV';
            }
        }
    </script>
</body>
</html>"""


def get_fbref_scraper(leagues, seasons):
    FBref = get_fbref_class()
    league_ids = [LEAGUES[lg]["id"] for lg in leagues if lg in LEAGUES]
    if not league_ids:
        raise ValueError("No valid leagues provided")
    return FBref(leagues=league_ids, seasons=seasons)


def filter_by_teams(df, teams):
    pd = get_pandas()
    if df.index.names and "team" in df.index.names:
        df = df.reset_index()
        df = df[df["team"].isin(teams)]
        return df
    elif "team" in df.columns:
        return df[df["team"].isin(teams)]
    elif "home_team" in df.columns and "away_team" in df.columns:
        return df[(df["home_team"].isin(teams)) | (df["away_team"].isin(teams))]
    return df


def fetch_data(data_type, leagues, seasons, stat_type=None, teams=None):
    pd = get_pandas()
    fbref = get_fbref_scraper(leagues, seasons)

    if data_type == "team":
        df = fbref.read_team_season_stats(stat_type=stat_type or "standard")
    elif data_type == "player":
        df = fbref.read_player_season_stats(stat_type=stat_type or "standard")
    elif data_type == "schedule":
        df = fbref.read_schedule()
    elif data_type == "player_match":
        df = fbref.read_player_match_stats(stat_type=stat_type or "summary")
    else:
        raise ValueError(f"Unknown data type: {data_type}")

    if teams and len(teams) > 0:
        df = filter_by_teams(df, teams)

    return df


@app.route("/")
def index():
    html = (
        HTML_TEMPLATE.replace("LEAGUES_DATA", json.dumps(LEAGUES))
        .replace("SEASONS_DATA", json.dumps(SEASONS))
        .replace("DATA_TYPES_DATA", json.dumps(DATA_TYPES))
    )
    return html


@app.route("/api/teams", methods=["GET"])
def get_teams():
    league = request.args.get("league", "epl")
    season = request.args.get("season", "2324")

    try:
        pd = get_pandas()
        fbref = get_fbref_scraper([league], [season])
        df = fbref.read_team_season_stats(stat_type="standard")

        if df.index.names and "team" in df.index.names:
            teams = df.index.get_level_values("team").unique().tolist()
        elif "team" in df.columns:
            teams = df["team"].unique().tolist()
        else:
            teams = []

        return jsonify({"teams": sorted(teams)})
    except Exception as e:
        return jsonify({"teams": [], "error": str(e)})


@app.route("/api/preview", methods=["POST"])
def preview_data():
    try:
        pd = get_pandas()
        data = request.json
        leagues = data.get("leagues", ["epl"])
        seasons = data.get("seasons", ["2324"])
        data_type = data.get("data_type", "team")
        stat_type = data.get("stat_type", "standard")
        teams = data.get("teams", [])

        df = fetch_data(
            data_type, leagues, seasons, stat_type, teams if teams else None
        )

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [
                " - ".join(str(c) for c in col).strip(" - ")
                for col in df.columns.values
            ]

        df = df.reset_index()

        preview = df.head(20).to_dict(orient="records")
        columns = list(df.columns)

        return jsonify(
            {
                "success": True,
                "preview": preview,
                "columns": columns,
                "total_rows": len(df),
                "total_cols": len(columns),
            }
        )
    except Exception as e:
        error_details = traceback.format_exc()
        return (
            jsonify({"success": False, "error": str(e), "details": error_details}),
            400,
        )


@app.route("/api/download", methods=["POST"])
def download_data():
    try:
        pd = get_pandas()
        from io import StringIO

        data = request.json
        leagues = data.get("leagues", ["epl"])
        seasons = data.get("seasons", ["2324"])
        data_type = data.get("data_type", "team")
        stat_type = data.get("stat_type", "standard")
        teams = data.get("teams", [])

        df = fetch_data(
            data_type, leagues, seasons, stat_type, teams if teams else None
        )

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [
                " - ".join(str(c) for c in col).strip(" - ")
                for col in df.columns.values
            ]

        df = df.reset_index()

        leagues_str = "_".join(leagues)
        seasons_str = "_".join(seasons)
        stat_str = (
            f"_{stat_type}" if data_type in ["team", "player", "player_match"] else ""
        )
        teams_str = f"_{'_'.join(teams[:2])}" if teams else ""
        filename = f"{data_type}_{leagues_str}_{seasons_str}{stat_str}{teams_str}.csv"

        output = StringIO()
        df.to_csv(output, index=False)
        csv_content = output.getvalue()

        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        error_details = traceback.format_exc()
        return (
            jsonify({"success": False, "error": str(e), "details": error_details}),
            400,
        )


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint to test if the function is working."""
    status = {"status": "ok", "python_version": sys.version}

    # Test soccerdata import
    try:
        FBref = get_fbref_class()
        status["soccerdata"] = "ok"
        status["fbref_class"] = str(FBref)
    except Exception as e:
        status["soccerdata"] = f"error: {str(e)}"

    # Test pandas import
    try:
        pd = get_pandas()
        status["pandas"] = f"ok - {pd.__version__}"
    except Exception as e:
        status["pandas"] = f"error: {str(e)}"

    # List installed packages
    try:
        import pkg_resources

        installed = [f"{p.key}=={p.version}" for p in pkg_resources.working_set]
        status["installed_packages"] = sorted(
            [
                p
                for p in installed
                if any(x in p for x in ["soccer", "pandas", "lxml", "requests"])
            ]
        )
    except:
        pass

    return jsonify(status)


# For local development
if __name__ == "__main__":
    app.run(debug=True, port=5050)
