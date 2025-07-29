
import streamlit as st
import requests
import json
import os
from datetime import datetime

# ⚠️ Replace this with your actual API key from API-Football
API_KEY = "ae9150d9d516423114b2ff7e3df54a21"
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# File to store prediction logs
LOG_FILE = "match_predictions.json"

# Load previous predictions
def load_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    return []

# Save prediction to log
def save_prediction(log):
    logs = load_logs()
    logs.append(log)
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=4)

# Get leagues
def get_leagues():
    url = f"{BASE_URL}/leagues"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()["response"]
    return []

# Get upcoming fixtures
def get_upcoming_fixtures(league_id=39, next_n=10):
    url = f"{BASE_URL}/fixtures?league={league_id}&season=2024&next={next_n}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()["response"]
    return []

# Get team statistics
def get_team_stats(team_id, league_id=39):
    url = f"{BASE_URL}/teams/statistics?league={league_id}&season=2024&team={team_id}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        stats = response.json()["response"]
        avg_scored = stats["goals"]["for"]["average"]["total"]
        avg_conceded = stats["goals"]["against"]["average"]["total"]
        return float(avg_scored), float(avg_conceded)
    return 0.0, 0.0

# Predict 2+ goal win
def predict_2_goal_win(team1_stats, team2_stats):
    t1_scored, t1_conceded = team1_stats
    t2_scored, t2_conceded = team2_stats
    score_diff = (t1_scored - t2_conceded) - (t2_scored - t1_conceded)
    if score_diff >= 2:
        confidence = min(95, 50 + (score_diff * 10))
        return True, round(confidence)
    return False, 0

# Confirm a fixture result
def get_fixture_result(fixture_id):
    url = f"{BASE_URL}/fixtures?id={fixture_id}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        match = response.json()["response"][0]
        score_home = match["goals"]["home"]
        score_away = match["goals"]["away"]
        full_time = match["fixture"]["status"]["short"] == "FT"
        return full_time, score_home, score_away
    return False, None, None

# Streamlit UI
st.title("📊 Football Match Predictor + Tracker")
st.info("Replace 'YOUR_API_KEY_HERE' with your API key to use this app")

if API_KEY == "YOUR_API_KEY_HERE":
    st.warning("⚠️ Please enter your API key in the code to activate live data.")
else:
    leagues = get_leagues()
    top_leagues = [l for l in leagues if l["league"]["type"] == "League" and l["season"] == 2024]
    league_map = {f"{l['league']['name']} ({l['country']['name']})": l["league"]["id"] for l in top_leagues}
    selected_league = st.selectbox("Choose a League", list(league_map.keys()))
    league_id = league_map[selected_league]

    fixtures = get_upcoming_fixtures(league_id=league_id)
    if fixtures:
        fixture_options = [f"{f['teams']['home']['name']} vs {f['teams']['away']['name']} - {f['fixture']['date'][:10]}" for f in fixtures]
        selected = st.selectbox("Choose a Fixture", fixture_options)
        selected_fixture = fixtures[fixture_options.index(selected)]
        fixture_id = selected_fixture["fixture"]["id"]
        home_team = selected_fixture["teams"]["home"]
        away_team = selected_fixture["teams"]["away"]

        st.subheader(f"🔍 {home_team['name']} vs {away_team['name']}")

        team1_stats = get_team_stats(home_team["id"], league_id)
        team2_stats = get_team_stats(away_team["id"], league_id)

        if st.button("Predict Outcome"):
            will_win_by_2, confidence = predict_2_goal_win(team1_stats, team2_stats)
            timestamp = datetime.now().isoformat()
            result_text = ""
            if will_win_by_2:
                result_text = f"✅ Predicted: {home_team['name']} will win by 2+ goals. Confidence: {confidence}%"
                st.success(result_text)
                st.metric("Confidence", f"{confidence}%")
            else:
                result_text = "❌ No strong prediction for 2+ goal margin"
                st.error(result_text)

            log = {
                "fixture_id": fixture_id,
                "home": home_team["name"],
                "away": away_team["name"],
                "prediction": "2+ goal win" if will_win_by_2 else "No prediction",
                "confidence": confidence,
                "timestamp": timestamp,
                "league": selected_league,
            }
            save_prediction(log)

        with st.expander("📋 View Past Predictions"):
            logs = load_logs()
            for log in reversed(logs[-10:]):
                st.write(f"- {log['home']} vs {log['away']} | Prediction: {log['prediction']} | Confidence: {log['confidence']}% | {log['timestamp'][:16]}")

        with st.expander("✅ Confirm Match Result"):
            if st.button("Check Final Score"):
                full_time, h_score, a_score = get_fixture_result(fixture_id)
                if full_time:
                    margin = abs(h_score - a_score)
                    winner = home_team["name"] if h_score > a_score else away_team["name"]
                    if margin >= 2:
                        st.success(f"Match ended {h_score}-{a_score}. {winner} won by {margin} goals ✅")
                    else:
                        st.error(f"Match ended {h_score}-{a_score}. Only {margin}-goal margin ❌")
                else:
                    st.warning("⏳ Match has not finished yet.")
    else:
        st.error("No fixtures found.")
