# Football Stats Lab ⚽

A beautiful web app to fetch and download football statistics for Europe's top 5 leagues.

**Live Demo**: [Deploy your own on Vercel](#deploy-to-vercel)

![Football Stats Lab](https://img.shields.io/badge/Made%20with-Flask-blue) ![Python](https://img.shields.io/badge/Python-3.9+-green)

## Supported Leagues

| Key | League |
|-----|--------|
| `epl` | English Premier League |
| `laliga` | Spanish La Liga |
| `ligue1` | French Ligue 1 |
| `bundesliga` | German Bundesliga |
| `seriea` | Italian Serie A |

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Command Line

```bash
# Fetch EPL team shooting stats for 2023-24 season
python fetch_football_stats.py --leagues epl --seasons 2324 --data team --stat shooting

# Fetch all top 5 leagues player standard stats
python fetch_football_stats.py --leagues epl laliga bundesliga seriea ligue1 --seasons 2324 --data player

# Preview data without saving
python fetch_football_stats.py --leagues epl --seasons 2324 --data schedule --preview

# Fetch schedule for multiple leagues
python fetch_football_stats.py --leagues laliga seriea --seasons 2324 --data schedule

# Fetch player match-level stats
python fetch_football_stats.py --leagues epl --seasons 2324 --data player_match --stat summary
```

### As a Python Module

```python
from fetch_football_stats import (
    fetch_team_stats,
    fetch_player_stats,
    fetch_schedule,
    fetch_player_match_stats,
)

# Fetch Premier League team shooting stats
team_shooting = fetch_team_stats(
    leagues=["epl"],
    seasons=["2324"],
    stat_type="shooting"
)

# Fetch player stats for multiple leagues
player_stats = fetch_player_stats(
    leagues=["epl", "laliga", "bundesliga"],
    seasons=["2324"],
    stat_type="standard"
)

# Get match schedule
schedule = fetch_schedule(
    leagues=["seriea"],
    seasons=["2324"]
)

# Get player match-level stats
player_match = fetch_player_match_stats(
    leagues=["ligue1"],
    seasons=["2324"],
    stat_type="summary"
)
```

## Available Stat Types

### Team Stats
- `standard` - Basic stats (goals, assists, xG, etc.)
- `shooting` - Shot-related stats
- `passing` - Passing stats
- `passing_types` - Pass type breakdown
- `goal_shot_creation` - GCA/SCA stats
- `defense` - Defensive actions
- `possession` - Ball possession stats
- `misc` - Miscellaneous stats

### Player Stats
All team stat types plus:
- `playing_time` - Minutes, starts, etc.
- `keeper` - Goalkeeper stats
- `keeper_adv` - Advanced goalkeeper stats

### Player Match Stats
- `summary` - Match summary stats
- `passing` - Passing stats per match
- `passing_types` - Pass types per match
- `defense` - Defensive actions per match
- `possession` - Possession stats per match
- `misc` - Miscellaneous stats per match
- `keeper` - Goalkeeper stats per match

## Season Format

Seasons are specified in `YYMM` format:
- `2324` = 2023-24 season
- `2223` = 2022-23 season
- `2122` = 2021-22 season

## Output

By default, data is saved as CSV files in the `output/` directory. Use `--preview` to see data in terminal without saving.

## Data Source

All data is sourced from [FBref](https://fbref.com/) via the `soccerdata` package.

---

## Web App

### Run Locally

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the web app
python app.py
```

Then open **http://localhost:5050** in your browser.

### Features

- 🏆 **Multi-league selection** - Choose from EPL, La Liga, Bundesliga, Serie A, Ligue 1
- 📅 **Multi-season support** - Fetch data from 2020-21 to 2024-25
- 🏟️ **Team filtering** - Filter stats for specific teams
- 📊 **Progress indicator** - Real-time progress updates while fetching
- 📥 **CSV download** - One-click export of all data
- 👁️ **Data preview** - See your data before downloading

---

## Deploy to Vercel

### Option 1: One-Click Deploy

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/YOUR_USERNAME/sportsdata)

### Option 2: Manual Deploy

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel**
   ```bash
   vercel login
   ```

3. **Deploy**
   ```bash
   cd /path/to/sportsdata
   vercel
   ```

4. **Follow the prompts** - Vercel will detect the Python app and deploy it.

5. **For production deployment**
   ```bash
   vercel --prod
   ```

### Project Structure for Vercel

```
sportsdata/
├── api/
│   └── index.py          # Vercel serverless function
├── vercel.json           # Vercel configuration
├── requirements.txt      # Python dependencies
├── app.py               # Local development server
├── templates/
│   └── index.html       # Local template
└── fetch_football_stats.py  # CLI tool
```

### Environment Variables (if needed)

Set these in your Vercel dashboard under Project Settings → Environment Variables:

- None required for basic functionality

### Limitations on Vercel

- **Serverless timeout**: Vercel has a 10-second timeout on the free tier (60s on Pro). Large data requests may timeout.
- **Cold starts**: First request after inactivity may be slower.
- **Recommended**: For heavy usage, consider deploying to Railway, Render, or a VPS.

### Alternative Deployment Options

| Platform | Command | Notes |
|----------|---------|-------|
| **Railway** | `railway up` | Great for Python apps |
| **Render** | Connect GitHub repo | Auto-deploys |
| **Fly.io** | `fly launch` | Global edge deployment |
| **Heroku** | `git push heroku main` | Classic PaaS |

# trigger deploy
