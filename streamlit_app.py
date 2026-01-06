#!/usr/bin/env python3
"""
Football Stats Lab - Streamlit Version
"""

import streamlit as st
import pandas as pd

# Page config
st.set_page_config(
    page_title="Football Stats Lab",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0a0a0f 0%, #12121a 100%);
    }
    .main-header {
        text-align: center;
        padding: 2rem 0;
    }
    .main-header h1 {
        color: #00ff88;
        font-size: 3rem;
    }
    .stButton > button {
        background: linear-gradient(135deg, #00ff88, #00cc6a);
        color: #0a0a0f;
        font-weight: bold;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 10px;
    }
    .stSelectbox, .stMultiSelect {
        background-color: #1a1a25;
    }
</style>
""", unsafe_allow_html=True)

# League data
LEAGUES = {
    "ENG-Premier League": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League",
    "ESP-La Liga": "🇪🇸 La Liga", 
    "GER-Bundesliga": "🇩🇪 Bundesliga",
    "ITA-Serie A": "🇮🇹 Serie A",
    "FRA-Ligue 1": "🇫🇷 Ligue 1",
}

SEASONS = ["2425", "2324", "2223", "2122", "2021"]
SEASON_LABELS = {
    "2425": "2024-25",
    "2324": "2023-24",
    "2223": "2022-23",
    "2122": "2021-22",
    "2021": "2020-21",
}

STAT_TYPES = {
    "team": ["standard", "shooting", "passing", "passing_types", "goal_shot_creation", "defense", "possession", "misc"],
    "player": ["standard", "shooting", "passing", "passing_types", "goal_shot_creation", "defense", "possession", "playing_time", "misc", "keeper", "keeper_adv"],
}

# Cache the soccerdata import
@st.cache_resource
def get_soccerdata():
    import soccerdata as sd
    return sd

# Cache data fetching
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_team_stats(leagues, seasons, stat_type):
    sd = get_soccerdata()
    fbref = sd.FBref(leagues=leagues, seasons=seasons)
    return fbref.read_team_season_stats(stat_type=stat_type)

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_player_stats(leagues, seasons, stat_type):
    sd = get_soccerdata()
    fbref = sd.FBref(leagues=leagues, seasons=seasons)
    return fbref.read_player_season_stats(stat_type=stat_type)

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_schedule(leagues, seasons):
    sd = get_soccerdata()
    fbref = sd.FBref(leagues=leagues, seasons=seasons)
    return fbref.read_schedule()

def flatten_columns(df):
    """Flatten multi-level column names."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [' - '.join(str(c) for c in col).strip(' - ') for col in df.columns.values]
    return df

# Header
st.markdown("""
<div class="main-header">
    <h1>⚽ Football Stats Lab</h1>
    <p style="color: #8888aa; font-size: 1.2rem;">Fetch statistics for Europe's top 5 leagues</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    # League selection
    st.subheader("1️⃣ Select Leagues")
    selected_leagues = st.multiselect(
        "Choose leagues",
        options=list(LEAGUES.keys()),
        default=["ENG-Premier League"],
        format_func=lambda x: LEAGUES[x]
    )
    
    # Season selection
    st.subheader("2️⃣ Select Seasons")
    selected_seasons = st.multiselect(
        "Choose seasons",
        options=SEASONS,
        default=["2324"],
        format_func=lambda x: SEASON_LABELS[x]
    )
    
    # Data type
    st.subheader("3️⃣ Data Type")
    data_type = st.selectbox(
        "Choose data type",
        options=["Team Stats", "Player Stats", "Schedule"],
        index=0
    )
    
    # Stat type (if applicable)
    if data_type in ["Team Stats", "Player Stats"]:
        st.subheader("4️⃣ Stat Type")
        stat_key = "team" if data_type == "Team Stats" else "player"
        stat_type = st.selectbox(
            "Choose stat type",
            options=STAT_TYPES[stat_key],
            index=0,
            format_func=lambda x: x.replace("_", " ").title()
        )
    else:
        stat_type = None

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    fetch_button = st.button("📥 Fetch Data", use_container_width=True, type="primary")

# Fetch and display data
if fetch_button:
    if not selected_leagues:
        st.error("Please select at least one league")
    elif not selected_seasons:
        st.error("Please select at least one season")
    else:
        with st.spinner("Fetching data from FBref... This may take a moment."):
            try:
                if data_type == "Team Stats":
                    df = fetch_team_stats(selected_leagues, selected_seasons, stat_type)
                elif data_type == "Player Stats":
                    df = fetch_player_stats(selected_leagues, selected_seasons, stat_type)
                else:
                    df = fetch_schedule(selected_leagues, selected_seasons)
                
                # Flatten columns and reset index
                df = flatten_columns(df)
                df = df.reset_index()
                
                # Store in session state
                st.session_state['data'] = df
                st.session_state['data_type'] = data_type
                st.session_state['stat_type'] = stat_type
                
                st.success(f"✅ Fetched {len(df):,} rows!")
                
            except Exception as e:
                st.error(f"Error fetching data: {str(e)}")

# Display data if available
if 'data' in st.session_state:
    df = st.session_state['data']
    
    st.markdown("---")
    
    # Stats
    col1, col2, col3 = st.columns(3)
    col1.metric("📊 Rows", f"{len(df):,}")
    col2.metric("📋 Columns", f"{len(df.columns)}")
    col3.metric("📁 Data Type", st.session_state.get('data_type', 'N/A'))
    
    # Data preview
    st.subheader("📋 Data Preview")
    st.dataframe(df.head(100), use_container_width=True, height=400)
    
    # Download button
    csv = df.to_csv(index=False)
    filename = f"{st.session_state.get('data_type', 'data').lower().replace(' ', '_')}_{st.session_state.get('stat_type', 'stats')}.csv"
    
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=filename,
        mime="text/csv",
        use_container_width=True
    )

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #555566; padding: 1rem;">
    Data sourced from <a href="https://fbref.com" target="_blank" style="color: #00ff88;">FBref</a> via the soccerdata package
</div>
""", unsafe_allow_html=True)

