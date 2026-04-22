from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from GameSim import run_simulation

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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)