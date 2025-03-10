import numpy as np
import pandas as pd
import pybaseball as pyb
import re
import streamlit as st

st.set_page_config(page_title="CBL 2025 Draft", layout="wide", initial_sidebar_state="auto", menu_items=None)

@st.cache_data(ttl=1800)
def get_map():
    url = "https://docs.google.com/spreadsheets/d/1JgczhD5VDQ1EiXqVG-blttZcVwbZd5_Ne_mefUGwJnk/pubhtml?gid=0&single=true"
    tables = pd.read_html(url, header=1)

    # The function returns a list of DataFrames, so you need to select the appropriate one
    id_map = tables[0]  # assuming the first table is the one you need

    id_map = id_map.dropna(how='all')  # Drops rows that are entirely NaN (blank row)
    id_map.reset_index(drop=True, inplace=True)
    id_map = id_map.drop(id_map.columns[0], axis=1)
    id_map['IDFANGRAPHS'] = pd.to_numeric(id_map['IDFANGRAPHS'], errors='coerce', downcast='integer')

    return id_map

@st.cache_data(ttl=1800)
def get_batters(map):
    cbl_batters = pd.read_csv('batters_sup.csv')
    batting_stats = pyb.batting_stats(2024, qual=0)

    pre_batters = pd.merge(cbl_batters, batting_stats, left_on='FanGraph ID', right_on='IDfg', how='inner')

    pre_batters['is_carded'] = np.where(pre_batters['CBL5Percent'].astype(str) == 'NC', False, True)

    pre_batters = pd.merge(pre_batters, map[['IDFANGRAPHS', 'BATS', 'MLBNAME', 'MLBID']], 
                       left_on='FanGraph ID', right_on='IDFANGRAPHS', 
                       how='left')

    pre_batters = pre_batters.rename(columns={'BATS': 'Bats'})

    # Define groups for rounding
    three_decimals = ['AVG', 'OBP', 'SLG', 'OPS', 'ISO', 'BABIP', 'xBA', 'xSLG', 'wOBA', 'xwOBA']
    two_decimals = ['WPA', 'BB/K']
    percent_columns = ['BB%', 'K%', 'O-Contact%', 'Z-Contact%', 'Barrel%', 'HardHit%']

    # Apply rounding but keep numeric types
    pre_batters[three_decimals] = pre_batters[three_decimals].round(3)
    pre_batters[two_decimals] = pre_batters[two_decimals].round(2)
    pre_batters[percent_columns] = (pre_batters[percent_columns] * 100).round(1)
    
    return pre_batters[['Name', 'Age', 'CBLCard', 'is_carded', 'Team', 'CBLPos', 'Bats',
                    'AB', 'AVG', 'OBP', 'SLG', 'OPS', 'wRC+', 'WAR', 'H', '2B', '3B', 'HR', 'R', 'RBI', 
                    'BB', 'SO', 'SB', 'BB%', 'K%', 'BB/K', 'ISO', 'BABIP', 'xBA', 'xSLG', 'wOBA', 'xwOBA',
                    'WPA', 'O-Contact%', 'Z-Contact%', 'Barrel%', 'HardHit%', 'FanGraph ID', 'MLBID', 'MLBNAME']]

@st.cache_data(ttl=1800)
def get_pitchers(map):
    cbl_pitchers = pd.read_csv('pitchers_sup.csv')
    pitching_stats = pyb.pitching_stats(2024, qual=0)

    pre_pitchers = pd.merge(cbl_pitchers, pitching_stats, left_on='FanGraph ID', right_on='IDfg', how='inner')

    pre_pitchers['is_carded'] = np.where(pre_pitchers['CBL5Percent'].astype(str) == 'NC', False, True)

    pre_pitchers = pd.merge(pre_pitchers, map[['IDFANGRAPHS', 'THROWS', 'MLBNAME', 'MLBID']], 
                       left_on='FanGraph ID', right_on='IDFANGRAPHS', 
                       how='left')

    pre_pitchers = pre_pitchers.rename(columns={'THROWS': 'Throws'})

    # Define groups for rounding
    one_decimal = ['IP', 'Start-IP', 'Relief-IP']
    two_decimals = ['ERA', 'FIP', 'K/9', 'BB/9', 'H/9', 'HR/9', 'xERA', 'xFIP', 'WPA']
    three_decimals = ['WHIP', 'AVG', 'BABIP']
    percent_columns = ['LOB%', 'GB%', 'FB%', 'K%', 'BB%', 'Soft%', 'Med%', 'Hard%']

    # Apply rounding while keeping numeric types
    pre_pitchers[one_decimal] = pre_pitchers[one_decimal].round(1)
    pre_pitchers[two_decimals] = pre_pitchers[two_decimals].round(2)
    pre_pitchers[three_decimals] = pre_pitchers[three_decimals].round(3)
    pre_pitchers[percent_columns] = (pre_pitchers[percent_columns] * 100).round(1)

    return pre_pitchers[['Name', 'Age', 'CBLCard', 'is_carded', 'Team', 'CBLPos', 'Throws',
                        'G', 'GS', 'IP', 'ERA', 'FIP', 'WHIP', 'WAR', 'K/9', 'BB/9', 'H', 'R', 'ER', 
                        'HR', 'BB', 'SV', 'H/9', 'HR/9', 'xERA', 'xFIP', 'AVG', 'BABIP', 'LOB%', 'GB%', 
                        'FB%', 'K%', 'BB%', 'Soft%', 'Med%', 'Hard%', 'Stuff+', 'Location+', 'Pitching+', 
                        'WPA','Start-IP', 'Relief-IP', 'FanGraph ID', 'MLBID', 'MLBNAME']]

# Function to generate Baseball Savant URLs
def gen_savant_url(row):
    if pd.isna(row['MLBNAME']) or pd.isna(row['MLBID']):
        return None  # If missing data, return None
    
    # Ensure MLBNAME is a string
    name_parts = str(row['MLBNAME']).strip().split(' ')
    
    # Define suffixes like "Jr.", "Sr.", etc.
    suffixes = {'jr', 'sr', 'ii', 'iii', 'iv', 'v'}
    
    # Special case: Handle hyphenated last names correctly
    if '-' in name_parts[-1]:  # If last name is hyphenated (e.g., Strange-Gordon)
        last_name = name_parts[-1]  # Keep the full hyphenated last name
        first_name = "-".join(name_parts[:-1])
    elif name_parts[-1].lower() in suffixes:  # Handle suffix cases like "Jr."
        last_name = name_parts[-2] + "-" + name_parts[-1].lower()
        first_name = "-".join(name_parts[:-2])
    else:
        last_name = name_parts[-1]
        first_name = "-".join(name_parts[:-1])
    
    # Ensure names are lowercase and remove special characters
    first_name = re.sub(r"[^a-z0-9\-]", "", first_name.lower())
    last_name = re.sub(r"[^a-z0-9\-]", "", last_name.lower())
    
    player_id = int(row['MLBID'])  # Convert MLBID to an integer
    
    return f"https://baseballsavant.mlb.com/savant-player/{first_name}-{last_name}-{player_id}"

id_map = get_map()

batters = get_batters(id_map)
batters['Savant Link'] = batters.apply(gen_savant_url, axis=1)
batters = batters.drop(columns=['FanGraph ID', 'MLBID', 'MLBNAME'])

pitchers = get_pitchers(id_map)
pitchers['Savant Link'] = pitchers.apply(gen_savant_url, axis=1)
pitchers = pitchers.drop(columns=['FanGraph ID', 'MLBID', 'MLBNAME'])

fielders = pd.read_csv('defense.csv')
fielders = fielders[fielders['B/P'] == 'BAT']
fielders['Name'] = fielders['FIRST'] + ' ' + fielders['LAST']
fielders = fielders[['LG', 'TM', 'Name', 'C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF']]

column_config_batters = {
    "Name": st.column_config.Column("Name", pinned=True),
    "AVG": st.column_config.NumberColumn("AVG", format="%.3f"),
    "OBP": st.column_config.NumberColumn("OBP", format="%.3f"),
    "SLG": st.column_config.NumberColumn("SLG", format="%.3f"),
    "OPS": st.column_config.NumberColumn("OPS", format="%.3f"),
    "ISO": st.column_config.NumberColumn("ISO", format="%.3f"),
    "BABIP": st.column_config.NumberColumn("BABIP", format="%.3f"),
    "xBA": st.column_config.NumberColumn("xBA", format="%.3f"),
    "xSLG": st.column_config.NumberColumn("xSLG", format="%.3f"),
    "wOBA": st.column_config.NumberColumn("wOBA", format="%.3f"),
    "xwOBA": st.column_config.NumberColumn("xwOBA", format="%.3f"),
    "WPA": st.column_config.NumberColumn("WPA", format="%.2f"),
    "BB/K": st.column_config.NumberColumn("BB/K", format="%.2f"),
    "BB%": st.column_config.NumberColumn("BB%", format="%.1f%%"),
    "K%": st.column_config.NumberColumn("K%", format="%.1f%%"),
    "O-Contact%": st.column_config.NumberColumn("O-Contact%", format="%.1f%%"),
    "Z-Contact%": st.column_config.NumberColumn("Z-Contact%", format="%.1f%%"),
    "Barrel%": st.column_config.NumberColumn("Barrel%", format="%.1f%%"),
    "HardHit%": st.column_config.NumberColumn("HardHit%", format="%.1f%%"),
    "Savant Link": st.column_config.LinkColumn("Baseball Savant")
}

column_config_pitchers = {
    "Name": st.column_config.Column("Name", pinned=True),
    "IP": st.column_config.NumberColumn("IP", format="%.1f"),
    "Start-IP": st.column_config.NumberColumn("Start-IP", format="%.1f"),
    "Relief-IP": st.column_config.NumberColumn("Relief-IP", format="%.1f"),
    "ERA": st.column_config.NumberColumn("ERA", format="%.2f"),
    "FIP": st.column_config.NumberColumn("FIP", format="%.2f"),
    "K/9": st.column_config.NumberColumn("K/9", format="%.2f"),
    "BB/9": st.column_config.NumberColumn("BB/9", format="%.2f"),
    "H/9": st.column_config.NumberColumn("H/9", format="%.2f"),
    "HR/9": st.column_config.NumberColumn("HR/9", format="%.2f"),
    "xERA": st.column_config.NumberColumn("xERA", format="%.2f"),
    "xFIP": st.column_config.NumberColumn("xFIP", format="%.2f"),
    "WPA": st.column_config.NumberColumn("WPA", format="%.2f"),
    "WHIP": st.column_config.NumberColumn("WHIP", format="%.3f"),
    "AVG": st.column_config.NumberColumn("AVG", format="%.3f"),
    "BABIP": st.column_config.NumberColumn("BABIP", format="%.3f"),
    "LOB%": st.column_config.NumberColumn("LOB%", format="%.1f%%"),
    "GB%": st.column_config.NumberColumn("GB%", format="%.1f%%"),
    "FB%": st.column_config.NumberColumn("FB%", format="%.1f%%"),
    "K%": st.column_config.NumberColumn("K%", format="%.1f%%"),
    "BB%": st.column_config.NumberColumn("BB%", format="%.1f%%"),
    "Soft%": st.column_config.NumberColumn("Soft%", format="%.1f%%"),
    "Med%": st.column_config.NumberColumn("Med%", format="%.1f%%"),
    "Hard%": st.column_config.NumberColumn("Hard%", format="%.1f%%"),
    "Savant Link": st.column_config.LinkColumn("Baseball Savant")
}

selected_page = st.selectbox(label="page", options=["Batters", "Pitchers", "Defense"], label_visibility='hidden')

if selected_page == "Batters":
    data = batters
    column_config = column_config_batters
    pos_options = ['DH', 'CA', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF']
elif selected_page == "Pitchers":
    data = pitchers
    column_config = column_config_pitchers
    pos_options = ['SP', 'RP']
elif selected_page == "Defense":
    data = fielders
    column_config = {}
    pos_options = [
        "ARI", "ATL", "BAL", "BOS", "CHC", "CHW", "CIN", "CLE", "COL", "DET",
        "HOU", "KCR", "LAA", "LAD", "MIA", "MIL", "MIN", "NYM", "NYY", "OAK",
        "PHI", "PIT", "SDP", "SFG", "SEA", "STL", "TBR", "TEX", "TOR", "WSN"
    ]

if selected_page != "Defense":
    left_col, left_mid_col, right_mid_col, right_col = st.columns([1, 1, 1, 1], gap="medium")
    
    with left_col:
        carded_only = st.checkbox('Carded Players Only')
        if carded_only:
            data = data[data['is_carded']]

    with left_mid_col:
        positions = st.multiselect("Filter by Position", options=pos_options)
        if positions:
            data = data[data['CBLPos'].apply(lambda x: any(pos in x.split('/') for pos in positions))]
    with right_mid_col:
        age_range = st.slider("Filter by Age", 
                            min_value=data['Age'].min(), 
                            max_value=data['Age'].max(), 
                            value=(data['Age'].min(), data['Age'].max())
                        )
        data = data[(data['Age'] >= age_range[0]) & (data['Age'] <= age_range[1])]
    with right_col:
        if selected_page == "Batters":
            usage_range = st.slider("Filter by ABs", 
                                min_value=data['AB'].min(), 
                                max_value=data['AB'].max(), 
                                value=(data['AB'].min(), data['AB'].max())
                            )
            data = data[(data['AB'] >= usage_range[0]) & (data['AB'] <= usage_range[1])]
        else:
            usage_range = st.slider("Filter by IP", 
                                min_value=data['IP'].min(), 
                                max_value=data['IP'].max(), 
                                value=(data['IP'].min(), data['IP'].max()),
                                step=0.1,
                                format="%.1f"
                            )
            data = data[(data['IP'] >= usage_range[0]) & (data['IP'] <= usage_range[1])]
else:
    teams = st.multiselect("Filter by Team", options=pos_options)
    if teams:
        data = data[data['TM'].isin(teams)]
st.dataframe(data, column_config=column_config, height=750, hide_index=True)