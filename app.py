from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)

# 正式上線時建議只允許你的前端網域
CORS(
    app,
    resources={r"/*": {"origins": "*"}}
)

@app.get("/")
def home():
    return jsonify({
        "ok": True,
        "service": "tbl-sim-api",
        "message": "Render API is running"
    })

@app.get("/health")
def health():
    return jsonify({"ok": True})

@app.post("/simulate")
def simulate():
    try:
        payload = request.get_json(force=True) or {}
        home_team = payload.get("home_team")
        away_team = payload.get("away_team")

        if not home_team or not away_team:
            return jsonify({
                "ok": False,
                "error": "缺少 home_team 或 away_team"
            }), 400

        result = run_simulation(home_team, away_team)

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


def run_simulation(home_team, away_team):
    """
    這裡先放包裝函式。
    你之後把你原本的 Python 比賽引擎邏輯接到這裡。
    """

    home_name = home_team.get("info", {}).get("teamName", "主隊")
    away_name = away_team.get("info", {}).get("teamName", "客隊")

    home_lineup = home_team.get("activeLineup", [])
    away_lineup = away_team.get("activeLineup", [])

    # 範例：先用很簡單的總評加總模擬
    home_score_base = team_score_base(home_lineup)
    away_score_base = team_score_base(away_lineup)

    home_score = max(60, round(home_score_base))
    away_score = max(60, round(away_score_base))

    winner = home_name if home_score >= away_score else away_name

    return {
        "homeTeam": home_name,
        "awayTeam": away_name,
        "homeScore": home_score,
        "awayScore": away_score,
        "winner": winner,
        "playerPoints": {
            "home": build_player_points(home_lineup, home_score),
            "away": build_player_points(away_lineup, away_score)
        }
    }


def team_score_base(lineup):
    if not lineup:
        return 60

    total_ovr = sum(player.get("ovr", 0) for player in lineup)
    avg_ovr = total_ovr / len(lineup)

    total_shot = 0
    total_iq = 0
    total_stamina = 0

    for p in lineup:
        shot = p.get("SHOT", {})
        bliq = p.get("BLIQ", {})

        total_shot += shot.get("cls", 0) + shot.get("stb", 0) + shot.get("rng", 0)
        total_iq += bliq.get("off", 0) + bliq.get("ctr", 0) + bliq.get("ofb", 0)
        total_stamina += p.get("stamina", 0)

    avg_shot = total_shot / len(lineup)
    avg_iq = total_iq / len(lineup)
    avg_stamina = total_stamina / len(lineup)

    return 35 + avg_ovr * 0.18 + avg_shot * 0.12 + avg_iq * 0.08 + avg_stamina * 0.05


def build_player_points(lineup, team_score):
    if not lineup:
        return []

    weights = []
    for p in lineup:
        shot = p.get("SHOT", {})
        bliq = p.get("BLIQ", {})
        weight = (
            shot.get("cls", 0) +
            shot.get("stb", 0) +
            shot.get("rng", 0) +
            bliq.get("off", 0)
        )
        weights.append(max(weight, 1))

    total_weight = sum(weights)
    result = []

    running_sum = 0
    for i, p in enumerate(lineup):
        if i == len(lineup) - 1:
            points = team_score - running_sum
        else:
            points = round(team_score * weights[i] / total_weight)
            running_sum += points

        result.append({
            "slot": p.get("slot", "-"),
            "name": p.get("name", "未知球員"),
            "points": points
        })

    return result


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)