"""阶段3：把全量详情原始数据清洗成分析用宽表。

输入：
  data/raw/valorant_details_full.json （浏览器采集的原始数据）
  data/raw/champions.json             （特工 id->名称）
输出：
  data/battles_detailed.csv
  data/battles_detailed.json
"""
import csv
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw")

# 地图代号 -> 国服官方中文名（均经官网/BWIKI/VALORANT Wiki 核实）
MAP_NAMES = {
    "Ascent": "亚海悬城",
    "Triad": "隐世修所",
    "Bonsai": "霓虹町",
    "Juliett": "日落之城",
    "Infinity": "幽邃地窟",
    "Jam": "莲华古城",
    "Foxtrot": "微风岛屿",
    "Plummet": "天枢云阙",
}

# 段位 tier -> 名称（国服 11=白银III，其余按需补；保留数字字段）
# 参考：0未定级 1-3铁 4-6铜 7-9银? 实际VAL: 1-3 iron,4-6 bronze,7-9 silver...
# 用户 competitiveTier=11 且页面显示白银III -> 国服映射与国际服不同，
# 不在脚本里硬猜，tier 数字原样保留。


def load_champs():
    with open(os.path.join(RAW, "champions.json"), encoding="utf-8") as f:
        d = json.load(f)
    return {c["characterId"]: (c["name"], c.get("en_name", "")) for c in d["characterStats"]}


def to_int(v, default=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def main():
    champs = load_champs()
    with open(os.path.join(RAW, "valorant_details_full.json"), encoding="utf-8") as f:
        raw = json.load(f)

    rows = []
    for item in raw["battles"]:
        L = item["list"]
        S = item["self_detail"] or {}
        map_code = L["mapId"].rstrip("/").split("/")[-1]
        char_id = L["characterId"]
        agent_name, agent_en = champs.get(char_id, ("", ""))

        rounds = to_int(L.get("roundsPlayed"))
        hs = to_int(S.get("totalHeadshots"))
        kills = to_int(L.get("statsKills"))
        deaths = to_int(L.get("statsDeaths"))
        assists = to_int(L.get("statsAssists"))
        kast = to_int(S.get("kast"))

        rows.append({
            "date": L["dtEventTime"][:10],
            "datetime": L["dtEventTime"],
            "win": 1 if to_int(L.get("wonMatch")) == 1 else 0,
            "map_code": map_code,
            "map_name": MAP_NAMES.get(map_code, ""),
            "agent": agent_name,
            "agent_en": agent_en,
            "tier_before": to_int(L.get("CompetitiveTierBefore")),
            "tier_after": to_int(L.get("CompetitiveTierAfter")),
            "rr_earned": to_int(L.get("CompetitiveTierRankedRatingEarned")),
            "rr_after": to_int(L.get("competitiveTierRankedRatingAfter")),
            "rounds_played": rounds,
            "rounds_won": to_int(L.get("roundsWon")),
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
            "kda_ratio": round((kills + assists) / deaths, 3) if deaths else None,
            "score": to_int(L.get("statsScore")),
            "headshots": hs,
            "bodyshots": to_int(S.get("totalBodyshots")),
            "legshots": to_int(S.get("totalLegshots")),
            "headshot_rate": round(hs / kills, 3) if kills else None,
            "damage": to_int(S.get("totalDamage")),
            "adr": round(to_int(S.get("totalDamage")) / rounds, 1) if rounds else None,
            "kast": kast,
            "economy_score": to_int(S.get("economyScore")),
            "first_kills": to_int(S.get("firstKillCount")),
            "plants": to_int(S.get("plantCount")),
            "defuses": to_int(S.get("defuseCount")),
            "clutches": to_int(S.get("clutchCount")),
            "aces": to_int(S.get("aceCount")),
            "thrifty": to_int(S.get("thriftyCount")),
            "flawless": to_int(S.get("flawlessCount")),
            "triple_kills": to_int(S.get("tripleKillCount")),
            "quadra_kills": to_int(S.get("quadraKillCount")),
            "penta_kills": to_int(S.get("pentaKillCount")),
            "duration_min": round(to_int(L.get("gameLengthMillis")) / 60000, 2),
            "match_mvp": to_int(S.get("isMatchMvp")),
            "team_mvp": to_int(S.get("isTeamMvp")),
            "svp": to_int(S.get("svp")),
        })

    rows.sort(key=lambda r: r["datetime"], reverse=True)

    out_json = os.path.join(BASE, "data", "battles_detailed.json")
    out_csv = os.path.join(BASE, "data", "battles_detailed.csv")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"wrote {len(rows)} battles")
    missing_agent = [r["date"] for r in rows if not r["agent"]]
    missing_map = sorted({r["map_code"] for r in rows if not r["map_name"]})
    print("missing agent names:", missing_agent)
    print("maps pending name:", missing_map)


if __name__ == "__main__":
    main()
