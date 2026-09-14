import os
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text

# Page Setup
st.set_page_config(
    page_title="Tennis Event & Rankings Explorer",
    page_icon="🎾",
    layout="wide"
)

# ---------------------------------------------------------
# DYNAMIC DATABASE ENGINE & SCHEMA DETECTION
# ---------------------------------------------------------
@st.cache_resource
def get_db_info():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "tennis.db")
    
    # 1. Check if database file exists
    if not os.path.exists(db_path):
        return None, None, f"Database file not found at path: `{db_path}`. Ensure `tennis.db` is committed to GitHub."
    
    # 2. Inspect table names directly via sqlite3 to handle case-sensitivity dynamically
    try:
        conn_check = sqlite3.connect(db_path)
        cursor = conn_check.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        raw_tables = [row[0] for row in cursor.fetchall()]
        conn_check.close()
        
        if not raw_tables:
            return None, None, "Database file exists, but it contains 0 tables! Your uploaded `tennis.db` might be empty."
        
        # Build mapping for table names (case-insensitive lookup)
        table_map = {t.lower(): t for t in raw_tables}
        engine = create_engine(f"sqlite:///{db_path}")
        
        return engine, table_map, None
    except Exception as e:
        return None, None, f"Error inspecting database file: {e}"

engine, TABLES, db_error = get_db_info()

# Display database load error if initialization fails
if db_error:
    st.error("❌ Database Initialization Failed")
    st.warning(db_error)
    st.info("💡 **Fix:** Force upload your local populated `tennis.db` using: `git add -f tennis.db` then commit & push.")
    st.stop()

# Helper function to get exact table name regardless of casing
def get_tbl(name):
    return TABLES.get(name.lower(), name)

def run_query(query, params=None):
    try:
        with engine.connect() as conn:
            return pd.read_sql(text(query), conn, params=params)
    except Exception as e:
        st.error(f"⚠️ Query Execution Failed: {e}")
        st.stop()

# ---------------------------------------------------------
# HEADER SECTION
# ---------------------------------------------------------
st.title("🎾 Tennis Event & Rankings Explorer")
st.markdown("Real-time sports analytics powered by Sportradar API and SQL database.")

# Sidebar Controls
st.sidebar.header("Navigation & Filters")
app_mode = st.sidebar.radio("Select View Mode", [
    "Homepage Dashboard", 
    "Search & Filter Competitors", 
    "Country-Wise Analysis", 
    "Venues & Complexes Explorer",
    "Mandatory SQL Queries"
])

# Resolve exact table names from database schema
TBL_COMPETITORS = get_tbl("Competitors")
TBL_RANKINGS = get_tbl("Competitor_Rankings")
TBL_VENUES = get_tbl("Venues")
TBL_COMPLEXES = get_tbl("Complexes")
TBL_CATEGORIES = get_tbl("Categories")
TBL_COMPETITIONS = get_tbl("Competitions")

# ---------------------------------------------------------
# VIEW 1: HOMEPAGE DASHBOARD
# ---------------------------------------------------------
if app_mode == "Homepage Dashboard":
    st.header("🏆 Executive Summary Dashboard")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_comp = run_query(f"SELECT COUNT(*) AS total FROM {TBL_COMPETITORS}")['total'].iloc[0]
    total_countries = run_query(f"SELECT COUNT(DISTINCT country) AS total FROM {TBL_COMPETITORS}")['total'].iloc[0]
    max_pts = run_query(f"SELECT MAX(points) AS total FROM {TBL_RANKINGS}")['total'].iloc[0]
    total_venues = run_query(f"SELECT COUNT(*) AS total FROM {TBL_VENUES}")['total'].iloc[0]
    
    col1.metric("Total Competitors", f"{total_comp:,}")
    col2.metric("Countries Represented", f"{total_countries}")
    col3.metric("Highest Ranking Points", f"{max_pts:,}")
    col4.metric("Total Venues Registered", f"{total_venues:,}")
    
    st.divider()
    
    st.subheader("Top 10 Ranked Competitors")
    top_10_df = run_query(f"""
        SELECT c.name AS Competitor, c.country AS Country, r.rank AS Rank, r.points AS Points, r.competitions_played AS [Played]
        FROM {TBL_COMPETITORS} c
        JOIN {TBL_RANKINGS} r ON c.competitor_id = r.competitor_id
        ORDER BY r.rank ASC
        LIMIT 10
    """)
    st.dataframe(top_10_df, use_container_width=True)
    
    # Leaderboard Visualization
    fig = px.bar(
        top_10_df, 
        x="Competitor", 
        y="Points", 
        color="Country",
        title="Top 10 Competitors by Ranking Points",
        text_auto=True
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# VIEW 2: SEARCH & FILTER COMPETITORS
# ---------------------------------------------------------
elif app_mode == "Search & Filter Competitors":
    st.header("🔍 Search & Filter Competitors")
    
    st.sidebar.subheader("Filter Parameters")
    search_name = st.sidebar.text_input("Search Competitor Name", "")
    
    # Dynamic Rank Range Slider
    min_rank, max_rank = run_query(f"SELECT MIN(rank) AS min_r, MAX(rank) AS max_r FROM {TBL_RANKINGS}").iloc[0]
    rank_range = st.sidebar.slider("Rank Range", int(min_rank), int(max_rank), (1, 50))
    
    # Query Data
    query = f"""
        SELECT c.name AS Competitor, c.country AS Country, c.abbreviation AS Code,
               r.rank AS Rank, r.movement AS Movement, r.points AS Points, r.competitions_played AS [Competitions Played]
        FROM {TBL_COMPETITORS} c
        JOIN {TBL_RANKINGS} r ON c.competitor_id = r.competitor_id
        WHERE r.rank BETWEEN :min_r AND :max_r
    """
    params = {"min_r": rank_range[0], "max_r": rank_range[1]}
    
    if search_name:
        query += " AND c.name LIKE :search"
        params["search"] = f"%{search_name}%"
        
    query += " ORDER BY r.rank ASC"
    
    df_filtered = run_query(query, params)
    st.markdown(f"Found **{len(df_filtered)}** competitors matching criteria:")
    st.dataframe(df_filtered, use_container_width=True)

# ---------------------------------------------------------
# VIEW 3: COUNTRY-WISE ANALYSIS
# ---------------------------------------------------------
elif app_mode == "Country-Wise Analysis":
    st.header("🌍 Country-Wise Performance Analysis")
    
    country_df = run_query(f"""
        SELECT c.country AS Country, 
               COUNT(c.competitor_id) AS Total_Competitors, 
               AVG(r.points) AS Avg_Points,
               SUM(r.points) AS Total_Points
        FROM {TBL_COMPETITORS} c
        JOIN {TBL_RANKINGS} r ON c.competitor_id = r.competitor_id
        GROUP BY c.country
        ORDER BY Total_Competitors DESC
    """)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Country Distribution Data")
        st.dataframe(country_df, use_container_width=True)
        
    with col2:
        st.subheader("Top 10 Countries by Player Representation")
        fig = px.pie(
            country_df.head(10), 
            names="Country", 
            values="Total_Competitors", 
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# VIEW 4: VENUES & COMPLEXES EXPLORER
# ---------------------------------------------------------
elif app_mode == "Venues & Complexes Explorer":
    st.header("🏟️ Venues & Complexes Explorer")
    
    venues_df = run_query(f"""
        SELECT v.venue_name AS Venue, v.city_name AS City, v.country_name AS Country, v.timezone AS Timezone, c.complex_name AS Complex
        FROM {TBL_VENUES} v
        JOIN {TBL_COMPLEXES} c ON v.complex_id = c.complex_id
    """)
    
    st.dataframe(venues_df, use_container_width=True)
    
    fig = px.histogram(
        venues_df, 
        x="Country", 
        title="Distribution of Venues Across Countries",
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# VIEW 5: MANDATORY SQL QUERIES EXECUTION
# ---------------------------------------------------------
elif app_mode == "Mandatory SQL Queries":
    st.header("💻 Execute Mandatory Project Queries")
    
    query_option = st.selectbox("Select Project Query to Run", [
        "1. List all competitions along with their category name",
        "2. Count the number of competitions in each category",
        "3. Find all competitions of type 'doubles'",
        "4. List all venues along with their associated complex name",
        "5. Count the number of venues in each complex",
        "6. Find complexes that have more than one venue",
        "7. Get all competitors with their rank and points",
        "8. Find competitors ranked in the top 5",
        "9. List competitors with no rank movement (stable rank)",
        "10. Count the number of competitors per country"
    ])
    
    sql_map = {
        "1. List all competitions along with their category name": 
            f"SELECT c.competition_id, c.competition_name, c.type, cat.category_name FROM {TBL_COMPETITIONS} c JOIN {TBL_CATEGORIES} cat ON c.category_id = cat.category_id",
            
        "2. Count the number of competitions in each category": 
            f"SELECT cat.category_name, COUNT(c.competition_id) AS total_competitions FROM {TBL_CATEGORIES} cat LEFT JOIN {TBL_COMPETITIONS} c ON cat.category_id = c.category_id GROUP BY cat.category_name ORDER BY total_competitions DESC",
            
        "3. Find all competitions of type 'doubles'": 
            f"SELECT competition_id, competition_name, type, gender FROM {TBL_COMPETITIONS} WHERE type = 'doubles'",
            
        "4. List all venues along with their associated complex name": 
            f"SELECT v.venue_name, v.city_name, v.country_name, c.complex_name FROM {TBL_VENUES} v JOIN {TBL_COMPLEXES} c ON v.complex_id = c.complex_id",
            
        "5. Count the number of venues in each complex": 
            f"SELECT c.complex_name, COUNT(v.venue_id) AS venue_count FROM {TBL_COMPLEXES} c LEFT JOIN {TBL_VENUES} v ON c.complex_id = v.complex_id GROUP BY c.complex_name ORDER BY venue_count DESC",
            
        "6. Find complexes that have more than one venue": 
            f"SELECT c.complex_name, COUNT(v.venue_id) AS venue_count FROM {TBL_COMPLEXES} c JOIN {TBL_VENUES} v ON c.complex_id = v.complex_id GROUP BY c.complex_id, c.complex_name HAVING COUNT(v.venue_id) > 1",
            
        "7. Get all competitors with their rank and points": 
            f"SELECT comp.name, comp.country, r.rank, r.points FROM {TBL_COMPETITORS} comp JOIN {TBL_RANKINGS} r ON comp.competitor_id = r.competitor_id ORDER BY r.rank ASC",
            
        "8. Find competitors ranked in the top 5": 
            f"SELECT comp.name, comp.country, r.rank, r.points FROM {TBL_COMPETITORS} comp JOIN {TBL_RANKINGS} r ON comp.competitor_id = r.competitor_id WHERE r.rank <= 5 ORDER BY r.rank ASC",
            
        "9. List competitors with no rank movement (stable rank)": 
            f"SELECT comp.name, comp.country, r.rank, r.movement FROM {TBL_COMPETITORS} comp JOIN {TBL_RANKINGS} r ON comp.competitor_id = r.competitor_id WHERE r.movement = 0",
            
        "10. Count the number of competitors per country": 
            f"SELECT country, COUNT(competitor_id) AS competitor_count FROM {TBL_COMPETITORS} GROUP BY country ORDER BY competitor_count DESC"
    }
    
    selected_query = sql_map[query_option]
    st.code(selected_query, language="sql")
    
    res_df = run_query(selected_query)
    st.write(f"Returned **{len(res_df)}** rows:")
    st.dataframe(res_df, use_container_width=True)
