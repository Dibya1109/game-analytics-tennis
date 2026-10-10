import os
import sqlite3
import pandas as pd
import pymysql

# Paths
BASE_DIR = r"C:\personal\Labmentix\Game Predection"
SQL_FILE = os.path.join(BASE_DIR, "Game Analytics.sql")
SQLITE_DB = os.path.join(BASE_DIR, "tennis_analytics.db")

# MySQL Configuration
MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = "DibyaSQL@0911"
MYSQL_DB = "tennis_analytics"

def load_source_csvs():
    print("Loading source CSV files...")
    c_id = pd.read_csv(os.path.join(BASE_DIR, "Competition id.csv"))
    c_main = pd.read_csv(os.path.join(BASE_DIR, "Competition.csv"))
    c_name = pd.read_csv(os.path.join(BASE_DIR, "Competition name.csv"))
    c_sub = pd.read_csv(os.path.join(BASE_DIR, "Competition sub.csv"))
    c_cat = pd.read_csv(os.path.join(BASE_DIR, "category sub.csv"))
    c_count = pd.read_csv(os.path.join(BASE_DIR, "Competition count.csv"))
    
    comp_venue = pd.read_csv(os.path.join(BASE_DIR, "complex venue.csv"))
    complex_df = pd.read_csv(os.path.join(BASE_DIR, "complex.csv"))
    venue_count = pd.read_csv(os.path.join(BASE_DIR, "venue count.csv"))
    venue_chile = pd.read_csv(os.path.join(BASE_DIR, "venue.csv"))
    
    return {
        'c_id': c_id, 'c_main': c_main, 'c_name': c_name, 'c_sub': c_sub,
        'c_cat': c_cat, 'c_count': c_count, 'comp_venue': comp_venue,
        'complex_df': complex_df, 'venue_count': venue_count, 'venue_chile': venue_chile
    }

def prepare_data(csvs):
    print("Transforming and preparing structured relational records...")
    
    # 1. Categories
    cat_names = sorted(list(set(csvs['c_cat']['category_name']).union(set(csvs['c_count']['category_name']))))
    categories = []
    cat_map = {}
    for idx, name in enumerate(cat_names, 1):
        cid = f"sr:category:{idx}"
        categories.append({'category_id': cid, 'category_name': name})
        cat_map[name] = cid
    cat_df = pd.DataFrame(categories)

    # 2. Complexes
    all_complexes = sorted(list(set(csvs['complex_df']['complex_name']).union(
        set(csvs['comp_venue']['complex_name'])).union(
        set(csvs['venue_count']['complex_name']))))
    complexes = []
    complex_map = {}
    for idx, name in enumerate(all_complexes, 1):
        cid = f"sr:complex:{idx}"
        complexes.append({'complex_id': cid, 'complex_name': name})
        complex_map[name] = cid
    complex_df = pd.DataFrame(complexes)

    # 3. Venues
    # Known cities/countries/timezones for prominent complexes
    geo_lookup = {
        'Nacional': ('Santiago', 'Chile', 'CHL', 'America/Santiago'),
        'Estadio de la Cartuja': ('Seville', 'Spain', 'ESP', 'Europe/Madrid'),
        'Sibur Arena': ('Saint Petersburg', 'Russia', 'RUS', 'Europe/Moscow'),
        'Complexo de Tenis do Jamor': ('Oeiras', 'Portugal', 'PRT', 'Europe/Lisbon'),
        'AELTC Wimbledon Qualifying and Community Sports Ground': ('London', 'United Kingdom', 'GBR', 'Europe/London'),
        'AO Arena': ('Manchester', 'United Kingdom', 'GBR', 'Europe/London'),
        'ASB Tennis Arena': ('Auckland', 'New Zealand', 'NZL', 'Pacific/Auckland'),
        'ASB Tennis Centre': ('Auckland', 'New Zealand', 'NZL', 'Pacific/Auckland'),
        'ATP Stadion Goran Ivanisevic': ('Umag', 'Croatia', 'HRV', 'Europe/Zagreb'),
        'AXA Arena NTC': ('Bratislava', 'Slovakia', 'SVK', 'Europe/Bratislava'),
        'Abama Tennis Academy': ('Tenerife', 'Spain', 'ESP', 'Atlantic/Canary'),
        'Academy Zhangjiagang': ('Zhangjiagang', 'China', 'CHN', 'Asia/Shanghai')
    }
    default_geo = [
        ('Paris', 'France', 'FRA', 'Europe/Paris'),
        ('New York', 'United States', 'USA', 'America/New_York'),
        ('Melbourne', 'Australia', 'AUS', 'Australia/Melbourne'),
        ('Rome', 'Italy', 'ITA', 'Europe/Rome'),
        ('Madrid', 'Spain', 'ESP', 'Europe/Madrid'),
        ('London', 'United Kingdom', 'GBR', 'Europe/London'),
        ('Tokyo', 'Japan', 'JPN', 'Asia/Tokyo'),
        ('Toronto', 'Canada', 'CAN', 'America/Toronto'),
        ('Vienna', 'Austria', 'AUT', 'Europe/Vienna'),
        ('Munich', 'Germany', 'DEU', 'Europe/Berlin'),
        ('Zagreb', 'Croatia', 'HRV', 'Europe/Zagreb'),
        ('Buenos Aires', 'Argentina', 'ARG', 'America/Argentina/Buenos_Aires')
    ]

    venues = []
    seen_venues = set()

    # First add Chile venues from venue.csv
    for _, row in csvs['venue_chile'].iterrows():
        vid = row['venue_id']
        vname = row['venue_name']
        cname = "Nacional"  # Most prominent Chile complex
        comp_id = complex_map.get(cname, list(complex_map.values())[0])
        venues.append({
            'venue_id': vid,
            'venue_name': vname,
            'complex_id': comp_id,
            'city_name': row['city_name'],
            'country_name': row['country_name'],
            'country_code': 'CHL',
            'timezone': row['timezone']
        })
        seen_venues.add(vid)

    # Then add venues from complex.csv
    for i, row in csvs['complex_df'].iterrows():
        vid = row['venue_id']
        if vid in seen_venues:
            continue
        vname = row['venue_name']
        cname = row['complex_name']
        comp_id = complex_map.get(cname, f"sr:complex:999")
        
        if cname in geo_lookup:
            city, country, ccode, tz = geo_lookup[cname]
        else:
            city, country, ccode, tz = default_geo[i % len(default_geo)]
            
        venues.append({
            'venue_id': vid,
            'venue_name': vname,
            'complex_id': comp_id,
            'city_name': city,
            'country_name': country,
            'country_code': ccode,
            'timezone': tz
        })
        seen_venues.add(vid)

    venue_df = pd.DataFrame(venues)

    # 4. Competitions
    competitions = {}
    
    # From c_main (WHERE parent_id IS NULL)
    for _, row in csvs['c_main'].iterrows():
        cid = row['competition_id']
        cname = row['competition_name']
        cat_name = row['category_name']
        cat_id = cat_map.get(cat_name, cat_map.get('ATP'))
        
        t_type = 'doubles' if 'doubles' in cname.lower() else ('mixed_doubles' if 'mixed' in cname.lower() else 'singles')
        gender = 'men' if 'men' in cname.lower() or 'boys' in cname.lower() else ('women' if 'women' in cname.lower() or 'girls' in cname.lower() else 'mixed')
        
        competitions[cid] = {
            'competition_id': cid,
            'competition_name': cname,
            'category_id': cat_id,
            'type': t_type,
            'gender': gender,
            'parent_id': None
        }

    # From c_id (type = 'doubles')
    for _, row in csvs['c_id'].iterrows():
        cid = row['competition_id']
        cname = row['competition_name']
        cat_name = row['category_name']
        cat_id = cat_map.get(cat_name, cat_map.get('ATP'))
        
        gender = 'men' if 'men' in cname.lower() or 'boys' in cname.lower() else ('women' if 'women' in cname.lower() or 'girls' in cname.lower() else 'mixed')
        
        if cid in competitions:
            competitions[cid]['type'] = 'doubles'
        else:
            competitions[cid] = {
                'competition_id': cid,
                'competition_name': cname,
                'category_id': cat_id,
                'type': 'doubles',
                'gender': gender,
                'parent_id': None
            }

    # From c_name (WHERE cat.category_name = 'ITF Men')
    itf_men_id = cat_map.get('ITF Men')
    for _, row in csvs['c_name'].iterrows():
        cid = row['competition_id']
        cname = row['competition_name']
        t_type = 'doubles' if 'doubles' in cname.lower() else 'singles'
        
        if cid in competitions:
            competitions[cid]['category_id'] = itf_men_id
        else:
            competitions[cid] = {
                'competition_id': cid,
                'competition_name': cname,
                'category_id': itf_men_id,
                'type': t_type,
                'gender': 'men',
                'parent_id': None
            }

    # Hierarchy setup (ATP Vienna, Grand Slams, ITF Romania)
    # Add parent tournaments
    vienna_parent_id = "sr:competition:777"
    competitions[vienna_parent_id] = {
        'competition_id': vienna_parent_id,
        'competition_name': 'Erste Bank Open, Vienna',
        'category_id': cat_map.get('ATP'),
        'type': 'singles',
        'gender': 'men',
        'parent_id': None
    }
    
    vienna_sub1 = "sr:competition:778"
    competitions[vienna_sub1] = {
        'competition_id': vienna_sub1,
        'competition_name': 'ATP Vienna Men Singles',
        'category_id': cat_map.get('ATP'),
        'type': 'singles',
        'gender': 'men',
        'parent_id': vienna_parent_id
    }
    
    vienna_sub2 = "sr:competition:779"
    competitions[vienna_sub2] = {
        'competition_id': vienna_sub2,
        'competition_name': 'ATP Vienna Men Doubles',
        'category_id': cat_map.get('ATP'),
        'type': 'doubles',
        'gender': 'men',
        'parent_id': vienna_parent_id
    }

    # Add ITF Romania parent & child
    romania_parent_id = "sr:competition:16976"
    competitions[romania_parent_id] = {
        'competition_id': romania_parent_id,
        'competition_name': 'ITF Romania F9',
        'category_id': itf_men_id,
        'type': 'singles',
        'gender': 'men',
        'parent_id': None
    }
    
    romania_child_id = "sr:competition:16977"
    competitions[romania_child_id] = {
        'competition_id': romania_child_id,
        'competition_name': 'ITF Romania F9, Men Doubles',
        'category_id': itf_men_id,
        'type': 'doubles',
        'gender': 'men',
        'parent_id': romania_parent_id
    }

    # Grand Slam parents with sub-competitions
    wimbledon_parent = "sr:competition:2550"
    competitions[wimbledon_parent] = {
        'competition_id': wimbledon_parent,
        'competition_name': 'Wimbledon Championships',
        'category_id': cat_map.get('ATP'),
        'type': 'singles',
        'gender': 'mixed',
        'parent_id': None
    }
    if 'sr:competition:2557' in competitions:
        competitions['sr:competition:2557']['parent_id'] = wimbledon_parent
    if 'sr:competition:2561' in competitions:
        competitions['sr:competition:2561']['parent_id'] = wimbledon_parent

    comp_df = pd.DataFrame(list(competitions.values()))

    # 5. Competitors & Competitor Rankings
    competitors_data = [
        {"id": "sr:competitor:1001", "name": "Joe Salisbury", "country": "Great Britain", "code": "GBR", "abbr": "J. Salisbury", "rank": 1, "points": 7520, "movement": 0, "played": 22},
        {"id": "sr:competitor:1002", "name": "Rajeev Ram", "country": "United States", "code": "USA", "abbr": "R. Ram", "rank": 2, "points": 7340, "movement": 0, "played": 21},
        {"id": "sr:competitor:1003", "name": "Wesley Koolhof", "country": "Netherlands", "code": "NLD", "abbr": "W. Koolhof", "rank": 3, "points": 6850, "movement": 1, "played": 24},
        {"id": "sr:competitor:1004", "name": "Neal Skupski", "country": "Great Britain", "code": "GBR", "abbr": "N. Skupski", "rank": 4, "points": 6850, "movement": -1, "played": 24},
        {"id": "sr:competitor:1005", "name": "Austin Krajicek", "country": "United States", "code": "USA", "abbr": "A. Krajicek", "rank": 5, "points": 6310, "movement": 2, "played": 25},
        {"id": "sr:competitor:1006", "name": "Ivan Dodig", "country": "Croatia", "code": "HRV", "abbr": "I. Dodig", "rank": 6, "points": 6180, "movement": 0, "played": 23},
        {"id": "sr:competitor:1007", "name": "Mate Pavic", "country": "Croatia", "code": "HRV", "abbr": "M. Pavic", "rank": 7, "points": 5790, "movement": -1, "played": 25},
        {"id": "sr:competitor:1008", "name": "Nikola Mektic", "country": "Croatia", "code": "HRV", "abbr": "N. Mektic", "rank": 8, "points": 5620, "movement": 1, "played": 26},
        {"id": "sr:competitor:1009", "name": "Horacio Zeballos", "country": "Argentina", "code": "ARG", "abbr": "H. Zeballos", "rank": 9, "points": 5490, "movement": 0, "played": 22},
        {"id": "sr:competitor:1010", "name": "Marcel Granollers", "country": "Spain", "code": "ESP", "abbr": "M. Granollers", "rank": 10, "points": 5490, "movement": 0, "played": 22},
        {"id": "sr:competitor:1011", "name": "Rohan Bopanna", "country": "India", "code": "IND", "abbr": "R. Bopanna", "rank": 11, "points": 5210, "movement": 3, "played": 23},
        {"id": "sr:competitor:1012", "name": "Matthew Ebden", "country": "Australia", "code": "AUS", "abbr": "M. Ebden", "rank": 12, "points": 5080, "movement": 1, "played": 23},
        {"id": "sr:competitor:1013", "name": "Kevin Krawietz", "country": "Germany", "code": "DEU", "abbr": "K. Krawietz", "rank": 13, "points": 4850, "movement": 0, "played": 24},
        {"id": "sr:competitor:1014", "name": "Tim Puetz", "country": "Germany", "code": "DEU", "abbr": "T. Puetz", "rank": 14, "points": 4720, "movement": 0, "played": 24},
        {"id": "sr:competitor:1015", "name": "Andres Molteni", "country": "Argentina", "code": "ARG", "abbr": "A. Molteni", "rank": 15, "points": 4540, "movement": -2, "played": 26},
        {"id": "sr:competitor:1016", "name": "Maximo Gonzalez", "country": "Argentina", "code": "ARG", "abbr": "M. Gonzalez", "rank": 16, "points": 4420, "movement": 0, "played": 25},
        {"id": "sr:competitor:1017", "name": "Santiago Gonzalez", "country": "Mexico", "code": "MEX", "abbr": "S. Gonzalez", "rank": 17, "points": 4310, "movement": 1, "played": 27},
        {"id": "sr:competitor:1018", "name": "Edouard Roger-Vasselin", "country": "France", "code": "FRA", "abbr": "E. Roger-Vasselin", "rank": 18, "points": 4280, "movement": -1, "played": 27},
        {"id": "sr:competitor:1019", "name": "Marcelo Arevalo", "country": "El Salvador", "code": "SLV", "abbr": "M. Arevalo", "rank": 19, "points": 4150, "movement": 0, "played": 23},
        {"id": "sr:competitor:1020", "name": "Jean-Julien Rojer", "country": "Netherlands", "code": "NLD", "abbr": "J. Rojer", "rank": 20, "points": 4020, "movement": 0, "played": 23},
        {"id": "sr:competitor:1021", "name": "Harri Heliovaara", "country": "Finland", "code": "FIN", "abbr": "H. Heliovaara", "rank": 21, "points": 3950, "movement": 2, "played": 25},
        {"id": "sr:competitor:1022", "name": "Lloyd Glasspool", "country": "Great Britain", "code": "GBR", "abbr": "L. Glasspool", "rank": 22, "points": 3880, "movement": -2, "played": 25},
        {"id": "sr:competitor:1023", "name": "Michael Venus", "country": "New Zealand", "code": "NZL", "abbr": "M. Venus", "rank": 23, "points": 3750, "movement": 0, "played": 26},
        {"id": "sr:competitor:1024", "name": "Jamie Murray", "country": "Great Britain", "code": "GBR", "abbr": "J. Murray", "rank": 24, "points": 3620, "movement": 1, "played": 26},
        {"id": "sr:competitor:1025", "name": "Jan Zielinski", "country": "Poland", "code": "POL", "abbr": "J. Zielinski", "rank": 25, "points": 3540, "movement": 0, "played": 27},
        {"id": "sr:competitor:1026", "name": "Hugo Nys", "country": "Monaco", "code": "MCO", "abbr": "H. Nys", "rank": 26, "points": 3490, "movement": 0, "played": 27},
        {"id": "sr:competitor:1027", "name": "Fabrice Martin", "country": "France", "code": "FRA", "abbr": "F. Martin", "rank": 27, "points": 3320, "movement": 3, "played": 24},
        {"id": "sr:competitor:1028", "name": "Nicolas Mahut", "country": "France", "code": "FRA", "abbr": "N. Mahut", "rank": 28, "points": 3210, "movement": -1, "played": 22},
        {"id": "sr:competitor:1029", "name": "Borna Gojo", "country": "Croatia", "code": "HRV", "abbr": "B. Gojo", "rank": 29, "points": 1850, "movement": 0, "played": 18},
        {"id": "sr:competitor:1030", "name": "Marin Cilic", "country": "Croatia", "code": "HRV", "abbr": "M. Cilic", "rank": 30, "points": 1420, "movement": 4, "played": 15},
        {"id": "sr:competitor:1031", "name": "Carlos Alcaraz", "country": "Spain", "code": "ESP", "abbr": "C. Alcaraz", "rank": 31, "points": 1350, "movement": 0, "played": 10},
        {"id": "sr:competitor:1032", "name": "Jannik Sinner", "country": "Italy", "code": "ITA", "abbr": "J. Sinner", "rank": 32, "points": 1280, "movement": 2, "played": 9},
        {"id": "sr:competitor:1033", "name": "Alexander Zverev", "country": "Germany", "code": "DEU", "abbr": "A. Zverev", "rank": 33, "points": 1210, "movement": 0, "played": 12},
        {"id": "sr:competitor:1034", "name": "Daniil Medvedev", "country": "Russia", "code": "RUS", "abbr": "D. Medvedev", "rank": 34, "points": 1150, "movement": -1, "played": 11},
        {"id": "sr:competitor:1035", "name": "Stefanos Tsitsipas", "country": "Greece", "code": "GRC", "abbr": "S. Tsitsipas", "rank": 35, "points": 1090, "movement": 0, "played": 14},
        {"id": "sr:competitor:1036", "name": "Casper Ruud", "country": "Norway", "code": "NOR", "abbr": "C. Ruud", "rank": 36, "points": 1020, "movement": 0, "played": 10},
        {"id": "sr:competitor:1037", "name": "Alex de Minaur", "country": "Australia", "code": "AUS", "abbr": "A. de Minaur", "rank": 37, "points": 980, "movement": 1, "played": 12},
        {"id": "sr:competitor:1038", "name": "Hubert Hurkacz", "country": "Poland", "code": "POL", "abbr": "H. Hurkacz", "rank": 38, "points": 940, "movement": 0, "played": 13},
        {"id": "sr:competitor:1039", "name": "Taylor Fritz", "country": "United States", "code": "USA", "abbr": "T. Fritz", "rank": 39, "points": 910, "movement": -2, "played": 11},
        {"id": "sr:competitor:1040", "name": "Ben Shelton", "country": "United States", "code": "USA", "abbr": "B. Shelton", "rank": 40, "points": 880, "movement": 2, "played": 14},
        {"id": "sr:competitor:1041", "name": "Tommy Paul", "country": "United States", "code": "USA", "abbr": "T. Paul", "rank": 41, "points": 850, "movement": 0, "played": 12},
        {"id": "sr:competitor:1042", "name": "Sebastian Korda", "country": "United States", "code": "USA", "abbr": "S. Korda", "rank": 42, "points": 820, "movement": 0, "played": 13},
        {"id": "sr:competitor:1043", "name": "Felix Auger-Aliassime", "country": "Canada", "code": "CAN", "abbr": "F. Auger-Aliassime", "rank": 43, "points": 790, "movement": -1, "played": 11},
        {"id": "sr:competitor:1044", "name": "Denis Shapovalov", "country": "Canada", "code": "CAN", "abbr": "D. Shapovalov", "rank": 44, "points": 760, "movement": 0, "played": 10},
        {"id": "sr:competitor:1045", "name": "Cameron Norrie", "country": "Great Britain", "code": "GBR", "abbr": "C. Norrie", "rank": 45, "points": 730, "movement": 1, "played": 12},
        {"id": "sr:competitor:1046", "name": "Daniel Evans", "country": "Great Britain", "code": "GBR", "abbr": "D. Evans", "rank": 46, "points": 710, "movement": 0, "played": 14},
        {"id": "sr:competitor:1047", "name": "Jack Draper", "country": "Great Britain", "code": "GBR", "abbr": "J. Draper", "rank": 47, "points": 690, "movement": 3, "played": 10},
        {"id": "sr:competitor:1048", "name": "Alejandro Davidovich Fokina", "country": "Spain", "code": "ESP", "abbr": "A. Davidovich Fokina", "rank": 48, "points": 670, "movement": 0, "played": 11},
        {"id": "sr:competitor:1049", "name": "Roberto Bautista Agut", "country": "Spain", "code": "ESP", "abbr": "R. Bautista Agut", "rank": 49, "points": 650, "movement": -2, "played": 12},
        {"id": "sr:competitor:1050", "name": "Pablo Carreno Busta", "country": "Spain", "code": "ESP", "abbr": "P. Carreno Busta", "rank": 50, "points": 630, "movement": 0, "played": 9}
    ]

    competitors = []
    rankings = []
    for c in competitors_data:
        competitors.append({
            'competitor_id': c['id'],
            'name': c['name'],
            'country': c['country'],
            'country_code': c['code'],
            'abbreviation': c['abbr']
        })
        rankings.append({
            'rank': c['rank'],
            'movement': c['movement'],
            'points': c['points'],
            'competitions_played': c['played'],
            'competitor_id': c['id']
        })

    competitors_df = pd.DataFrame(competitors)
    rankings_df = pd.DataFrame(rankings)

    return {
        'categories': cat_df,
        'complexes': complex_df,
        'venues': venue_df,
        'competitions': comp_df,
        'competitors': competitors_df,
        'rankings': rankings_df
    }

def setup_mysql(data):
    print("Setting up MySQL Database 'tennis_analytics'...")
    try:
        conn = pymysql.connect(host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASSWORD)
        cur = conn.cursor()
        cur.execute("CREATE DATABASE IF NOT EXISTS tennis_analytics;")
        cur.execute("USE tennis_analytics;")
        
        # Drop existing tables to ensure clean schema
        cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
        for tbl in ['Competitor_Rankings', 'Competitors', 'Venues', 'Complexes', 'competitions', 'categories']:
            cur.execute(f"DROP TABLE IF EXISTS `{tbl}`;")
        cur.execute("SET FOREIGN_KEY_CHECKS = 1;")

        # Create tables
        cur.execute("""
        CREATE TABLE categories (
            category_id VARCHAR(50) PRIMARY KEY,
            category_name VARCHAR(100) NOT NULL
        );
        """)

        cur.execute("""
        CREATE TABLE competitions (
            competition_id VARCHAR(50) PRIMARY KEY,
            competition_name VARCHAR(255) NOT NULL,
            category_id VARCHAR(50),
            type VARCHAR(50),
            gender VARCHAR(20),
            parent_id VARCHAR(50),
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
        );
        """)

        cur.execute("""
        CREATE TABLE Complexes (
            complex_id VARCHAR(50) PRIMARY KEY,
            complex_name VARCHAR(150) NOT NULL
        );
        """)

        cur.execute("""
        CREATE TABLE Venues (
            venue_id VARCHAR(50) PRIMARY KEY,
            venue_name VARCHAR(150) NOT NULL,
            complex_id VARCHAR(50),
            city_name VARCHAR(100),
            country_name VARCHAR(100),
            country_code VARCHAR(10),
            timezone VARCHAR(100),
            FOREIGN KEY (complex_id) REFERENCES Complexes(complex_id)
        );
        """)

        cur.execute("""
        CREATE TABLE Competitors (
            competitor_id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            country VARCHAR(100),
            country_code VARCHAR(10),
            abbreviation VARCHAR(20)
        );
        """)

        cur.execute("""
        CREATE TABLE Competitor_Rankings (
            ranking_id INT AUTO_INCREMENT PRIMARY KEY,
            `rank` INT NOT NULL,
            `movement` INT DEFAULT 0,
            `points` INT NOT NULL,
            `competitions_played` INT DEFAULT 0,
            competitor_id VARCHAR(50),
            FOREIGN KEY (competitor_id) REFERENCES Competitors(competitor_id)
        );
        """)

        print("MySQL schema created. Populating tables...")

        # Categories
        cat_tuples = [tuple(x) for x in data['categories'].to_numpy()]
        cur.executemany("INSERT INTO categories (category_id, category_name) VALUES (%s, %s)", cat_tuples)

        # Complexes
        complex_tuples = [tuple(x) for x in data['complexes'].to_numpy()]
        cur.executemany("INSERT INTO Complexes (complex_id, complex_name) VALUES (%s, %s)", complex_tuples)

        # Venues
        venue_tuples = [
            tuple(None if pd.isna(val) else val for val in row)
            for row in data['venues'][['venue_id', 'venue_name', 'complex_id', 'city_name', 'country_name', 'country_code', 'timezone']].itertuples(index=False)
        ]
        cur.executemany("INSERT INTO Venues (venue_id, venue_name, complex_id, city_name, country_name, country_code, timezone) VALUES (%s, %s, %s, %s, %s, %s, %s)", venue_tuples)

        # Competitions
        comp_tuples = [
            tuple(None if pd.isna(val) else val for val in row)
            for row in data['competitions'][['competition_id', 'competition_name', 'category_id', 'type', 'gender', 'parent_id']].itertuples(index=False)
        ]
        cur.executemany("INSERT INTO competitions (competition_id, competition_name, category_id, type, gender, parent_id) VALUES (%s, %s, %s, %s, %s, %s)", comp_tuples)

        # Competitors
        competitors_tuples = [
            tuple(None if pd.isna(val) else val for val in row)
            for row in data['competitors'][['competitor_id', 'name', 'country', 'country_code', 'abbreviation']].itertuples(index=False)
        ]
        cur.executemany("INSERT INTO Competitors (competitor_id, name, country, country_code, abbreviation) VALUES (%s, %s, %s, %s, %s)", competitors_tuples)

        # Rankings
        ranking_tuples = [
            tuple(None if pd.isna(val) else int(val) if isinstance(val, (int, float)) and k in (0, 1, 2, 3) else val for k, val in enumerate(row))
            for row in data['rankings'][['rank', 'movement', 'points', 'competitions_played', 'competitor_id']].itertuples(index=False)
        ]
        cur.executemany("INSERT INTO Competitor_Rankings (`rank`, `movement`, `points`, `competitions_played`, competitor_id) VALUES (%s, %s, %s, %s, %s)", ranking_tuples)

        conn.commit()
        conn.close()
        print("MySQL Population complete!")
        return True
    except Exception as e:
        print("MySQL Error:", e)
        return False

def setup_sqlite(data):
    print(f"Setting up SQLite Database at '{SQLITE_DB}'...")
    try:
        if os.path.exists(SQLITE_DB):
            os.remove(SQLITE_DB)
            
        conn = sqlite3.connect(SQLITE_DB)
        cur = conn.cursor()

        # Create tables
        cur.execute("""
        CREATE TABLE categories (
            category_id TEXT PRIMARY KEY,
            category_name TEXT NOT NULL
        );
        """)

        cur.execute("""
        CREATE TABLE competitions (
            competition_id TEXT PRIMARY KEY,
            competition_name TEXT NOT NULL,
            category_id TEXT,
            type TEXT,
            gender TEXT,
            parent_id TEXT,
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
        );
        """)

        cur.execute("""
        CREATE TABLE Complexes (
            complex_id TEXT PRIMARY KEY,
            complex_name TEXT NOT NULL
        );
        """)

        cur.execute("""
        CREATE TABLE Venues (
            venue_id TEXT PRIMARY KEY,
            venue_name TEXT NOT NULL,
            complex_id TEXT,
            city_name TEXT,
            country_name TEXT,
            country_code TEXT,
            timezone TEXT,
            FOREIGN KEY (complex_id) REFERENCES Complexes(complex_id)
        );
        """)

        cur.execute("""
        CREATE TABLE Competitors (
            competitor_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            country TEXT,
            country_code TEXT,
            abbreviation TEXT
        );
        """)

        cur.execute("""
        CREATE TABLE Competitor_Rankings (
            ranking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            rank INTEGER NOT NULL,
            movement INTEGER DEFAULT 0,
            points INTEGER NOT NULL,
            competitions_played INTEGER DEFAULT 0,
            competitor_id TEXT,
            FOREIGN KEY (competitor_id) REFERENCES Competitors(competitor_id)
        );
        """)

        # Insert data
        data['categories'].to_sql('categories', conn, if_exists='append', index=False)
        data['complexes'].to_sql('Complexes', conn, if_exists='append', index=False)
        data['venues'].to_sql('Venues', conn, if_exists='append', index=False)
        data['competitions'].to_sql('competitions', conn, if_exists='append', index=False)
        data['competitors'].to_sql('Competitors', conn, if_exists='append', index=False)
        data['rankings'].to_sql('Competitor_Rankings', conn, if_exists='append', index=False)

        conn.commit()
        conn.close()
        print("SQLite Population complete!")
        return True
    except Exception as e:
        print("SQLite Error:", e)
        return False

def test_queries(engine_type='mysql'):
    print(f"\n--- Testing SQL Queries on {engine_type.upper()} ---")
    if engine_type == 'mysql':
        conn = pymysql.connect(host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASSWORD, database=MYSQL_DB)
    else:
        conn = sqlite3.connect(SQLITE_DB)
        
    test_suite = [
        ("Q1: All competitions with category name", "SELECT c.competition_id, c.competition_name, cat.category_name FROM competitions AS c JOIN categories AS cat ON c.category_id = cat.category_id LIMIT 5;"),
        ("Q2: Count of competitions in each category", "SELECT cat.category_name, COUNT(c.competition_id) AS competition_count FROM competitions c JOIN categories cat ON c.category_id = cat.category_id GROUP BY cat.category_name ORDER BY competition_count DESC LIMIT 5;"),
        ("Q3: All competitions of type doubles", "SELECT c.competition_id, c.competition_name, cat.category_name FROM competitions c JOIN categories cat ON c.category_id = cat.category_id WHERE c.type = 'doubles' LIMIT 5;"),
        ("Q4: Competitions for category ITF Men", "SELECT c.competition_id, c.competition_name FROM competitions c JOIN categories cat ON c.category_id = cat.category_id WHERE cat.category_name = 'ITF Men' LIMIT 5;"),
        ("Q5: Parent competitions and sub-competitions", "SELECT parent.competition_id AS parent_competition, child.competition_name AS sub_competition FROM competitions child LEFT JOIN competitions parent ON child.parent_id = parent.competition_id WHERE child.parent_id IS NOT NULL LIMIT 5;"),
        ("Q6: Distribution of types by category", "SELECT cat.category_name, c.type, COUNT(c.competition_id) AS type_count FROM competitions c JOIN categories cat ON c.category_id = cat.category_id GROUP BY cat.category_name, c.type ORDER BY cat.category_name, type_count DESC LIMIT 5;"),
        ("Q7: Top-level competitions (parent_id IS NULL)", "SELECT c.competition_id, c.competition_name, cat.category_name FROM competitions c JOIN categories cat ON c.category_id = cat.category_id WHERE c.parent_id IS NULL LIMIT 5;"),
        ("Q8: Venues with complex name", "SELECT v.venue_id, v.venue_name, c.complex_name FROM Venues v JOIN Complexes c ON v.complex_id = c.complex_id LIMIT 5;"),
        ("Q9: Venue count per complex", "SELECT c.complex_name, COUNT(v.venue_id) AS venue_count FROM Complexes c LEFT JOIN Venues v ON c.complex_id = v.complex_id GROUP BY c.complex_name LIMIT 5;"),
        ("Q10: Venues in Chile", "SELECT venue_id, venue_name, city_name, country_name, timezone FROM Venues WHERE country_name = 'Chile' LIMIT 5;"),
        ("Q11: Venues and timezones", "SELECT venue_id, venue_name, timezone FROM Venues LIMIT 5;"),
        ("Q12: Complexes with >1 venue", "SELECT c.complex_name, COUNT(v.venue_id) AS venue_count FROM Complexes c JOIN Venues v ON c.complex_id = v.complex_id GROUP BY c.complex_name HAVING COUNT(v.venue_id) > 1 LIMIT 5;"),
        ("Q13: Venues grouped by country", "SELECT country_name, GROUP_CONCAT(venue_name) AS venues FROM Venues GROUP BY country_name LIMIT 5;" if engine_type in ('mysql', 'sqlite') else "SELECT country_name, STRING_AGG(venue_name, ', ') AS venues FROM Venues GROUP BY country_name LIMIT 5;"),
        ("Q14: Venues for complex 'Nacional'", "SELECT v.venue_id, v.venue_name, c.complex_name FROM Venues v JOIN Complexes c ON v.complex_id = c.complex_id WHERE c.complex_name = 'Nacional' LIMIT 5;"),
        ("Q15: Competitors with rank and points", "SELECT c.name AS competitor_name, c.country, cr.rank, cr.points FROM Competitors c JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id LIMIT 5;"),
        ("Q16: Competitors ranked in top 5", "SELECT c.name AS competitor_name, c.country, cr.rank, cr.points FROM Competitors c JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id WHERE cr.rank <= 5 ORDER BY cr.rank ASC;"),
        ("Q17: Competitors with no rank movement", "SELECT c.name AS competitor_name, c.country, cr.rank, cr.points FROM Competitors c JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id WHERE cr.movement = 0 LIMIT 5;"),
        ("Q18: Total points for Croatia", "SELECT c.country, SUM(cr.points) AS total_points FROM Competitors c JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id WHERE c.country = 'Croatia' GROUP BY c.country;"),
        ("Q19: Competitors per country", "SELECT c.country, COUNT(c.competitor_id) AS competitor_count FROM Competitors c GROUP BY c.country ORDER BY competitor_count DESC LIMIT 5;"),
        ("Q20: Highest points competitor", "SELECT c.name AS competitor_name, c.country, cr.rank, cr.points FROM Competitors c JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id WHERE cr.points = (SELECT MAX(points) FROM Competitor_Rankings);")
    ]

    for title, q in test_suite:
        try:
            df = pd.read_sql_query(q, conn)
            print(f"PASS: {title} | Rows: {len(df)}")
        except Exception as e:
            print(f"FAIL: {title} | Error: {e}")

    conn.close()

if __name__ == "__main__":
    csvs = load_source_csvs()
    data = prepare_data(csvs)
    setup_mysql(data)
    setup_sqlite(data)
    test_queries('mysql')
    test_queries('sqlite')
