"""
data_generator.py - Tạo dữ liệu TFT giả lập thực tế cho thực nghiệm
Bao gồm các meta composition với tỷ lệ thắng khác nhau và "hidden meta"
"""

import random
import json
import csv
import os
import itertools
from collections import Counter

import numpy as np
import pandas as pd

# ===================== TFT SET DATA =====================

CHAMPIONS = {
    # Cost 1
    "Samira": {"cost": 1, "traits": ["Noxus", "Challenger"]},
    "Poppy": {"cost": 1, "traits": ["Demacia", "Bastion"]},
    "Malzahar": {"cost": 1, "traits": ["Void", "Sorcerer"]},
    "Tristana": {"cost": 1, "traits": ["Yordle", "Gunner"]},
    "Cassiopeia": {"cost": 1, "traits": ["Noxus", "Invoker"]},
    "Renekton": {"cost": 1, "traits": ["Shurima", "Bruiser"]},
    "Chomath": {"cost": 1, "traits": ["Void", "Bruiser"]},
    "Irelia": {"cost": 1, "traits": ["Ionia", "Challenger"]},
    "Orianna": {"cost": 1, "traits": ["Piltover", "Sorcerer"]},
    "Jhin": {"cost": 1, "traits": ["Ionia", "Gunner"]},
    # Cost 2
    "Warwick": {"cost": 2, "traits": ["Zaun", "Challenger"]},
    "Jinx": {"cost": 2, "traits": ["Zaun", "Gunner"]},
    "Vi": {"cost": 2, "traits": ["Piltover", "Bruiser"]},
    "Swain": {"cost": 2, "traits": ["Noxus", "Sorcerer"]},
    "Soraka": {"cost": 2, "traits": ["Targon", "Invoker"]},
    "Ashe": {"cost": 2, "traits": ["Freljord", "Gunner"]},
    "Galio": {"cost": 2, "traits": ["Demacia", "Bastion"]},
    "Taliyah": {"cost": 2, "traits": ["Shurima", "Sorcerer"]},
    # Cost 3
    "Ekko": {"cost": 3, "traits": ["Zaun", "Rogue"]},
    "Katarina": {"cost": 3, "traits": ["Noxus", "Rogue"]},
    "VelKoz": {"cost": 3, "traits": ["Void", "Sorcerer"]},
    "Lux": {"cost": 3, "traits": ["Demacia", "Sorcerer"]},
    "Jayce": {"cost": 3, "traits": ["Piltover", "Gunner"]},
    "Karma": {"cost": 3, "traits": ["Ionia", "Invoker"]},
    "Darius": {"cost": 3, "traits": ["Noxus", "Bruiser"]},
    "Taric": {"cost": 3, "traits": ["Targon", "Bastion"]},
    "Shen": {"cost": 3, "traits": ["Ionia", "Bastion"]},
    # Cost 4
    "Kayn": {"cost": 4, "traits": ["Ionia", "Challenger", "Rogue"]},
    "Aatrox": {"cost": 4, "traits": ["Darkin", "Bruiser"]},
    "Silco": {"cost": 4, "traits": ["Zaun", "Invoker"]},
    "AurelionSol": {"cost": 4, "traits": ["Targon", "Sorcerer"]},
    "Urgot": {"cost": 4, "traits": ["Zaun", "Gunner"]},
    "Garen": {"cost": 4, "traits": ["Demacia", "Bastion"]},
    "Aphelios": {"cost": 4, "traits": ["Targon", "Gunner"]},
    "Azir": {"cost": 4, "traits": ["Shurima", "Invoker"]},
    # Cost 5
    "Ryze": {"cost": 5, "traits": ["Shurima", "Sorcerer", "Invoker"]},
    "Belveth": {"cost": 5, "traits": ["Void", "Challenger"]},
    "Heimerdinger": {"cost": 5, "traits": ["Piltover", "Yordle", "Sorcerer"]},
    "Sion": {"cost": 5, "traits": ["Noxus", "Bruiser"]},
    "KSante": {"cost": 5, "traits": ["Shurima", "Bastion"]},
}

ITEMS = [
    "InfinityEdge", "BloodThirster", "RapidFirecannon", "GuinsoosRageblade",
    "JeweledGauntlet", "BlueBuff", "Morellonomicon", "GiantSlayer",
    "HandOfJustice", "LastWhisper", "Deathblade", "HextechGunblade",
    "IonicSpark", "SunfireCape", "DragonsClaw", "WarmogsArmor",
    "TitansResolve", "Redemption", "ShroudOfStillness", "ZephyrGale"
]

ALL_TRAITS = [
    "Zaun", "Noxus", "Demacia", "Void", "Piltover", "Ionia",
    "Shurima", "Targon", "Freljord", "Yordle", "Darkin",
    "Challenger", "Gunner", "Sorcerer", "Bruiser", "Bastion",
    "Invoker", "Rogue"
]

# ===================== META COMPOSITIONS =====================
# Mỗi meta comp định nghĩa: core_champions, flex_slots, carry, best_items, base_winrate

META_COMPS = {
    "zaun_reroll": {
        "core": ["Warwick", "Jinx", "Ekko", "Silco"],
        "flex": ["Vi", "Urgot", "Cassiopeia", "Singed"],
        "carry": "Jinx",
        "best_items": ["InfinityEdge", "RapidFirecannon", "LastWhisper"],
        "popularity": 0.15,  # 15% chance to be picked
        "base_placement": 3.2,  # avg placement (lower = better)
    },
    "noxus_bruiser": {
        "core": ["Swain", "Katarina", "Darius", "Sion"],
        "flex": ["Cassiopeia", "Samira", "Aatrox", "Renekton"],
        "carry": "Katarina",
        "best_items": ["JeweledGauntlet", "BlueBuff", "HextechGunblade"],
        "popularity": 0.13,
        "base_placement": 3.5,
    },
    "demacia_bastion": {
        "core": ["Poppy", "Galio", "Lux", "Garen"],
        "flex": ["Taric", "Shen", "KSante", "Soraka"],
        "carry": "Lux",
        "best_items": ["JeweledGauntlet", "BlueBuff", "Morellonomicon"],
        "popularity": 0.12,
        "base_placement": 3.8,
    },
    "void_sorcerer": {
        "core": ["Malzahar", "Chomath", "VelKoz", "Belveth"],
        "flex": ["Taliyah", "AurelionSol", "Swain", "Soraka"],
        "carry": "VelKoz",
        "best_items": ["JeweledGauntlet", "GuinsoosRageblade", "GiantSlayer"],
        "popularity": 0.10,
        "base_placement": 3.6,
    },
    "ionia_challenger": {
        "core": ["Irelia", "Kayn", "Karma", "Shen"],
        "flex": ["Warwick", "Samira", "Belveth", "Jhin"],
        "carry": "Kayn",
        "best_items": ["InfinityEdge", "BloodThirster", "TitansResolve"],
        "popularity": 0.11,
        "base_placement": 3.4,
    },
    "piltover_gunner": {
        "core": ["Orianna", "Vi", "Jayce", "Heimerdinger"],
        "flex": ["Jinx", "Tristana", "Aphelios", "Ashe"],
        "carry": "Jayce",
        "best_items": ["InfinityEdge", "GiantSlayer", "RapidFirecannon"],
        "popularity": 0.09,
        "base_placement": 3.7,
    },
    # ----- HIDDEN META (rare but strong) -----
    "hidden_shurima_invoker": {
        "core": ["Renekton", "Taliyah", "Azir", "Ryze"],
        "flex": ["KSante", "Soraka", "Karma", "AurelionSol"],
        "carry": "Azir",
        "best_items": ["BlueBuff", "JeweledGauntlet", "HandOfJustice"],
        "popularity": 0.03,  # very rare
        "base_placement": 2.8,  # but very strong
    },
    "hidden_targon_carry": {
        "core": ["Soraka", "Taric", "AurelionSol", "Aphelios"],
        "flex": ["KSante", "Galio", "Lux", "Garen"],
        "carry": "Aphelios",
        "best_items": ["InfinityEdge", "RapidFirecannon", "GuinsoosRageblade"],
        "popularity": 0.02,
        "base_placement": 2.5,  # very strong
    },
    "hidden_yordle_reroll": {
        "core": ["Tristana", "Poppy", "Heimerdinger"],
        "flex": ["Lux", "Orianna", "Jinx", "Vi", "Galio"],
        "carry": "Tristana",
        "best_items": ["GuinsoosRageblade", "GiantSlayer", "RapidFirecannon"],
        "popularity": 0.02,
        "base_placement": 2.9,
    },
}

# Random comp for remaining probability
RANDOM_COMP_PROB = 1.0 - sum(c["popularity"] for c in META_COMPS.values())


def _get_active_traits(champion_names):
    """Tính trait kích hoạt từ danh sách tướng."""
    trait_counts = Counter()
    for name in champion_names:
        if name in CHAMPIONS:
            for trait in CHAMPIONS[name]["traits"]:
                trait_counts[trait] += 1
    # Trait kích hoạt khi có >= 2 tướng cùng trait
    active = {}
    for trait, count in trait_counts.items():
        if count >= 2:
            # Tier dựa trên số lượng
            if count >= 6:
                tier = 3
            elif count >= 4:
                tier = 2
            else:
                tier = 1
            active[trait] = tier
    return active


def _assign_items(champions, carry, best_items, all_items):
    """Phân bổ trang bị cho tướng. Carry nhận item tốt nhất."""
    item_assignment = {}
    used_items = set()

    # Carry nhận 3 best items
    carry_items = []
    for item in best_items:
        if len(carry_items) < 3:
            carry_items.append(item)
            used_items.add(item)
    item_assignment[carry] = carry_items

    # Các tướng còn lại nhận 0-2 item ngẫu nhiên
    available = [i for i in all_items if i not in used_items]
    for champ in champions:
        if champ == carry:
            continue
        n_items = random.choices([0, 1, 2], weights=[0.3, 0.4, 0.3])[0]
        if n_items > 0 and available:
            chosen = random.sample(available, min(n_items, len(available)))
            item_assignment[champ] = chosen
            for c in chosen:
                if random.random() < 0.3:  # Items can be shared
                    available.remove(c)
        else:
            item_assignment[champ] = []

    return item_assignment


def generate_player(match_id, player_idx, meta_comps, all_champs, all_items):
    """Tạo dữ liệu 1 người chơi trong 1 trận."""
    # Chọn comp
    comp_names = list(meta_comps.keys()) + ["random"]
    comp_probs = [meta_comps[c]["popularity"] for c in meta_comps] + [RANDOM_COMP_PROB]
    chosen_comp = random.choices(comp_names, weights=comp_probs)[0]

    if chosen_comp != "random":
        comp = meta_comps[chosen_comp]
        # Lấy core + 1 vài flex
        core = list(comp["core"])
        n_flex = random.randint(2, min(4, len(comp["flex"])))
        flex = random.sample(comp["flex"], n_flex)
        champions = core + flex
        # Giới hạn 6-9 tướng
        team_size = random.randint(6, 9)
        if len(champions) > team_size:
            champions = core + random.sample(flex, max(0, team_size - len(core)))
        elif len(champions) < team_size:
            # Thêm tướng ngẫu nhiên
            pool = [c for c in all_champs if c not in champions]
            extra = random.sample(pool, min(team_size - len(champions), len(pool)))
            champions.extend(extra)

        carry = comp["carry"]
        best_items = comp["best_items"]
        base_placement = comp["base_placement"]
    else:
        # Random comp
        team_size = random.randint(6, 9)
        champions = random.sample(list(all_champs.keys()), team_size)
        carry = random.choice(champions)
        best_items = random.sample(all_items, 3)
        base_placement = 4.5  # Random comp has worse avg

    # Gán star level
    champion_stars = {}
    for champ in champions:
        cost = all_champs.get(champ, {}).get("cost", 1)
        if cost <= 2:
            star = random.choices([1, 2, 3], weights=[0.2, 0.5, 0.3])[0]
        elif cost <= 3:
            star = random.choices([1, 2, 3], weights=[0.3, 0.5, 0.2])[0]
        elif cost <= 4:
            star = random.choices([1, 2], weights=[0.6, 0.4])[0]
        else:
            star = random.choices([1, 2], weights=[0.8, 0.2])[0]
        champion_stars[champ] = star

    # Gán items
    items = _assign_items(champions, carry, best_items, all_items)

    # Tính traits
    active_traits = _get_active_traits(champions)

    # Level
    level = random.choices([7, 8, 9], weights=[0.2, 0.5, 0.3])[0]

    # Item quality bonus (carry có 3 BiS item → placement tốt hơn)
    item_bonus = 0
    if chosen_comp != "random":
        carry_items_set = set(items.get(carry, []))
        bis_match = len(carry_items_set & set(comp["best_items"]))
        item_bonus = -0.3 * bis_match  # Better items → lower placement number

    # Star level bonus
    star_bonus = 0
    carry_star = champion_stars.get(carry, 1)
    if carry_star == 3:
        star_bonus = -0.8
    elif carry_star == 2:
        star_bonus = -0.3

    # Tính placement cuối cùng (có noise)
    raw_placement = base_placement + item_bonus + star_bonus + random.gauss(0, 1.2)

    return {
        "match_id": match_id,
        "player_id": f"player_{player_idx}_{random.randint(10000, 99999)}",
        "comp_type": chosen_comp,
        "champions": champions,
        "champion_stars": champion_stars,
        "items": items,
        "active_traits": active_traits,
        "level": level,
        "gold_left": max(0, random.randint(0, 50)),
        "total_damage": random.randint(5000, 80000),
        "_raw_placement": raw_placement,
    }


def generate_matches(n_matches=50000, seed=42):
    """Tạo n_matches trận đấu TFT, mỗi trận 8 người chơi."""
    random.seed(seed)
    np.random.seed(seed)

    all_records = []

    for match_idx in range(n_matches):
        match_id = f"VN2_{1000000 + match_idx}"

        # Tạo 8 người chơi
        players = []
        for p_idx in range(8):
            player = generate_player(match_id, p_idx, META_COMPS, CHAMPIONS, ITEMS)
            players.append(player)

        # Sắp xếp theo raw_placement để gán thứ hạng 1-8
        players.sort(key=lambda x: x["_raw_placement"])
        for rank, player in enumerate(players, 1):
            player["placement"] = rank
            player["rounds_survived"] = max(10, min(38, int(38 - (rank - 1) * 3 + random.gauss(0, 2))))
            del player["_raw_placement"]
            all_records.append(player)

        if (match_idx + 1) % 10000 == 0:
            print(f"  Đã tạo {match_idx + 1}/{n_matches} trận...")

    return all_records


def records_to_csv(records, filepath):
    """Chuyển records sang CSV (flatten)."""
    rows = []
    for r in records:
        row = {
            "match_id": r["match_id"],
            "player_id": r["player_id"],
            "placement": r["placement"],
            "comp_type": r["comp_type"],
            "level": r["level"],
            "gold_left": r["gold_left"],
            "total_damage": r["total_damage"],
            "rounds_survived": r["rounds_survived"],
            "champions": "|".join(r["champions"]),
            "champion_stars": json.dumps(r["champion_stars"]),
            "items": json.dumps(r["items"]),
            "active_traits": json.dumps(r["active_traits"]),
            "num_champions": len(r["champions"]),
            "num_items": sum(len(v) for v in r["items"].values()),
            "num_active_traits": len(r["active_traits"]),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    return df


def records_to_json(records, filepath):
    """Lưu records dạng JSON."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def print_summary(df):
    """In thống kê tổng hợp."""
    print("\n" + "=" * 60)
    print("📊 THỐNG KÊ DỮ LIỆU TFT MATCH DATA")
    print("=" * 60)
    print(f"Tổng số records (player-games): {len(df):,}")
    print(f"Tổng số trận đấu: {df['match_id'].nunique():,}")
    print(f"Placement phân phối:\n{df['placement'].value_counts().sort_index()}")
    print(f"\nSố tướng trung bình/đội: {df['num_champions'].mean():.1f}")
    print(f"Số item trung bình/đội: {df['num_items'].mean():.1f}")
    print(f"\nComp types phân phối:")
    print(df["comp_type"].value_counts())
    print(f"\nWin-rate theo comp type (Top 4):")
    df["is_win"] = df["placement"] <= 4
    wr = df.groupby("comp_type")["is_win"].mean().sort_values(ascending=False)
    for comp, rate in wr.items():
        tag = " 🔥 HIDDEN META" if "hidden" in str(comp) else ""
        print(f"  {comp}: {rate:.1%}{tag}")
    print("=" * 60)


if __name__ == "__main__":
    print("🎮 TFT Match Data Generator")
    print("Đang tạo 50,000 trận đấu...")

    raw_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw")
    os.makedirs(raw_dir, exist_ok=True)

    records = generate_matches(n_matches=50000, seed=42)

    csv_path = os.path.join(raw_dir, "tft_matches.csv")
    json_path = os.path.join(raw_dir, "tft_matches.json")

    print("💾 Lưu CSV...")
    df = records_to_csv(records, csv_path)
    print(f"  → {csv_path} ({os.path.getsize(csv_path) / 1024 / 1024:.1f} MB)")

    print("💾 Lưu JSON...")
    records_to_json(records, json_path)
    print(f"  → {json_path} ({os.path.getsize(json_path) / 1024 / 1024:.1f} MB)")

    print_summary(df)
    print("\n✅ Hoàn tất!")
