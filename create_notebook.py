import os
import json

cells = []

def make_md(source):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in source.split("\n")]
    }

def make_code(source):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in source.split("\n")]
    }

# Title & intro
cells.append(make_md("""# 🎾 Game Analytics: Unlocking Tennis Data with Sportradar API
### Comprehensive Relational SQL & Data Analytics Walkthrough
**Team Allocation:**
- **Ashish:** Data Extraction (API layer - Sportradar Competitions, Complexes, Doubles Rankings)
- **Nithish:** SQL Database (Relational Schema & 20 Analytical SQL Queries)
- **Dibya:** Streamlit Interactive BI Dashboard & Live Query Engine
"""))

# Setup & Imports
cells.append(make_code("""import os
import pymysql
import sqlite3
import pandas as pd
import plotly.express as px
from db_manager import run_query, SQL_QUERIES, get_table_counts

print('Libraries and Database Manager loaded successfully!')
"""))

# Database stats
cells.append(make_md("""## 1. Database Health Check & Record Counts
Connecting to both MySQL (`tennis_analytics`) and the local SQLite replica (`tennis_analytics.db`)."""))

cells.append(make_code("""counts_mysql = get_table_counts('mysql')
counts_sqlite = get_table_counts('sqlite')

df_counts = pd.DataFrame({
    'Table Name': list(counts_mysql.keys()),
    'MySQL Row Count': list(counts_mysql.values()),
    'SQLite Row Count': list(counts_sqlite.values())
})
df_counts
"""))

# Categories and competitions
cells.append(make_md("""## 2. Competitions & Category Analysis
### Query 2: Competition Count per Category"""))

cells.append(make_code("""q2_sql = '''SELECT cat.category_name, COUNT(c.competition_id) AS competition_count 
FROM competitions c
JOIN categories cat ON c.category_id = cat.category_id
GROUP BY cat.category_name
ORDER BY competition_count DESC;'''

df_q2, ms, _ = run_query(q2_sql, 'mysql')
print(f'Execution Time: {ms:.2f} ms')
display(df_q2.head(10))

fig_q2 = px.bar(df_q2, x='category_name', y='competition_count', color='competition_count',
                title='Competition Distribution by Tennis Category', template='plotly_dark')
fig_q2.show()
"""))

# Event Format Distribution
cells.append(make_md("""### Query 6: Competition Type Distribution by Category"""))
cells.append(make_code("""q6_sql = '''SELECT cat.category_name, c.type, COUNT(c.competition_id) AS type_count 
FROM competitions c
JOIN categories cat ON c.category_id = cat.category_id
GROUP BY cat.category_name, c.type
ORDER BY cat.category_name, type_count DESC;'''

df_q6, _, _ = run_query(q6_sql, 'mysql')
display(df_q6.head(10))
"""))

# Hierarchy Analysis
cells.append(make_md("""### Query 5: Parent & Sub-Competition Hierarchies (Business Use Case 1)"""))
cells.append(make_code("""q5_sql = '''SELECT parent.competition_id AS parent_competition, child.competition_name AS sub_competition 
FROM competitions child
LEFT JOIN competitions parent ON child.parent_id = parent.competition_id
WHERE child.parent_id IS NOT NULL;'''

df_q5, _, _ = run_query(q5_sql, 'mysql')
df_q5
"""))

# Venues & Complexes
cells.append(make_md("""## 3. Venues & Complexes Infrastructure
### Query 10: Chilean Venue Details"""))
cells.append(make_code("""q10_sql = '''SELECT venue_id, venue_name, city_name, country_name, timezone
FROM Venues
WHERE country_name = 'Chile';'''

df_q10, _, _ = run_query(q10_sql, 'mysql')
display(df_q10.head(10))
"""))

# Multi-court facilities
cells.append(make_md("""### Query 12: Complexes with More than One Venue"""))
cells.append(make_code("""q12_sql = '''SELECT c.complex_name, COUNT(v.venue_id) AS venue_count
FROM Complexes c
JOIN Venues v ON c.complex_id = v.complex_id
GROUP BY c.complex_name
HAVING COUNT(v.venue_id) > 1
ORDER BY venue_count DESC
LIMIT 10;'''

df_q12, _, _ = run_query(q12_sql, 'mysql')
df_q12
"""))

# Competitor Rankings
cells.append(make_md("""## 4. Competitor Rankings & Country Strength
### Query 16: Top 5 World Doubles Competitors"""))
cells.append(make_code("""q16_sql = '''SELECT c.name AS competitor_name, c.country, cr.rank, cr.points
FROM Competitors c
JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id
WHERE cr.rank <= 5
ORDER BY cr.rank ASC;'''

df_q16, _, _ = run_query(q16_sql, 'mysql')
df_q16
"""))

# Stable Rank
cells.append(make_md("""### Query 17: Stable Rank Competitors (Movement = 0)"""))
cells.append(make_code("""q17_sql = '''SELECT c.name AS competitor_name, c.country, cr.rank, cr.points
FROM Competitors c
JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id
WHERE cr.movement = 0
ORDER BY cr.rank ASC;'''

df_q17, _, _ = run_query(q17_sql, 'mysql')
display(df_q17.head(10))
"""))

# Croatia Points Spotlight
cells.append(make_md("""### Query 18: Total Ranking Points for Croatia"""))
cells.append(make_code("""q18_sql = '''SELECT c.country, SUM(cr.points) AS total_points
FROM Competitors c
JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id
WHERE c.country = 'Croatia'
GROUP BY c.country;'''

df_q18, _, _ = run_query(q18_sql, 'mysql')
df_q18
"""))

# World #1 Max Points
cells.append(make_md("""### Query 20: Highest Points Competitor in Current Week"""))
cells.append(make_code("""q20_sql = '''SELECT c.name AS competitor_name, c.country, cr.rank, cr.points
FROM Competitors c
JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id
WHERE cr.points = (
    SELECT MAX(points)
    FROM Competitor_Rankings
);'''

df_q20, _, _ = run_query(q20_sql, 'mysql')
df_q20
"""))

nb_dict = {
    "cells": cells,
    "metadata": {
        "language_info": {
            "name": "python",
            "version": "3.10"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

out_path = os.path.join(os.path.dirname(__file__), "Tennis_Analytics_Walkthrough.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb_dict, f, indent=2)

print(f"Notebook successfully generated at: {out_path}")
