import streamlit as st
import soccerdata as sd
import pandas as pd

st.set_page_config(
    page_title="Football Stats Lab",
    page_icon="⚽",
    layout="wide"
)

# Custom CSS for dark theme
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
    .stat-box {
        background: #1a1a25;
        border-radius: 10px;
        padding: 1rem;
        border: 1px solid #2a2a3a;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("<div class='main-header'><h1>⚽ Football Stats Lab</h1></div>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8888aa;'>Fetch stats for Europe's top 5 leagues</p>", unsafe_allow_html=True)

# League options
LEAGUES = {
    "Premier League 🏴󠁧󠁢󠁥󠁮󠁧󠁿": "ENG-Premier League",
    "La Liga 🇪🇸": "ESP-La Liga",
    "Bundesliga 🇩🇪": "GER-Bundesliga",
    "Serie A 🇮🇹": "ITA-Serie A",
    "Ligue 1 🇫🇷": "FRA-Ligue 1",
}

SEASONS = ["2324", "2223", "2122", "2021"]
SEASON_LABELS = {
    "2324": "2023-24",
    "2223": "2022-23",
    "2122": "2021-22",
    "2021": "2020-21",
}

STAT_TYPES = {
    "Team Stats": {
        "standard": "Standard Stats",
        "shooting": "Shooting",
        "passing": "Passing",
        "defense": "Defense",
        "possession": "Possession",
    },
    "Player Stats": {
        "standard": "Standard Stats",
        "shooting": "Shooting",
        "passing": "Passing",
        "defense": "Defense",
        "playing_time": "Playing Time",
        "keeper": "Goalkeeper",
    }
}

# Sidebar
with st.sidebar:
    st.header("📊 Settings")
    
    # League selection
    selected_league = st.selectbox(
        "Select League",
        options=list(LEAGUES.keys()),
        index=0
    )
    
    # Season selection
    selected_season = st.selectbox(
        "Select Season",
        options=SEASONS,
        format_func=lambda x: SEASON_LABELS[x],
        index=0
    )
    
    # Data type
    data_type = st.radio(
        "Data Type",
        options=["Team Stats", "Player Stats", "Schedule"],
        index=0
    )
    
    # Stat type (if applicable)
    if data_type in ["Team Stats", "Player Stats"]:
        stat_type = st.selectbox(
            "Stat Type",
            options=list(STAT_TYPES[data_type].keys()),
            format_func=lambda x: STAT_TYPES[data_type][x]
        )
    else:
        stat_type = None
    
    st.divider()
    
    # Fetch button
    fetch_button = st.button("🔍 Fetch Data", type="primary", use_container_width=True)


# Main content
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_data(league_id, season, data_type, stat_type):
    """Fetch data from FBref"""
    fbref = sd.FBref(leagues=[league_id], seasons=[season])
    
    if data_type == "Team Stats":
        df = fbref.read_team_season_stats(stat_type=stat_type)
    elif data_type == "Player Stats":
        df = fbref.read_player_season_stats(stat_type=stat_type)
    else:  # Schedule
        df = fbref.read_schedule()
    
    # Flatten multi-index columns
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [' - '.join(str(c) for c in col).strip(' - ') for col in df.columns]
    
    return df.reset_index()


# Display data
if fetch_button:
    league_id = LEAGUES[selected_league]
    
    with st.spinner(f"Fetching {data_type.lower()} for {selected_league}..."):
        try:
            df = fetch_data(league_id, selected_season, data_type, stat_type)
            
            # Stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Rows", f"{len(df):,}")
            with col2:
                st.metric("Columns", len(df.columns))
            with col3:
                st.metric("League", selected_league.split()[0])
            
            st.divider()
            
            # Data table
            st.dataframe(df, use_container_width=True, height=500)
            
            # Download button
            csv = df.to_csv(index=False)
            filename = f"{data_type.lower().replace(' ', '_')}_{selected_season}_{stat_type or 'schedule'}.csv"
            
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=filename,
                mime="text/csv",
                type="primary"
            )
            
        except Exception as e:
            st.error(f"Error fetching data: {str(e)}")
            st.info("Try selecting a different league/season combination.")

else:
    # Welcome message
    st.info("👈 Select options in the sidebar and click **Fetch Data** to get started!")
    
    st.markdown("""
    ### Available Data:
    - **Team Stats**: Goals, assists, xG, shooting, passing, defense, possession
    - **Player Stats**: Individual player statistics for the season
    - **Schedule**: Match fixtures and results
    
    ### Supported Leagues:
    🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League | 🇪🇸 La Liga | 🇩🇪 Bundesliga | 🇮🇹 Serie A | 🇫🇷 Ligue 1
    """)


# Footer
st.markdown("---")
st.markdown("<p style='text-align: center; color: #555;'>Data from FBref via soccerdata</p>", unsafe_allow_html=True)
