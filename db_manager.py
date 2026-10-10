import os
import sqlite3
import time
import warnings
import pandas as pd
import pymysql
from sqlalchemy import create_engine

warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH = os.path.join(BASE_DIR, "tennis_analytics.db")

MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "DibyaSQL@0911",
    "database": "tennis_analytics",
    "port": 3306
}

# The 20 Required SQL Queries from Nithish
SQL_QUERIES = [
    {
        "id": 1,
        "category": "Competitions & Categories",
        "title": "List all competitions along with their category name",
        "desc": "Joins competitions with their parent category to provide a unified tournament classification view.",
        "sql_mysql": """SELECT c.competition_id, c.competition_name, cat.category_name
FROM competitions AS c
JOIN categories AS cat ON c.category_id = cat.category_id;""",
        "sql_sqlite": """SELECT c.competition_id, c.competition_name, cat.category_name
FROM competitions AS c
JOIN categories AS cat ON c.category_id = cat.category_id;""",
        "chart_type": "table"
    },
    {
        "id": 2,
        "category": "Competitions & Categories",
        "title": "Count the number of competitions in each category",
        "desc": "Aggregates tournament distribution across tennis levels (ITF Men, ITF Women, Challenger, ATP, WTA).",
        "sql_mysql": """SELECT cat.category_name, COUNT(c.competition_id) AS competition_count 
FROM competitions c
JOIN categories cat ON c.category_id = cat.category_id
GROUP BY cat.category_name
ORDER BY competition_count DESC;""",
        "sql_sqlite": """SELECT cat.category_name, COUNT(c.competition_id) AS competition_count 
FROM competitions c
JOIN categories cat ON c.category_id = cat.category_id
GROUP BY cat.category_name
ORDER BY competition_count DESC;""",
        "chart_type": "bar",
        "x": "category_name",
        "y": "competition_count"
    },
    {
        "id": 3,
        "category": "Competitions & Categories",
        "title": "Find all competitions of type 'doubles'",
        "desc": "Filters the tournament catalog specifically for doubles events.",
        "sql_mysql": """SELECT c.competition_id, c.competition_name, cat.category_name 
FROM competitions c
JOIN categories cat ON c.category_id = cat.category_id
WHERE c.type = 'doubles';""",
        "sql_sqlite": """SELECT c.competition_id, c.competition_name, cat.category_name 
FROM competitions c
JOIN categories cat ON c.category_id = cat.category_id
WHERE c.type = 'doubles';""",
        "chart_type": "table"
    },
    {
        "id": 4,
        "category": "Competitions & Categories",
        "title": "Get competitions that belong to a specific category (e.g., ITF Men)",
        "desc": "Retrieves all tournaments governed under the ITF Men circuit.",
        "sql_mysql": """SELECT c.competition_id, c.competition_name 
FROM competitions c
JOIN categories cat ON c.category_id = cat.category_id
WHERE cat.category_name = 'ITF Men';""",
        "sql_sqlite": """SELECT c.competition_id, c.competition_name 
FROM competitions c
JOIN categories cat ON c.category_id = cat.category_id
WHERE cat.category_name = 'ITF Men';""",
        "chart_type": "table"
    },
    {
        "id": 5,
        "category": "Competitions & Categories",
        "title": "Identify parent competitions and their sub-competitions",
        "desc": "Maps competition hierarchies linking main parent events to singles/doubles sub-events.",
        "sql_mysql": """SELECT parent.competition_id AS parent_competition, child.competition_name AS sub_competition 
FROM competitions child
LEFT JOIN competitions parent ON child.parent_id = parent.competition_id
WHERE child.parent_id IS NOT NULL;""",
        "sql_sqlite": """SELECT parent.competition_id AS parent_competition, child.competition_name AS sub_competition 
FROM competitions child
LEFT JOIN competitions parent ON child.parent_id = parent.competition_id
WHERE child.parent_id IS NOT NULL;""",
        "chart_type": "table"
    },
    {
        "id": 6,
        "category": "Competitions & Categories",
        "title": "Analyze the distribution of competition types by category",
        "desc": "Cross-tabulation showing singles, doubles, and mixed event representation per category.",
        "sql_mysql": """SELECT cat.category_name, c.type, COUNT(c.competition_id) AS type_count 
FROM competitions c
JOIN categories cat ON c.category_id = cat.category_id
GROUP BY cat.category_name, c.type
ORDER BY cat.category_name, type_count DESC;""",
        "sql_sqlite": """SELECT cat.category_name, c.type, COUNT(c.competition_id) AS type_count 
FROM competitions c
JOIN categories cat ON c.category_id = cat.category_id
GROUP BY cat.category_name, c.type
ORDER BY cat.category_name, type_count DESC;""",
        "chart_type": "bar",
        "x": "category_name",
        "y": "type_count",
        "color": "type"
    },
    {
        "id": 7,
        "category": "Competitions & Categories",
        "title": "List all competitions with no parent (top-level competitions)",
        "desc": "Filters master standalone tournaments and parent circuits without parent dependencies.",
        "sql_mysql": """SELECT c.competition_id, c.competition_name, cat.category_name 
FROM competitions c
JOIN categories cat ON c.category_id = cat.category_id
WHERE c.parent_id IS NULL;""",
        "sql_sqlite": """SELECT c.competition_id, c.competition_name, cat.category_name 
FROM competitions c
JOIN categories cat ON c.category_id = cat.category_id
WHERE c.parent_id IS NULL;""",
        "chart_type": "table"
    },
    {
        "id": 8,
        "category": "Complexes & Venues",
        "title": "List all venues along with their associated complex name",
        "desc": "Resolves venue courts with their overarching sports complex facilities.",
        "sql_mysql": """SELECT v.venue_id, v.venue_name, c.complex_name
FROM Venues v
JOIN Complexes c ON v.complex_id = c.complex_id;""",
        "sql_sqlite": """SELECT v.venue_id, v.venue_name, c.complex_name
FROM Venues v
JOIN Complexes c ON v.complex_id = c.complex_id;""",
        "chart_type": "table"
    },
    {
        "id": 9,
        "category": "Complexes & Venues",
        "title": "Count the number of venues in each complex",
        "desc": "Quantifies court capacity per sports complex to identify major tournament hubs.",
        "sql_mysql": """SELECT c.complex_name, COUNT(v.venue_id) AS venue_count
FROM Complexes c
LEFT JOIN Venues v ON c.complex_id = v.complex_id
GROUP BY c.complex_name
ORDER BY venue_count DESC;""",
        "sql_sqlite": """SELECT c.complex_name, COUNT(v.venue_id) AS venue_count
FROM Complexes c
LEFT JOIN Venues v ON c.complex_id = v.complex_id
GROUP BY c.complex_name
ORDER BY venue_count DESC;""",
        "chart_type": "bar",
        "x": "complex_name",
        "y": "venue_count"
    },
    {
        "id": 10,
        "category": "Complexes & Venues",
        "title": "Get details of venues in a specific country (e.g., Chile)",
        "desc": "Examines national venue infrastructure with cities and local timezones for Chile.",
        "sql_mysql": """SELECT venue_id, venue_name, city_name, country_name, timezone
FROM Venues
WHERE country_name = 'Chile';""",
        "sql_sqlite": """SELECT venue_id, venue_name, city_name, country_name, timezone
FROM Venues
WHERE country_name = 'Chile';""",
        "chart_type": "table"
    },
    {
        "id": 11,
        "category": "Complexes & Venues",
        "title": "Identify all venues and their timezones",
        "desc": "Assesses worldwide tournament scheduling timezones for broadcast planning.",
        "sql_mysql": """SELECT venue_id, venue_name, timezone
FROM Venues;""",
        "sql_sqlite": """SELECT venue_id, venue_name, timezone
FROM Venues;""",
        "chart_type": "table"
    },
    {
        "id": 12,
        "category": "Complexes & Venues",
        "title": "Find complexes that have more than one venue",
        "desc": "Filters multi-court tennis centers capable of hosting multi-match concurrent sessions.",
        "sql_mysql": """SELECT c.complex_name, COUNT(v.venue_id) AS venue_count
FROM Complexes c
JOIN Venues v ON c.complex_id = v.complex_id
GROUP BY c.complex_name
HAVING COUNT(v.venue_id) > 1
ORDER BY venue_count DESC;""",
        "sql_sqlite": """SELECT c.complex_name, COUNT(v.venue_id) AS venue_count
FROM Complexes c
JOIN Venues v ON c.complex_id = v.complex_id
GROUP BY c.complex_name
HAVING COUNT(v.venue_id) > 1
ORDER BY venue_count DESC;""",
        "chart_type": "bar",
        "x": "complex_name",
        "y": "venue_count"
    },
    {
        "id": 13,
        "category": "Complexes & Venues",
        "title": "List venues grouped by country",
        "desc": "Generates a comma-separated inventory of tennis courts grouped by host country.",
        "sql_mysql": """SELECT country_name, GROUP_CONCAT(venue_name SEPARATOR ', ') AS venues
FROM Venues
GROUP BY country_name;""",
        "sql_sqlite": """SELECT country_name, GROUP_CONCAT(venue_name, ', ') AS venues
FROM Venues
GROUP BY country_name;""",
        "chart_type": "table"
    },
    {
        "id": 14,
        "category": "Complexes & Venues",
        "title": "Find all venues for a specific complex (e.g., Nacional)",
        "desc": "Retrieves the court inventory for the renowned 'Nacional' tennis complex.",
        "sql_mysql": """SELECT v.venue_id, v.venue_name, c.complex_name
FROM Venues v
JOIN Complexes c ON v.complex_id = c.complex_id
WHERE c.complex_name = 'Nacional';""",
        "sql_sqlite": """SELECT v.venue_id, v.venue_name, c.complex_name
FROM Venues v
JOIN Complexes c ON v.complex_id = c.complex_id
WHERE c.complex_name = 'Nacional';""",
        "chart_type": "table"
    },
    {
        "id": 15,
        "category": "Competitors & Rankings",
        "title": "Get all competitors with their rank and points",
        "desc": "Combines player profile records with live official doubles rankings and ATP/WTA points.",
        "sql_mysql": """SELECT c.name AS competitor_name, c.country, cr.rank, cr.points
FROM Competitors c
JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id
ORDER BY cr.rank ASC;""",
        "sql_sqlite": """SELECT c.name AS competitor_name, c.country, cr.rank, cr.points
FROM Competitors c
JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id
ORDER BY cr.rank ASC;""",
        "chart_type": "table"
    },
    {
        "id": 16,
        "category": "Competitors & Rankings",
        "title": "Find competitors ranked in the top 5",
        "desc": "Highlights elite world top 5 doubles competitors and their respective point totals.",
        "sql_mysql": """SELECT c.name AS competitor_name, c.country, cr.rank, cr.points
FROM Competitors c
JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id
WHERE cr.rank <= 5
ORDER BY cr.rank ASC;""",
        "sql_sqlite": """SELECT c.name AS competitor_name, c.country, cr.rank, cr.points
FROM Competitors c
JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id
WHERE cr.rank <= 5
ORDER BY cr.rank ASC;""",
        "chart_type": "bar",
        "x": "competitor_name",
        "y": "points"
    },
    {
        "id": 17,
        "category": "Competitors & Rankings",
        "title": "List competitors with no rank movement (stable rank)",
        "desc": "Filters players whose ranking position held steady with 0 delta movement.",
        "sql_mysql": """SELECT c.name AS competitor_name, c.country, cr.rank, cr.points
FROM Competitors c
JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id
WHERE cr.movement = 0
ORDER BY cr.rank ASC;""",
        "sql_sqlite": """SELECT c.name AS competitor_name, c.country, cr.rank, cr.points
FROM Competitors c
JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id
WHERE cr.movement = 0
ORDER BY cr.rank ASC;""",
        "chart_type": "table"
    },
    {
        "id": 18,
        "category": "Competitors & Rankings",
        "title": "Get the total points of competitors from a specific country (e.g., Croatia)",
        "desc": "Calculates aggregate ranking power for top tennis powerhouses like Croatia.",
        "sql_mysql": """SELECT c.country, SUM(cr.points) AS total_points
FROM Competitors c
JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id
WHERE c.country = 'Croatia'
GROUP BY c.country;""",
        "sql_sqlite": """SELECT c.country, SUM(cr.points) AS total_points
FROM Competitors c
JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id
WHERE c.country = 'Croatia'
GROUP BY c.country;""",
        "chart_type": "metric"
    },
    {
        "id": 19,
        "category": "Competitors & Rankings",
        "title": "Count the number of competitors per country",
        "desc": "Measures international tennis talent density by counting ranked players per nation.",
        "sql_mysql": """SELECT c.country, COUNT(c.competitor_id) AS competitor_count
FROM Competitors c
GROUP BY c.country
ORDER BY competitor_count DESC;""",
        "sql_sqlite": """SELECT c.country, COUNT(c.competitor_id) AS competitor_count
FROM Competitors c
GROUP BY c.country
ORDER BY competitor_count DESC;""",
        "chart_type": "bar",
        "x": "country",
        "y": "competitor_count"
    },
    {
        "id": 20,
        "category": "Competitors & Rankings",
        "title": "Find competitors with the highest points in the current week",
        "desc": "Discovers the reigning World #1 points leader using subquery MAX(points).",
        "sql_mysql": """SELECT c.name AS competitor_name, c.country, cr.rank, cr.points
FROM Competitors c
JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id
WHERE cr.points = (
    SELECT MAX(points)
    FROM Competitor_Rankings
);""",
        "sql_sqlite": """SELECT c.name AS competitor_name, c.country, cr.rank, cr.points
FROM Competitors c
JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id
WHERE cr.points = (
    SELECT MAX(points)
    FROM Competitor_Rankings
);""",
        "chart_type": "table"
    }
]

def check_mysql_connection():
    try:
        conn = pymysql.connect(
            host=MYSQL_CONFIG["host"],
            user=MYSQL_CONFIG["user"],
            password=MYSQL_CONFIG["password"],
            database=MYSQL_CONFIG["database"],
            port=MYSQL_CONFIG["port"],
            connect_timeout=1
        )
        conn.close()
        return True, "Connected to MySQL (tennis_analytics)"
    except Exception as e:
        return False, str(e)

def check_sqlite_connection():
    if os.path.exists(SQLITE_PATH):
        try:
            conn = sqlite3.connect(SQLITE_PATH)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r[0] for r in cur.fetchall()]
            conn.close()
            return True, f"Connected to SQLite ({len(tables)} tables)"
        except Exception as e:
            return False, str(e)
    return False, "SQLite DB file not found"

def get_connection(db_engine="mysql"):
    if db_engine == "mysql":
        return pymysql.connect(
            host=MYSQL_CONFIG["host"],
            user=MYSQL_CONFIG["user"],
            password=MYSQL_CONFIG["password"],
            database=MYSQL_CONFIG["database"],
            port=MYSQL_CONFIG["port"]
        )
    else:
        return sqlite3.connect(SQLITE_PATH)

def run_query(query_sql, db_engine="mysql"):
    start = time.perf_counter()
    conn = get_connection(db_engine)
    try:
        df = pd.read_sql_query(query_sql, conn)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return df, elapsed_ms, None
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return None, elapsed_ms, str(e)
    finally:
        conn.close()

def get_table_counts(db_engine="mysql"):
    tables = ['categories', 'competitions', 'Complexes', 'Venues', 'Competitors', 'Competitor_Rankings']
    counts = {}
    conn = get_connection(db_engine)
    cur = conn.cursor()
    for t in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM `{t}`" if db_engine == 'mysql' else f"SELECT COUNT(*) FROM {t}")
            row = cur.fetchone()
            counts[t] = row[0] if row else 0
        except Exception:
            counts[t] = 0
    conn.close()
    return counts
