#!/usr/bin/env python3
"""
Local FBref Data Scraper
Run this locally to fetch fresh data, then deploy the JSON files.
"""

import soccerdata as sd
import pandas as pd
import json
import os
from datetime import datetime

# Output directory - save directly to web app's public folder
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "web", "public", "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Leagues to fetch
LEAGUES = {
    "epl": "ENG-Premier League",
    "laliga": "ESP-La Liga",
    "bundesliga": "GER-Bundesliga",
    "seriea": "ITA-Serie A",
    "ligue1": "FRA-Ligue 1",
}

# Seasons to fetch
SEASONS = ["2324", "2223"]

# Stat types
TEAM_STATS = ["standard", "shooting", "passing", "defense", "possession"]
PLAYER_STATS = ["standard", "shooting", "passing", "defense", "keeper"]


def flatten_columns(df):
    """Flatten MultiIndex columns."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [' - '.join(str(c) for c in col).strip(' - ') for col in df.columns]
    return df


def df_to_json(df):
    """Convert DataFrame to JSON-serializable format."""
    df = flatten_columns(df.copy())
    df = df.reset_index()
    # Convert timestamps to strings
    for col in df.columns:
        if df[col].dtype == 'datetime64[ns]' or 'datetime' in str(df[col].dtype):
            df[col] = df[col].astype(str)
    # Convert to records and handle NaN
    records = df.where(pd.notnull(df), None).to_dict(orient='records')
    # Clean up any remaining non-serializable objects
    clean_records = []
    for record in records:
        clean_record = {}
        for k, v in record.items():
            if pd.isna(v) or v is None:
                clean_record[k] = None
            elif hasattr(v, 'isoformat'):  # datetime objects
                clean_record[k] = str(v)
            else:
                clean_record[k] = v
        clean_records.append(clean_record)
    columns = list(df.columns)
    return {"columns": columns, "data": clean_records}


def fetch_team_stats(league_id, league_name, season, stat_type):
    """Fetch team stats for a league/season."""
    print(f"  Fetching team {stat_type} stats...")
    try:
        fbref = sd.FBref(leagues=[league_id], seasons=[season])
        df = fbref.read_team_season_stats(stat_type=stat_type)
        return df_to_json(df)
    except Exception as e:
        print(f"    Error: {e}")
        return None


def fetch_player_stats(league_id, league_name, season, stat_type):
    """Fetch player stats for a league/season."""
    print(f"  Fetching player {stat_type} stats...")
    try:
        fbref = sd.FBref(leagues=[league_id], seasons=[season])
        df = fbref.read_player_season_stats(stat_type=stat_type)
        return df_to_json(df)
    except Exception as e:
        print(f"    Error: {e}")
        return None


def fetch_schedule(league_id, league_name, season):
    """Fetch match schedule."""
    print(f"  Fetching schedule...")
    try:
        fbref = sd.FBref(leagues=[league_id], seasons=[season])
        df = fbref.read_schedule()
        return df_to_json(df)
    except Exception as e:
        print(f"    Error: {e}")
        return None


def main():
    print("=" * 60)
    print("FBref Data Scraper")
    print("=" * 60)
    
    all_data = {
        "metadata": {
            "last_updated": datetime.now().isoformat(),
            "leagues": list(LEAGUES.keys()),
            "seasons": SEASONS,
        },
        "team_stats": {},
        "player_stats": {},
        "schedules": {},
    }
    
    for league_key, league_id in LEAGUES.items():
        print(f"\n📊 {league_key.upper()}")
        
        for season in SEASONS:
            print(f"\n  Season: {season}")
            key = f"{league_key}_{season}"
            
            # Team stats
            all_data["team_stats"][key] = {}
            for stat_type in TEAM_STATS:
                data = fetch_team_stats(league_id, league_key, season, stat_type)
                if data:
                    all_data["team_stats"][key][stat_type] = data
            
            # Player stats (only standard and shooting to save time/space)
            all_data["player_stats"][key] = {}
            for stat_type in PLAYER_STATS[:3]:  # standard, shooting, passing
                data = fetch_player_stats(league_id, league_key, season, stat_type)
                if data:
                    all_data["player_stats"][key][stat_type] = data
            
            # Schedule
            schedule = fetch_schedule(league_id, league_key, season)
            if schedule:
                all_data["schedules"][key] = schedule
    
    # Save to JSON
    output_file = os.path.join(OUTPUT_DIR, "football_data.json")
    print(f"\n💾 Saving to {output_file}...")
    
    with open(output_file, 'w') as f:
        json.dump(all_data, f)
    
    # Also save a smaller metadata file
    meta_file = os.path.join(OUTPUT_DIR, "metadata.json")
    with open(meta_file, 'w') as f:
        json.dump(all_data["metadata"], f, indent=2)
    
    print(f"\n✅ Done! Data saved to {OUTPUT_DIR}")
    print(f"   - football_data.json ({os.path.getsize(output_file) / 1024 / 1024:.1f} MB)")
    print("\nNext steps:")
    print("1. Copy the 'data' folder to your web app")
    print("2. Deploy to Vercel/Netlify/etc")


if __name__ == "__main__":
    main()

