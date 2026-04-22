from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import math
import random


class GameSim:
    QUARTERS = 4
    SECONDS_PER_QUARTER = 12 * 60
    POSSESSION_SECONDS = 24
    POINTS_PER_MADE_SHOT = 2

    def __init__(self, home_team, away_team, seed=None):
        self.home_team = home_team or {}
        self.away_team = away_team or {}

        if seed is not None:
            random.seed(seed)

        self.home_name = self.home_team.get("info", {}).get("teamName", "主隊")
        self.away_name = self.away_team.get("info", {}).get("teamName", "客隊")

        self.home_lineup = self._normalize_lineup(self.home_team.get("activeLineup", []))
        self.away_lineup = self._normalize_lineup(self.away_team.get("activeLineup", []))

        if len(self.home_lineup) == 0 or len(self.away_lineup) == 0:
            raise ValueError("home_team 或 away_team 缺少 activeLineup 資料")

        self.score = {
            "home": 0,
            "away": 0
        }

        self.player_points = {
            "home": self._init_player_points(self.home_lineup),
            "away": self._init_player_points(self.away_lineup)
        }

        self.jump_ball_winner = None
        self.possession_team = None
        self.game_log = []

    # =========================
    # 公開主流程
    # =========================
    def simulate_game(self):
        self.possession_team = self._jump_ball()
        self.game_log.append(f"跳球結果：{self.jump_ball_winner} 獲得第一波球權")

        for quarter in range(1, self.QUARTERS + 1):
            self._simulate_quarter(quarter)

        winner = self.home_name if self.score["home"] >= self.score["away"] else self.away_name

        return {
            "homeTeam": self.home_name,
            "awayTeam": self.away_name,
            "homeScore": self.score["home"],
            "awayScore": self.score["away"],
            "winner": winner,
            "playerPoints": {
                "home": self._build_player_points_output("home", self.home_lineup),
                "away": self._build_player_points_output("away", self.away_lineup)
            },
            "jumpBallWinner": self.jump_ball_winner,
            "gameLog": self.game_log
        }

    # =========================
    # 單節模擬
    # =========================
    def _simulate_quarter(self, quarter):
        possessions_in_quarter = self.SECONDS_PER_QUARTER // self.POSSESSION_SECONDS
        self.game_log.append(f"第 {quarter} 節開始")

        for possession_index in range(possessions_in_quarter):
            self._simulate_possession(quarter, possession_index + 1)

        self.game_log.append(
            f"第 {quarter} 節結束：{self.home_name} {self.score['home']} - {self.away_name} {self.score['away']}"
        )

    # =========================
    # 單回合模擬
    # =========================
    def _simulate_possession(self, quarter, possession_no):
        offense_side = self.possession_team
        defense_side = "away" if offense_side == "home" else "home"

        offense_team_name = self.home_name if offense_side == "home" else self.away_name
        defense_team_name = self.away_name if offense_side == "home" else self.home_name

        offense_lineup = self.home_lineup if offense_side == "home" else self.away_lineup
        defense_lineup = self.away_lineup if offense_side == "home" else self.home_lineup

        shooter = random.choice(offense_lineup)
        defender = self._find_same_slot_defender(shooter["slot"], defense_lineup)

        shot_rate = self._calculate_shot_success_rate(shooter, defender)
        shot_roll = random.uniform(0, 100)
        made = shot_roll <= shot_rate

        if made:
            self.score[offense_side] += self.POINTS_PER_MADE_SHOT
            self.player_points[offense_side][shooter["id"]] += self.POINTS_PER_MADE_SHOT

        self.game_log.append(
            f"Q{quarter} 回合{possession_no} | "
            f"{offense_team_name}進攻 | "
            f"{shooter['slot']} {shooter['name']} 出手，"
            f"{defense_team_name} {defender['slot']} {defender['name']} 防守 | "
            f"命中率 {shot_rate:.1f}% | "
            f"擲骰 {shot_roll:.1f} | "
            f"{'命中' if made else '未進'}"
        )

        # 回合結束，直接換邊
        self.possession_team = defense_side

    # =========================
    # 跳球
    # =========================
    def _jump_ball(self):
        home_center = self._find_same_slot_defender("C", self.home_lineup)
        away_center = self._find_same_slot_defender("C", self.away_lineup)

        home_jmp = self._get_nested(home_center, "ATLC", "jmp")
        away_jmp = self._get_nested(away_center, "ATLC", "jmp")

        if home_jmp > away_jmp:
            self.jump_ball_winner = self.home_name
            return "home"
        elif away_jmp > home_jmp:
            self.jump_ball_winner = self.away_name
            return "away"
        else:
            winner_side = random.choice(["home", "away"])
            self.jump_ball_winner = self.home_name if winner_side == "home" else self.away_name
            return winner_side

    # =========================
    # 命中率公式
    # =========================
    def _calculate_shot_success_rate(self, shooter, defender):
        """
        第一版簡單公式：
        - 先給一個基礎命中率 base_rate
        - 投籃能力 = 速度 + 彈跳 + 進攻智商
        - 防守負加成 = 彈跳 + 敏捷 + 防守智商
        - 最終命中率 = base_rate + offense_bonus - defense_penalty

        目前先控制在 15% ~ 85% 區間，避免過度極端。
        """

        shooter_spd = self._get_nested(shooter, "ATLC", "spd")
        shooter_jmp = self._get_nested(shooter, "ATLC", "jmp")
        shooter_off_iq = self._get_nested(shooter, "BLIQ", "off")

        defender_jmp = self._get_nested(defender, "ATLC", "jmp")
        defender_dex = self._get_nested(defender, "ATLC", "dex")
        defender_def_iq = self._get_nested(defender, "BLIQ", "def")

        offense_score = shooter_spd + shooter_jmp + shooter_off_iq
        defense_score = defender_jmp + defender_dex + defender_def_iq

        base_rate = 45.0
        offense_bonus = (offense_score - 30) * 1.2
        defense_penalty = (defense_score - 30) * 1.0

        final_rate = base_rate + offense_bonus - defense_penalty
        final_rate = max(15.0, min(85.0, final_rate))

        return final_rate

    # =========================
    # 工具函式
    # =========================
    def _normalize_lineup(self, lineup):
        normalized = []

        for player in lineup:
            if not isinstance(player, dict):
                continue

            normalized.append({
                "slot": player.get("slot", "UNK"),
                "id": player.get("id", f"UNKNOWN_{len(normalized)}"),
                "name": player.get("name", "未知球員"),
                "ATLC": player.get("ATLC", {}),
                "BLIQ": player.get("BLIQ", {})
            })

        return normalized

    def _find_same_slot_defender(self, slot, defense_lineup):
        for player in defense_lineup:
            if player.get("slot") == slot:
                return player

        # 如果真的找不到同位置，退而求其次隨機抓一個
        return random.choice(defense_lineup)

    def _get_nested(self, player, group_key, attr_key):
        return player.get(group_key, {}).get(attr_key, 0)

    def _init_player_points(self, lineup):
        return {player["id"]: 0 for player in lineup}

    def _build_player_points_output(self, side, lineup):
        result = []

        for player in lineup:
            result.append({
                "slot": player["slot"],
                "name": player["name"],
                "points": self.player_points[side].get(player["id"], 0)
            })

        return result


def run_simulation(home_team, away_team, seed=None):
    sim = GameSim(home_team, away_team, seed=seed)
    return sim.simulate_game()