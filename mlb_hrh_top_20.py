import streamlit as st
import requests
from datetime import date, timedelta
from collections import defaultdict

# --- Functions ---
def get_player_stats_for_date(game_date):
    stats_by_player = {}

    schedule_url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={game_date}"
    response = requests.get(schedule_url)
    if response.status_code != 200:
        return stats_by_player

    games = response.json().get("dates", [])
    if not games or not games[0].get("games"):
        return stats_by_player

    for game in games[0]["games"]:
        game_pk = game["gamePk"]
        boxscore_url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
        boxscore_response = requests.get(boxscore_url)
        if boxscore_response.status_code != 200:
            continue

        boxscore = boxscore_response.json()
        for team_key in ["home", "away"]:
            team_info = boxscore["teams"][team_key]["team"]
            opponent_key = "away" if team_key == "home" else "home"
            opponent_info = boxscore["teams"][opponent_key]["team"]

            players = boxscore["teams"][team_key]["players"]
            for player_data in players.values():
                person = player_data.get("person", {})
                name = person.get("fullName", "Unknown")
                stats = player_data.get("stats", {}).get("batting")
                if not stats:
                    continue

                hits = stats.get("hits", 0)
                runs = stats.get("runs", 0)
                rbi = stats.get("rbi", 0)

                if name not in stats_by_player:
                    stats_by_player[name] = {
                        "hits": 0,
                        "runs": 0,
                        "rbi": 0,
                        "team": team_info.get("name", ""),
                        "opponent": opponent_info.get("name", "")
                    }

                player_stats = stats_by_player[name]
                player_stats["hits"] += hits
                player_stats["runs"] += runs
                player_stats["rbi"] += rbi

    return stats_by_player

def get_todays_lineup_players(game_date):
    lineup_players = set()

    schedule_url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={game_date}"
    response = requests.get(schedule_url)
    if response.status_code != 200:
        return lineup_players

    games = response.json().get("dates", [])
    if not games or not games[0].get("games"):
        return lineup_players

    for game in games[0]["games"]:
        game_pk = game["gamePk"]
        live_feed_url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
        live_response = requests.get(live_feed_url)
        if live_response.status_code != 200:
            continue

        data = live_response.json()
        for team in ["home", "away"]:
            players = data.get("liveData", {}).get("boxscore", {}).get("teams", {}).get(team, {}).get("players", {})
            for info in players.values():
                if info.get("stats", {}).get("batting", {}).get("gamesPlayed") == 1:
                    full_name = info.get("person", {}).get("fullName")
                    if full_name:
                        lineup_players.add(full_name)

    return lineup_players

# --- Streamlit App ---
st.set_page_config(page_title="MLB H+R+RBI Predictions", layout="wide")
st.title("📊 Top 20 MLB H+R+RBI Picks (Last 10 Days)")

today = date.today()
today_str = today.isoformat()

st.markdown(f"**Date Analyzed:** `{today_str}`")
with st.spinner("Analyzing data... this may take 20-30 seconds ⏳"):

    lineup_players = get_todays_lineup_players(today_str)
    cumulative_stats = defaultdict(lambda: {"hits": 0, "runs": 0, "rbi": 0, "team": "", "opponent": ""})

    for i in range(10):
        day = (today - timedelta(days=i)).isoformat()
        stats = get_player_stats_for_date(day)
        for name, data in stats.items():
            cumulative_stats[name]["hits"] += data["hits"]
            cumulative_stats[name]["runs"] += data["runs"]
            cumulative_stats[name]["rbi"] += data["rbi"]
            cumulative_stats[name]["team"] = data["team"]
            cumulative_stats[name]["opponent"] = data["opponent"]

    player_stats = []
    for name, data in cumulative_stats.items():
        if name not in lineup_players:
            continue
        total_events = data["hits"] + data["runs"] + data["rbi"]
        avg_per_game = total_events / 10
        player_stats.append({
            "Name": name,
            "Team": data["team"],
            "Opponent": data["opponent"],
            "10-Day AVG H+R+RBI": round(avg_per_game, 2),
            "Hits": data["hits"],
            "Runs": data["runs"],
            "RBIs": data["rbi"],
            "Pick": "Over" if avg_per_game > 1.5 else "Under"
        })

    sorted_stats = sorted(player_stats, key=lambda x: x["10-Day AVG H+R+RBI"], reverse=True)
    top_20_df = sorted_stats[:20]

    st.success("✅ Top 20 Confirmed Starters Likely to Go Over 1.5 H+R+RBI:")
    st.dataframe(top_20_df, use_container_width=True)
