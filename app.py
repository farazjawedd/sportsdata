#!/usr/bin/env python3
"""
Football Stats Web App
A beautiful interface to fetch and download football statistics for Europe's top 5 leagues.
"""

from flask import Flask, render_template, request, Response, jsonify, stream_with_context
import soccerdata as sd
import pandas as pd
from io import StringIO
import json
import time
import os

app = Flask(__name__)

# League identifiers for soccerdata
LEAGUES = {
    "epl": {"name": "Premier League", "country": "England", "id": "ENG-Premier League", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    "laliga": {"name": "La Liga", "country": "Spain", "id": "ESP-La Liga", "flag": "🇪🇸"},
    "bundesliga": {"name": "Bundesliga", "country": "Germany", "id": "GER-Bundesliga", "flag": "🇩🇪"},
    "seriea": {"name": "Serie A", "country": "Italy", "id": "ITA-Serie A", "flag": "🇮🇹"},
    "ligue1": {"name": "Ligue 1", "country": "France", "id": "FRA-Ligue 1", "flag": "🇫🇷"},
}

# Available seasons (recent ones)
SEASONS = [
    {"value": "2425", "label": "2024-25"},
    {"value": "2324", "label": "2023-24"},
    {"value": "2223", "label": "2022-23"},
    {"value": "2122", "label": "2021-22"},
    {"value": "2021", "label": "2020-21"},
]

# Data types and their stat options
DATA_TYPES = {
    "team": {
        "name": "Team Season Stats",
        "description": "Aggregated team statistics for the entire season",
        "stats": [
            {"value": "standard", "label": "Standard Stats", "desc": "Goals, assists, xG, possession"},
            {"value": "shooting", "label": "Shooting", "desc": "Shots, shot accuracy, goals per shot"},
            {"value": "passing", "label": "Passing", "desc": "Pass completion, progressive passes"},
            {"value": "passing_types", "label": "Pass Types", "desc": "Crosses, through balls, switches"},
            {"value": "goal_shot_creation", "label": "Shot Creation", "desc": "SCA, GCA actions"},
            {"value": "defense", "label": "Defense", "desc": "Tackles, interceptions, blocks"},
            {"value": "possession", "label": "Possession", "desc": "Touches, carries, dribbles"},
            {"value": "misc", "label": "Miscellaneous", "desc": "Cards, fouls, aerials"},
        ]
    },
    "player": {
        "name": "Player Season Stats",
        "description": "Individual player statistics aggregated over the season",
        "stats": [
            {"value": "standard", "label": "Standard Stats", "desc": "Goals, assists, minutes played"},
            {"value": "shooting", "label": "Shooting", "desc": "Shots, xG, shot distance"},
            {"value": "passing", "label": "Passing", "desc": "Pass completion, key passes"},
            {"value": "passing_types", "label": "Pass Types", "desc": "Crosses, through balls"},
            {"value": "goal_shot_creation", "label": "Shot Creation", "desc": "SCA, GCA per 90"},
            {"value": "defense", "label": "Defense", "desc": "Tackles, pressures, blocks"},
            {"value": "possession", "label": "Possession", "desc": "Touches, dribbles, carries"},
            {"value": "playing_time", "label": "Playing Time", "desc": "Minutes, starts, subs"},
            {"value": "misc", "label": "Miscellaneous", "desc": "Cards, fouls, recoveries"},
            {"value": "keeper", "label": "Goalkeeper", "desc": "Saves, clean sheets, GA"},
            {"value": "keeper_adv", "label": "GK Advanced", "desc": "PSxG, crosses, sweeper"},
        ]
    },
    "schedule": {
        "name": "Match Schedule",
        "description": "Match fixtures, results, and scores",
        "stats": []
    },
    "player_match": {
        "name": "Player Match Stats",
        "description": "Individual player stats for each match",
        "stats": [
            {"value": "summary", "label": "Summary", "desc": "Overall match performance"},
            {"value": "passing", "label": "Passing", "desc": "Pass stats per match"},
            {"value": "passing_types", "label": "Pass Types", "desc": "Pass type breakdown"},
            {"value": "defense", "label": "Defense", "desc": "Defensive actions"},
            {"value": "possession", "label": "Possession", "desc": "Ball control stats"},
            {"value": "misc", "label": "Miscellaneous", "desc": "Cards, fouls"},
            {"value": "keeper", "label": "Goalkeeper", "desc": "GK stats per match"},
        ]
    },
}


def get_fbref_scraper(leagues: list[str], seasons: list[str]) -> sd.FBref:
    """Create an FBref scraper instance."""
    league_ids = [LEAGUES[lg]["id"] for lg in leagues if lg in LEAGUES]
    if not league_ids:
        raise ValueError("No valid leagues provided")
    return sd.FBref(leagues=league_ids, seasons=seasons)


def fetch_data(data_type: str, leagues: list[str], seasons: list[str], stat_type: str = None, teams: list[str] = None) -> pd.DataFrame:
    """Fetch data based on parameters."""
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
    
    # Filter by teams if specified
    if teams and len(teams) > 0:
        df = filter_by_teams(df, teams)
    
    return df


def filter_by_teams(df: pd.DataFrame, teams: list[str]) -> pd.DataFrame:
    """Filter DataFrame by team names."""
    if df.index.names and 'team' in df.index.names:
        # Team is in the index
        df = df.reset_index()
        df = df[df['team'].isin(teams)]
        return df
    elif 'team' in df.columns:
        return df[df['team'].isin(teams)]
    elif 'home_team' in df.columns and 'away_team' in df.columns:
        # Schedule data
        return df[(df['home_team'].isin(teams)) | (df['away_team'].isin(teams))]
    return df


def get_teams_for_league(league: str, season: str) -> list[str]:
    """Get list of teams for a specific league and season."""
    try:
        fbref = get_fbref_scraper([league], [season])
        df = fbref.read_team_season_stats(stat_type="standard")
        
        # Extract team names from index
        if df.index.names and 'team' in df.index.names:
            teams = df.index.get_level_values('team').unique().tolist()
        elif 'team' in df.columns:
            teams = df['team'].unique().tolist()
        else:
            teams = []
        
        return sorted(teams)
    except Exception as e:
        print(f"Error fetching teams: {e}")
        return []


@app.route("/")
def index():
    """Render the main page."""
    return render_template("index.html", 
                         leagues=LEAGUES, 
                         seasons=SEASONS, 
                         data_types=DATA_TYPES)


@app.route("/api/teams", methods=["GET"])
def get_teams():
    """Get teams for a specific league and season."""
    league = request.args.get("league", "epl")
    season = request.args.get("season", "2324")
    
    teams = get_teams_for_league(league, season)
    return jsonify({"teams": teams})


@app.route("/api/stats", methods=["GET"])
def get_stats_options():
    """Return available stat types for a data type."""
    data_type = request.args.get("data_type", "team")
    if data_type in DATA_TYPES:
        return jsonify(DATA_TYPES[data_type]["stats"])
    return jsonify([])


@app.route("/api/preview", methods=["POST"])
def preview_data():
    """Preview the first few rows of data."""
    try:
        data = request.json
        leagues = data.get("leagues", ["epl"])
        seasons = data.get("seasons", ["2324"])
        data_type = data.get("data_type", "team")
        stat_type = data.get("stat_type", "standard")
        teams = data.get("teams", [])
        
        df = fetch_data(data_type, leagues, seasons, stat_type, teams if teams else None)
        
        # Flatten multi-level columns for display
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [' - '.join(col).strip(' - ') for col in df.columns.values]
        
        # Reset index for JSON serialization
        df = df.reset_index()
        
        preview = df.head(20).to_dict(orient="records")
        columns = list(df.columns)
        
        return jsonify({
            "success": True,
            "preview": preview,
            "columns": columns,
            "total_rows": len(df),
            "total_cols": len(columns)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/download", methods=["POST"])
def download_data():
    """Download data as CSV."""
    try:
        data = request.json
        leagues = data.get("leagues", ["epl"])
        seasons = data.get("seasons", ["2324"])
        data_type = data.get("data_type", "team")
        stat_type = data.get("stat_type", "standard")
        teams = data.get("teams", [])
        
        df = fetch_data(data_type, leagues, seasons, stat_type, teams if teams else None)
        
        # Flatten multi-level columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [' - '.join(col).strip(' - ') for col in df.columns.values]
        
        df = df.reset_index()
        
        # Generate filename
        leagues_str = "_".join(leagues)
        seasons_str = "_".join(seasons)
        stat_str = f"_{stat_type}" if data_type in ["team", "player", "player_match"] else ""
        teams_str = f"_{'_'.join(teams[:2])}" if teams else ""
        filename = f"{data_type}_{leagues_str}_{seasons_str}{stat_str}{teams_str}.csv"
        
        # Convert to CSV
        output = StringIO()
        df.to_csv(output, index=False)
        csv_content = output.getvalue()
        
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/fetch-progress", methods=["POST"])
def fetch_with_progress():
    """Fetch data with progress updates using Server-Sent Events."""
    data = request.json
    leagues = data.get("leagues", ["epl"])
    seasons = data.get("seasons", ["2324"])
    data_type = data.get("data_type", "team")
    stat_type = data.get("stat_type", "standard")
    teams = data.get("teams", [])
    
    def generate():
        try:
            # Stage 1: Initializing
            yield f"data: {json.dumps({'stage': 'init', 'progress': 5, 'message': 'Initializing scraper...'})}\n\n"
            time.sleep(0.3)
            
            # Stage 2: Connecting
            yield f"data: {json.dumps({'stage': 'connect', 'progress': 15, 'message': 'Connecting to FBref...'})}\n\n"
            fbref = get_fbref_scraper(leagues, seasons)
            
            # Stage 3: Fetching
            yield f"data: {json.dumps({'stage': 'fetch', 'progress': 30, 'message': f'Fetching {data_type} data...'})}\n\n"
            
            if data_type == "team":
                df = fbref.read_team_season_stats(stat_type=stat_type or "standard")
            elif data_type == "player":
                yield f"data: {json.dumps({'stage': 'fetch', 'progress': 40, 'message': 'Fetching player stats (this may take a moment)...'})}\n\n"
                df = fbref.read_player_season_stats(stat_type=stat_type or "standard")
            elif data_type == "schedule":
                df = fbref.read_schedule()
            elif data_type == "player_match":
                yield f"data: {json.dumps({'stage': 'fetch', 'progress': 40, 'message': 'Fetching match-level stats (this may take a while)...'})}\n\n"
                df = fbref.read_player_match_stats(stat_type=stat_type or "summary")
            
            yield f"data: {json.dumps({'stage': 'process', 'progress': 70, 'message': 'Processing data...'})}\n\n"
            
            # Filter by teams
            if teams and len(teams) > 0:
                df = filter_by_teams(df, teams)
            
            yield f"data: {json.dumps({'stage': 'format', 'progress': 85, 'message': 'Formatting results...'})}\n\n"
            
            # Flatten multi-level columns
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [' - '.join(col).strip(' - ') for col in df.columns.values]
            
            df = df.reset_index()
            
            yield f"data: {json.dumps({'stage': 'complete', 'progress': 100, 'message': 'Complete!'})}\n\n"
            
            # Final result
            preview = df.head(20).to_dict(orient="records")
            columns = list(df.columns)
            
            result = {
                "stage": "done",
                "success": True,
                "preview": preview,
                "columns": columns,
                "total_rows": len(df),
                "total_cols": len(columns)
            }
            yield f"data: {json.dumps(result)}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'stage': 'error', 'success': False, 'error': str(e)})}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=False)
