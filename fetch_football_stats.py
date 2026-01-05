#!/usr/bin/env python3
"""
Football Stats Fetcher for Europe's Top 5 Leagues
Uses soccerdata package to fetch team and player statistics from FBref.

Supported Leagues:
  - English Premier League
  - Spanish La Liga
  - French Ligue 1
  - German Bundesliga
  - Italian Serie A
"""

import argparse
import soccerdata as sd
import pandas as pd
from pathlib import Path


# League identifiers for soccerdata
LEAGUES = {
    "epl": "ENG-Premier League",
    "laliga": "ESP-La Liga",
    "ligue1": "FRA-Ligue 1",
    "bundesliga": "GER-Bundesliga",
    "seriea": "ITA-Serie A",
}

# Available stat types for teams and players
TEAM_STAT_TYPES = [
    "standard",
    "shooting",
    "passing",
    "passing_types",
    "goal_shot_creation",
    "defense",
    "possession",
    "misc",
]

PLAYER_STAT_TYPES = [
    "standard",
    "shooting",
    "passing",
    "passing_types",
    "goal_shot_creation",
    "defense",
    "possession",
    "playing_time",
    "misc",
    "keeper",
    "keeper_adv",
]


def get_fbref_scraper(leagues: list[str], seasons: list[str]) -> sd.FBref:
    """
    Create an FBref scraper instance for specified leagues and seasons.

    Args:
        leagues: List of league keys (e.g., ['epl', 'laliga'])
        seasons: List of seasons in format ['2324', '2223'] for 2023-24, 2022-23

    Returns:
        FBref scraper instance
    """
    league_ids = [LEAGUES[lg.lower()] for lg in leagues if lg.lower() in LEAGUES]

    if not league_ids:
        raise ValueError(
            f"No valid leagues provided. Choose from: {list(LEAGUES.keys())}"
        )

    return sd.FBref(leagues=league_ids, seasons=seasons)


def fetch_team_stats(
    leagues: list[str], seasons: list[str], stat_type: str = "standard"
) -> pd.DataFrame:
    """
    Fetch team season statistics.

    Args:
        leagues: List of league keys
        seasons: List of seasons
        stat_type: Type of stats (standard, shooting, passing, etc.)

    Returns:
        DataFrame with team statistics
    """
    fbref = get_fbref_scraper(leagues, seasons)
    return fbref.read_team_season_stats(stat_type=stat_type)


def fetch_player_stats(
    leagues: list[str], seasons: list[str], stat_type: str = "standard"
) -> pd.DataFrame:
    """
    Fetch player season statistics.

    Args:
        leagues: List of league keys
        seasons: List of seasons
        stat_type: Type of stats (standard, shooting, passing, etc.)

    Returns:
        DataFrame with player statistics
    """
    fbref = get_fbref_scraper(leagues, seasons)
    return fbref.read_player_season_stats(stat_type=stat_type)


def fetch_schedule(leagues: list[str], seasons: list[str]) -> pd.DataFrame:
    """
    Fetch match schedule/results.

    Args:
        leagues: List of league keys
        seasons: List of seasons

    Returns:
        DataFrame with match schedule
    """
    fbref = get_fbref_scraper(leagues, seasons)
    return fbref.read_schedule()


def fetch_player_match_stats(
    leagues: list[str], seasons: list[str], stat_type: str = "summary"
) -> pd.DataFrame:
    """
    Fetch player match-level statistics.

    Args:
        leagues: List of league keys
        seasons: List of seasons
        stat_type: Type of stats (summary, passing, defense, etc.)

    Returns:
        DataFrame with player match statistics
    """
    fbref = get_fbref_scraper(leagues, seasons)
    return fbref.read_player_match_stats(stat_type=stat_type)


def save_to_csv(df: pd.DataFrame, filename: str, output_dir: str = "output") -> str:
    """
    Save DataFrame to CSV file.

    Args:
        df: DataFrame to save
        filename: Output filename
        output_dir: Output directory

    Returns:
        Full path to saved file
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    filepath = output_path / filename
    df.to_csv(filepath)
    return str(filepath)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch football stats for Europe's top 5 leagues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch EPL team shooting stats for 2023-24 season
  python fetch_football_stats.py --leagues epl --seasons 2324 --data team --stat shooting

  # Fetch all top 5 leagues player standard stats
  python fetch_football_stats.py --leagues epl laliga bundesliga seriea ligue1 --seasons 2324 --data player

  # Fetch schedule for La Liga and Serie A
  python fetch_football_stats.py --leagues laliga seriea --seasons 2324 --data schedule

  # Fetch player match-level stats
  python fetch_football_stats.py --leagues epl --seasons 2324 --data player_match --stat summary

Available leagues: epl, laliga, ligue1, bundesliga, seriea
Available team stat types: standard, shooting, passing, passing_types, goal_shot_creation, defense, possession, misc
Available player stat types: standard, shooting, passing, passing_types, goal_shot_creation, defense, possession, playing_time, misc, keeper, keeper_adv
Available player match stat types: summary, passing, passing_types, defense, possession, misc, keeper
        """,
    )

    parser.add_argument(
        "--leagues",
        "-l",
        nargs="+",
        default=["epl"],
        choices=list(LEAGUES.keys()),
        help="League(s) to fetch data for",
    )

    parser.add_argument(
        "--seasons",
        "-s",
        nargs="+",
        default=["2324"],
        help="Season(s) in format YYMM (e.g., 2324 for 2023-24)",
    )

    parser.add_argument(
        "--data",
        "-d",
        choices=["team", "player", "schedule", "player_match"],
        default="team",
        help="Type of data to fetch",
    )

    parser.add_argument(
        "--stat", "-t", default="standard", help="Stat type for team/player data"
    )

    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output CSV filename (auto-generated if not provided)",
    )

    parser.add_argument(
        "--preview",
        "-p",
        action="store_true",
        help="Preview first 10 rows instead of saving",
    )

    args = parser.parse_args()

    print(f"Fetching {args.data} data for {args.leagues} - seasons {args.seasons}...")

    try:
        if args.data == "team":
            df = fetch_team_stats(args.leagues, args.seasons, args.stat)
        elif args.data == "player":
            df = fetch_player_stats(args.leagues, args.seasons, args.stat)
        elif args.data == "schedule":
            df = fetch_schedule(args.leagues, args.seasons)
        elif args.data == "player_match":
            df = fetch_player_match_stats(args.leagues, args.seasons, args.stat)

        if args.preview:
            print(f"\n{df.shape[0]} rows, {df.shape[1]} columns")
            print("\nColumns:", list(df.columns))
            print("\nPreview (first 10 rows):")
            pd.set_option("display.max_columns", None)
            pd.set_option("display.width", None)
            print(df.head(10))
        else:
            # Generate filename if not provided
            if args.output:
                filename = args.output
            else:
                leagues_str = "_".join(args.leagues)
                seasons_str = "_".join(args.seasons)
                stat_str = (
                    f"_{args.stat}"
                    if args.data in ["team", "player", "player_match"]
                    else ""
                )
                filename = f"{args.data}_{leagues_str}_{seasons_str}{stat_str}.csv"

            filepath = save_to_csv(df, filename)
            print(f"Data saved to: {filepath}")
            print(f"Shape: {df.shape[0]} rows, {df.shape[1]} columns")

    except Exception as e:
        print(f"Error fetching data: {e}")
        raise


if __name__ == "__main__":
    main()
