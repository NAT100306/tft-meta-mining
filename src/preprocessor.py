"""
preprocessor.py - Module tiền xử lý dữ liệu TFT cho khai phá luật kết hợp & đồ thị
"""

import json
import ast
import pandas as pd
import numpy as np
from collections import Counter
from itertools import combinations
from mlxtend.preprocessing import TransactionEncoder


class TFTPreprocessor:
    """Lớp tiền xử lý dữ liệu TFT Match Data."""

    def __init__(self):
        self.stats = {}

    # ─────────────── LOAD ───────────────
    def load_data(self, filepath: str) -> pd.DataFrame:
        """Nạp dữ liệu từ CSV hoặc JSON."""
        if filepath.endswith(".csv"):
            df = pd.read_csv(filepath)
        elif filepath.endswith(".json"):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            df = pd.DataFrame(data)
        else:
            raise ValueError(f"Unsupported format: {filepath}")
        print(f"✅ Loaded {len(df):,} records from {filepath}")
        return df

    # ─────────────── CLEAN ───────────────
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Làm sạch dữ liệu: loại bỏ thiếu, trùng, ngoại lệ."""
        original_len = len(df)

        # Loại bỏ missing critical fields
        critical = ["match_id", "placement", "champions"]
        existing_critical = [c for c in critical if c in df.columns]
        df = df.dropna(subset=existing_critical)

        # Loại bỏ placement ngoài 1-8
        if "placement" in df.columns:
            df = df[df["placement"].between(1, 8)]

        # Loại bỏ duplicate
        df = df.drop_duplicates(subset=["match_id", "player_id"] if "player_id" in df.columns else None)

        removed = original_len - len(df)
        print(f"🧹 Cleaned: {removed:,} rows removed ({removed/original_len*100:.1f}%)")
        print(f"   Remaining: {len(df):,} records")
        return df.reset_index(drop=True)

    # ─────────────── LABEL ───────────────
    def label_win_lose(self, df: pd.DataFrame, threshold: int = 4) -> pd.DataFrame:
        """Gán nhãn Win/Lose dựa trên placement."""
        df = df.copy()
        df["result"] = df["placement"].apply(lambda x: "Win" if x <= threshold else "Lose")
        win_count = (df["result"] == "Win").sum()
        lose_count = (df["result"] == "Lose").sum()
        print(f"🏷️  Labels (Top {threshold}): Win={win_count:,} ({win_count/len(df)*100:.0f}%) | Lose={lose_count:,} ({lose_count/len(df)*100:.0f}%)")
        return df

    # ─────────────── PARSE HELPERS ───────────────
    @staticmethod
    def _parse_list_field(val):
        """Parse một trường list từ string."""
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            if "|" in val:
                return val.split("|")
            try:
                return ast.literal_eval(val)
            except (ValueError, SyntaxError):
                return val.split(",")
        return []

    @staticmethod
    def _parse_dict_field(val):
        """Parse một trường dict từ string."""
        if isinstance(val, dict):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                try:
                    return ast.literal_eval(val)
                except (ValueError, SyntaxError):
                    return {}
        return {}

    # ─────────────── TRANSACTIONS ───────────────
    def create_transactions(self, df: pd.DataFrame,
                            include_items: bool = True,
                            include_traits: bool = True) -> dict:
        """
        Chuyển mỗi player-game thành 1 transaction (set of strings).
        Returns dict: {'win': [frozenset, ...], 'lose': [frozenset, ...], 'all': [...]}
        Tối ưu: pre-parse toàn bộ cột trước, sau đó duyệt bằng zip (nhanh gấp 10-50x so với iterrows).
        """
        # Pre-parse tất cả cột 1 lần duy nhất (vectorized)
        champ_series = df["champions"].apply(self._parse_list_field) if "champions" in df.columns else pd.Series([[] for _ in range(len(df))])
        item_series = df["items"].apply(self._parse_dict_field) if (include_items and "items" in df.columns) else None
        trait_series = df["active_traits"].apply(self._parse_dict_field) if (include_traits and "active_traits" in df.columns) else None
        result_series = df["result"].values if "result" in df.columns else [""] * len(df)

        transactions = {"win": [], "lose": [], "all": []}

        for i in range(len(df)):
            items_in_txn = set()

            # Champions
            for c in champ_series.iloc[i]:
                items_in_txn.add(f"Champ_{c}")

            # Items
            if item_series is not None:
                for champ, item_list in item_series.iloc[i].items():
                    if isinstance(item_list, list):
                        for item in item_list:
                            items_in_txn.add(f"Item_{item}")

            # Traits
            if trait_series is not None:
                for trait, tier in trait_series.iloc[i].items():
                    items_in_txn.add(f"Trait_{trait}_{tier}")

            txn = frozenset(items_in_txn)
            transactions["all"].append(txn)

            result = result_series[i]
            if result == "Win":
                transactions["win"].append(txn)
            elif result == "Lose":
                transactions["lose"].append(txn)

        print(f"📦 Transactions: All={len(transactions['all']):,} | Win={len(transactions['win']):,} | Lose={len(transactions['lose']):,}")
        return transactions

    # ─────────────── BINARY MATRIX ───────────────
    def create_binary_matrix(self, transactions: list) -> pd.DataFrame:
        """Chuyển list of frozensets sang ma trận nhị phân one-hot (cho mlxtend)."""
        list_of_lists = [list(t) for t in transactions]
        te = TransactionEncoder()
        te_ary = te.fit(list_of_lists).transform(list_of_lists)
        df_binary = pd.DataFrame(te_ary, columns=te.columns_)
        print(f"📐 Binary matrix shape: {df_binary.shape}")
        return df_binary

    # ─────────────── CO-OCCURRENCE ───────────────
    def build_cooccurrence_matrix(self, df: pd.DataFrame,
                                   entity: str = "champions",
                                   weight: str = "winrate") -> pd.DataFrame:
        """
        Xây dựng ma trận đồng xuất hiện.
        entity: 'champions' hoặc 'items'
        weight: 'frequency', 'winrate', 'lift'
        Tối ưu: pre-parse toàn bộ cột trước rồi duyệt.
        """
        # Pre-parse cột entity 1 lần
        if entity == "champions":
            entity_series = df["champions"].apply(self._parse_list_field) if "champions" in df.columns else pd.Series([[] for _ in range(len(df))])
        else:
            def _extract_items(val):
                d = self._parse_dict_field(val)
                items = set()
                for item_list in d.values():
                    if isinstance(item_list, list):
                        items.update(item_list)
                return list(items)
            entity_series = df["items"].apply(_extract_items) if "items" in df.columns else pd.Series([[] for _ in range(len(df))])

        result_arr = df["result"].values if "result" in df.columns else [""] * len(df)

        # Thu thập tất cả entities
        all_entities = set()
        records = []
        for i in range(len(df)):
            entities = entity_series.iloc[i]
            is_win = result_arr[i] == "Win"
            all_entities.update(entities)
            records.append((entities, is_win))

        # Tạo ma trận
        entity_list = sorted(all_entities)
        n = len(entity_list)
        idx = {e: i for i, e in enumerate(entity_list)}
        cooccur = np.zeros((n, n))
        win_cooccur = np.zeros((n, n))
        entity_freq = np.zeros(n)
        total = len(records)

        for entities, is_win in records:
            for e in entities:
                if e in idx:
                    entity_freq[idx[e]] += 1
            for e1, e2 in combinations(entities, 2):
                if e1 in idx and e2 in idx:
                    i, j = idx[e1], idx[e2]
                    cooccur[i][j] += 1
                    cooccur[j][i] += 1
                    if is_win:
                        win_cooccur[i][j] += 1
                        win_cooccur[j][i] += 1

        if weight == "frequency":
            matrix = cooccur / max(total, 1)
        elif weight == "winrate":
            with np.errstate(divide="ignore", invalid="ignore"):
                matrix = np.where(cooccur > 0, win_cooccur / cooccur, 0)
        elif weight == "lift":
            with np.errstate(divide="ignore", invalid="ignore"):
                expected = np.outer(entity_freq, entity_freq) / (total ** 2)
                observed = cooccur / total
                matrix = np.where(expected > 0, observed / expected, 0)
        else:
            matrix = cooccur

        result = pd.DataFrame(matrix, index=entity_list, columns=entity_list)
        print(f"📊 Co-occurrence matrix ({weight}): {result.shape}")
        return result

    # ─────────────── STATISTICS ───────────────
    def get_statistics(self, df: pd.DataFrame) -> dict:
        """Tính thống kê mô tả toàn diện."""
        stats = {
            "total_records": len(df),
            "total_matches": df["match_id"].nunique() if "match_id" in df.columns else None,
        }

        # Champion frequency
        all_champs = []
        for val in df.get("champions", []):
            champs = self._parse_list_field(val)
            all_champs.extend(champs)
        stats["champion_frequency"] = dict(Counter(all_champs).most_common(50))
        stats["unique_champions"] = len(set(all_champs))

        # Item frequency
        all_items_list = []
        for val in df.get("items", []):
            item_dict = self._parse_dict_field(val)
            for item_list in item_dict.values():
                if isinstance(item_list, list):
                    all_items_list.extend(item_list)
        stats["item_frequency"] = dict(Counter(all_items_list).most_common(30))
        stats["unique_items"] = len(set(all_items_list))

        # Placement distribution
        if "placement" in df.columns:
            stats["placement_distribution"] = df["placement"].value_counts().sort_index().to_dict()

        # Win rate
        if "result" in df.columns:
            stats["win_rate"] = (df["result"] == "Win").mean()

        self.stats = stats
        return stats

    # ─────────────── FILTER ───────────────
    def filter_by_placement(self, df: pd.DataFrame, min_place: int = None,
                             max_place: int = None) -> pd.DataFrame:
        """Lọc theo placement range."""
        if min_place is not None:
            df = df[df["placement"] >= min_place]
        if max_place is not None:
            df = df[df["placement"] <= max_place]
        return df


if __name__ == "__main__":
    import os
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw", "tft_matches.csv")
    if os.path.exists(data_path):
        pp = TFTPreprocessor()
        df = pp.load_data(data_path)
        df = pp.clean_data(df)
        df = pp.label_win_lose(df, threshold=4)
        stats = pp.get_statistics(df)
        print(f"\nUnique champions: {stats['unique_champions']}")
        print(f"Unique items: {stats['unique_items']}")
        txns = pp.create_transactions(df)
        bin_win = pp.create_binary_matrix(txns["win"])
        cooc = pp.build_cooccurrence_matrix(df, entity="champions", weight="winrate")
        print("\n✅ Preprocessor demo complete!")
    else:
        print(f"⚠️ Data file not found: {data_path}")
        print("  Run data_generator.py first!")
