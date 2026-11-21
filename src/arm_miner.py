"""
arm_miner.py - Association Rule Mining module for TFT meta-game analysis.

This module provides the AssociationRuleMiner class which leverages both Apriori
and FP-Growth algorithms to discover meaningful champion/item/trait synergies
from Teamfight Tactics match data.  It also includes contrast-set mining to
isolate "meta-defining" rules and utilities for finding hidden OP compositions.
"""

from __future__ import annotations

import time
import tracemalloc
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import apriori, fpgrowth, association_rules


class AssociationRuleMiner:
    """Mine association rules from binary (one-hot) TFT match data.

    Parameters
    ----------
    min_support : float
        Minimum support threshold for frequent-itemset mining (default 0.02).
    min_confidence : float
        Minimum confidence threshold for rule generation (default 0.5).
    min_lift : float
        Minimum lift threshold for rule generation (default 1.0).
    """

    def __init__(
        self,
        min_support: float = 0.03,
        min_confidence: float = 0.5,
        min_lift: float = 1.0,
        max_len: Optional[int] = 4,
    ) -> None:
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.min_lift = min_lift
        self.max_len = max_len

    # ------------------------------------------------------------------
    # Core mining helpers
    # ------------------------------------------------------------------

    def _mine(
        self,
        algorithm_fn,
        algorithm_name: str,
        binary_df: pd.DataFrame,
        win_label: bool = True,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
        """Internal helper that runs a frequent-itemset algorithm, generates
        rules, and records timing / memory information.

        Parameters
        ----------
        algorithm_fn : callable
            Either ``apriori`` or ``fpgrowth`` from *mlxtend*.
        algorithm_name : str
            Human-readable name of the algorithm (for the timing dict).
        binary_df : pd.DataFrame
            One-hot encoded transaction DataFrame.
        win_label : bool
            If ``True`` the data is assumed to represent *winning* matches.

        Returns
        -------
        frequent_itemsets : pd.DataFrame
        rules : pd.DataFrame
        timing_info : dict
        """
        # --- Start profiling ---
        tracemalloc.start()
        start_time = time.perf_counter()

        # --- Frequent itemsets ---
        frequent_itemsets: pd.DataFrame = algorithm_fn(
            binary_df,
            min_support=self.min_support,
            use_colnames=True,
            max_len=self.max_len,
        )

        # --- Association rules ---
        if frequent_itemsets.empty:
            rules = pd.DataFrame()
        else:
            rules = association_rules(
                frequent_itemsets,
                metric="confidence",
                min_threshold=self.min_confidence,
            )
            # Apply lift filter
            if not rules.empty:
                rules = rules[rules["lift"] >= self.min_lift].copy()

        # --- Stop profiling ---
        elapsed = time.perf_counter() - start_time
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        timing_info: Dict = {
            "algorithm": algorithm_name,
            "win_label": win_label,
            "execution_time_s": round(elapsed, 4),
            "current_memory_bytes": current_mem,
            "peak_memory_bytes": peak_mem,
            "current_memory_mb": round(current_mem / (1024 * 1024), 2),
            "peak_memory_mb": round(peak_mem / (1024 * 1024), 2),
            "num_frequent_itemsets": len(frequent_itemsets),
            "num_rules": len(rules),
        }

        return frequent_itemsets, rules, timing_info

    # ------------------------------------------------------------------
    # Public API - algorithm runners
    # ------------------------------------------------------------------

    def run_apriori(
        self,
        binary_df: pd.DataFrame,
        win_label: bool = True,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
        """Run the *Apriori* algorithm on ``binary_df``.

        Parameters
        ----------
        binary_df : pd.DataFrame
            One-hot encoded transaction DataFrame (columns = items,
            rows = transactions, values ∈ {0, 1} or {True, False}).
        win_label : bool
            Whether the data represents winning matches.

        Returns
        -------
        frequent_itemsets : pd.DataFrame
            Frequent itemsets with their support values.
        rules : pd.DataFrame
            Association rules with support, confidence, lift, etc.
        timing_info : dict
            Execution time, memory usage, and counts.
        """
        return self._mine(apriori, "Apriori", binary_df, win_label)

    def run_fpgrowth(
        self,
        binary_df: pd.DataFrame,
        win_label: bool = True,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
        """Run the *FP-Growth* algorithm on ``binary_df``.

        Parameters
        ----------
        binary_df : pd.DataFrame
            One-hot encoded transaction DataFrame.
        win_label : bool
            Whether the data represents winning matches.

        Returns
        -------
        frequent_itemsets : pd.DataFrame
        rules : pd.DataFrame
        timing_info : dict
        """
        return self._mine(fpgrowth, "FP-Growth", binary_df, win_label)

    # ------------------------------------------------------------------
    # Algorithm comparison
    # ------------------------------------------------------------------

    def compare_algorithms(self, binary_df: pd.DataFrame) -> pd.DataFrame:
        """Run both Apriori and FP-Growth on the same data and compare.

        Parameters
        ----------
        binary_df : pd.DataFrame
            One-hot encoded transaction DataFrame.

        Returns
        -------
        comparison : pd.DataFrame
            Side-by-side comparison of execution time, memory usage,
            and the number of rules discovered by each algorithm.
        """
        _, _, apriori_info = self.run_apriori(binary_df)
        _, _, fpgrowth_info = self.run_fpgrowth(binary_df)

        comparison = pd.DataFrame(
            {
                "Metric": [
                    "Execution Time (s)",
                    "Peak Memory (MB)",
                    "Frequent Itemsets",
                    "Association Rules",
                ],
                "Apriori": [
                    apriori_info["execution_time_s"],
                    apriori_info["peak_memory_mb"],
                    apriori_info["num_frequent_itemsets"],
                    apriori_info["num_rules"],
                ],
                "FP-Growth": [
                    fpgrowth_info["execution_time_s"],
                    fpgrowth_info["peak_memory_mb"],
                    fpgrowth_info["num_frequent_itemsets"],
                    fpgrowth_info["num_rules"],
                ],
            }
        )
        comparison["Difference"] = comparison["FP-Growth"] - comparison["Apriori"]
        return comparison

    # ------------------------------------------------------------------
    # Contrast-set mining
    # ------------------------------------------------------------------

    def contrast_set_mining(
        self,
        win_transactions_df: pd.DataFrame,
        lose_transactions_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Identify *meta-defining* rules that appear (or are significantly
        stronger) in the **Win** set compared to the **Lose** set.

        Parameters
        ----------
        win_transactions_df : pd.DataFrame
            One-hot encoded transactions for winning matches.
        lose_transactions_df : pd.DataFrame
            One-hot encoded transactions for losing matches.

        Returns
        -------
        contrast_rules : pd.DataFrame
            Rules enriched with ``win_support``, ``win_confidence``,
            ``lose_support``, ``lose_confidence``, and their deltas.
            Only rules whose support or confidence is *higher* in the
            win set are returned, sorted by ``confidence_diff`` descending.
        """
        _, win_rules, _ = self.run_fpgrowth(win_transactions_df, win_label=True)
        _, lose_rules, _ = self.run_fpgrowth(lose_transactions_df, win_label=False)

        if win_rules.empty:
            return pd.DataFrame()

        # Build a lookup from (antecedents, consequents) -> metrics for loses
        lose_lookup: Dict[Tuple, Dict] = {}
        if not lose_rules.empty:
            for _, row in lose_rules.iterrows():
                key = (frozenset(row["antecedents"]), frozenset(row["consequents"]))
                lose_lookup[key] = {
                    "lose_support": row["support"],
                    "lose_confidence": row["confidence"],
                    "lose_lift": row["lift"],
                }

        contrast_rows: List[Dict] = []
        for _, row in win_rules.iterrows():
            key = (frozenset(row["antecedents"]), frozenset(row["consequents"]))
            lose_metrics = lose_lookup.get(
                key, {"lose_support": 0.0, "lose_confidence": 0.0, "lose_lift": 0.0}
            )

            support_diff = row["support"] - lose_metrics["lose_support"]
            confidence_diff = row["confidence"] - lose_metrics["lose_confidence"]
            lift_diff = row["lift"] - lose_metrics["lose_lift"]

            # Keep rule if it is stronger in the win set
            if support_diff > 0 or confidence_diff > 0:
                contrast_rows.append(
                    {
                        "antecedents": row["antecedents"],
                        "consequents": row["consequents"],
                        "win_support": row["support"],
                        "win_confidence": row["confidence"],
                        "win_lift": row["lift"],
                        "lose_support": lose_metrics["lose_support"],
                        "lose_confidence": lose_metrics["lose_confidence"],
                        "lose_lift": lose_metrics["lose_lift"],
                        "support_diff": round(support_diff, 4),
                        "confidence_diff": round(confidence_diff, 4),
                        "lift_diff": round(lift_diff, 4),
                    }
                )

        if not contrast_rows:
            return pd.DataFrame()

        contrast_df = pd.DataFrame(contrast_rows)
        contrast_df.sort_values("confidence_diff", ascending=False, inplace=True)
        contrast_df.reset_index(drop=True, inplace=True)
        return contrast_df

    # ------------------------------------------------------------------
    # Filtering utilities
    # ------------------------------------------------------------------

    def filter_high_lift_rules(
        self,
        rules: pd.DataFrame,
        min_lift: float = 1.5,
    ) -> pd.DataFrame:
        """Return rules whose *lift* exceeds ``min_lift``, sorted descending.

        High-lift rules represent **true synergies** — item/champion
        combinations that co-occur much more frequently than chance.

        Parameters
        ----------
        rules : pd.DataFrame
            Association rules DataFrame (must contain a ``lift`` column).
        min_lift : float
            Minimum lift threshold (default 1.5).

        Returns
        -------
        pd.DataFrame
            Filtered and sorted rules.
        """
        if rules.empty:
            return rules
        high_lift = rules[rules["lift"] > min_lift].copy()
        high_lift.sort_values("lift", ascending=False, inplace=True)
        high_lift.reset_index(drop=True, inplace=True)
        return high_lift

    def find_hidden_meta(
        self,
        rules: pd.DataFrame,
        max_support: float = 0.05,
        min_lift: float = 1.5,
        min_confidence: float = 0.6,
    ) -> pd.DataFrame:
        """Discover *hidden OP* compositions — rules with **low support** but
        **high lift and confidence**.

        These represent compositions that few players use but that
        achieve disproportionately high win rates when they do appear.

        Parameters
        ----------
        rules : pd.DataFrame
            Association rules DataFrame.
        max_support : float
            Maximum support (rarity threshold, default 0.05).
        min_lift : float
            Minimum lift (synergy threshold, default 1.5).
        min_confidence : float
            Minimum confidence (reliability threshold, default 0.6).

        Returns
        -------
        pd.DataFrame
            Hidden-meta rules sorted by lift descending.
        """
        if rules.empty:
            return rules

        mask = (
            (rules["support"] <= max_support)
            & (rules["lift"] >= min_lift)
            & (rules["confidence"] >= min_confidence)
        )
        hidden = rules[mask].copy()
        hidden.sort_values("lift", ascending=False, inplace=True)
        hidden.reset_index(drop=True, inplace=True)
        return hidden

    # ------------------------------------------------------------------
    # Output / visualisation
    # ------------------------------------------------------------------

    def format_rules(self, rules: pd.DataFrame, top_n: int = 20) -> str:
        """Pretty-print the top rules in a human-readable format.

        Parameters
        ----------
        rules : pd.DataFrame
            Association rules DataFrame.
        top_n : int
            Number of rules to display (default 20).

        Returns
        -------
        str
            Formatted string ready for printing.
        """
        if rules.empty:
            return "No rules to display."

        display_rules = rules.head(top_n)
        lines: List[str] = []
        lines.append("=" * 80)
        lines.append(f"{'ASSOCIATION RULES':^80}")
        lines.append("=" * 80)
        lines.append(
            f"{'#':<4} {'Antecedent -> Consequent':<50} "
            f"{'Supp':>6} {'Conf':>6} {'Lift':>6}"
        )
        lines.append("-" * 80)

        for idx, (_, row) in enumerate(display_rules.iterrows(), start=1):
            ant = ", ".join(sorted(row["antecedents"]))
            con = ", ".join(sorted(row["consequents"]))
            rule_str = f"{ant} -> {con}"
            if len(rule_str) > 48:
                rule_str = rule_str[:45] + "..."
            lines.append(
                f"{idx:<4} {rule_str:<50} "
                f"{row['support']:>6.3f} {row['confidence']:>6.3f} {row['lift']:>6.2f}"
            )

        lines.append("=" * 80)
        lines.append(f"Showing top {min(top_n, len(rules))} of {len(rules)} rules")
        formatted = "\n".join(lines)
        return formatted

    def plot_rules(
        self,
        rules: pd.DataFrame,
        top_n: int = 30,
    ) -> Tuple[plt.Figure, plt.Figure]:
        """Visualise association rules.

        Creates two figures:

        1. **Scatter plot** — Support vs Confidence, coloured by Lift.
        2. **Bar chart** — Top *top_n* rules ranked by Lift.

        Parameters
        ----------
        rules : pd.DataFrame
            Association rules DataFrame.
        top_n : int
            Number of rules to show in the bar chart (default 30).

        Returns
        -------
        fig_scatter : matplotlib.figure.Figure
        fig_bar : matplotlib.figure.Figure
        """
        # --- Scatter plot: Support vs Confidence (coloured by Lift) ---
        fig_scatter, ax1 = plt.subplots(figsize=(10, 6))
        scatter = ax1.scatter(
            rules["support"],
            rules["confidence"],
            c=rules["lift"],
            cmap="YlOrRd",
            alpha=0.7,
            edgecolors="grey",
            linewidths=0.5,
            s=50,
        )
        cbar = plt.colorbar(scatter, ax=ax1)
        cbar.set_label("Lift", fontsize=12)
        ax1.set_xlabel("Support", fontsize=12)
        ax1.set_ylabel("Confidence", fontsize=12)
        ax1.set_title("Association Rules — Support vs Confidence (colour = Lift)", fontsize=14)
        ax1.grid(True, alpha=0.3)
        fig_scatter.tight_layout()

        # --- Bar chart: Top rules by Lift ---
        top_rules = rules.nlargest(top_n, "lift").copy()
        top_rules["rule_label"] = top_rules.apply(
            lambda r: (
                ", ".join(sorted(r["antecedents"]))
                + " → "
                + ", ".join(sorted(r["consequents"]))
            ),
            axis=1,
        )
        # Truncate long labels
        top_rules["rule_label"] = top_rules["rule_label"].apply(
            lambda s: s if len(s) <= 50 else s[:47] + "..."
        )

        fig_bar, ax2 = plt.subplots(figsize=(12, max(6, top_n * 0.35)))
        y_pos = np.arange(len(top_rules))
        colours = plt.cm.YlOrRd(
            np.linspace(0.3, 0.9, len(top_rules))  # type: ignore[arg-type]
        )
        ax2.barh(y_pos, top_rules["lift"].values, color=colours, edgecolor="grey")
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(top_rules["rule_label"].values, fontsize=9)
        ax2.invert_yaxis()
        ax2.set_xlabel("Lift", fontsize=12)
        ax2.set_title(f"Top {len(top_rules)} Association Rules by Lift", fontsize=14)
        ax2.grid(True, axis="x", alpha=0.3)
        fig_bar.tight_layout()

        return fig_scatter, fig_bar


# ======================================================================
# Example usage
# ======================================================================

if __name__ == "__main__":
    # --- Build a small synthetic TFT-like dataset ---
    np.random.seed(42)
    n_matches = 500
    champions = [
        "Jinx", "Vi", "Ekko", "Jayce", "Caitlyn",
        "Ahri", "Lux", "Zed", "Shen", "Kayn",
    ]

    data: Dict[str, List[int]] = {champ: [] for champ in champions}
    data["Win"] = []

    for _ in range(n_matches):
        team_size = np.random.randint(3, 7)
        team = np.random.choice(champions, size=team_size, replace=False)
        for champ in champions:
            data[champ].append(int(champ in team))

        # Simulate a synergy: Jinx + Vi → higher win rate
        if "Jinx" in team and "Vi" in team:
            data["Win"].append(int(np.random.random() < 0.75))
        else:
            data["Win"].append(int(np.random.random() < 0.45))

    df = pd.DataFrame(data)
    binary_df = df.drop(columns=["Win"]).astype(bool)

    win_df = binary_df[df["Win"] == 1].reset_index(drop=True)
    lose_df = binary_df[df["Win"] == 0].reset_index(drop=True)

    # --- Instantiate the miner ---
    miner = AssociationRuleMiner(min_support=0.02, min_confidence=0.3, min_lift=1.0)

    # 1. Run Apriori
    print("\n>>> Running Apriori …")
    freq_ap, rules_ap, info_ap = miner.run_apriori(win_df)
    print(f"    Itemsets: {info_ap['num_frequent_itemsets']}, "
          f"Rules: {info_ap['num_rules']}, "
          f"Time: {info_ap['execution_time_s']}s, "
          f"Peak mem: {info_ap['peak_memory_mb']} MB")

    # 2. Run FP-Growth
    print("\n>>> Running FP-Growth …")
    freq_fp, rules_fp, info_fp = miner.run_fpgrowth(win_df)
    print(f"    Itemsets: {info_fp['num_frequent_itemsets']}, "
          f"Rules: {info_fp['num_rules']}, "
          f"Time: {info_fp['execution_time_s']}s, "
          f"Peak mem: {info_fp['peak_memory_mb']} MB")

    # 3. Compare algorithms
    print("\n>>> Algorithm comparison:")
    comparison = miner.compare_algorithms(win_df)
    print(comparison.to_string(index=False))

    # 4. Contrast-set mining (Win vs Lose)
    print("\n>>> Contrast-set mining (Win vs Lose) …")
    contrast = miner.contrast_set_mining(win_df, lose_df)
    if not contrast.empty:
        print(f"    Found {len(contrast)} contrast rules.")
        print(contrast.head(10).to_string(index=False))
    else:
        print("    No contrast rules found.")

    # 5. High-lift rules
    print("\n>>> High-lift synergies:")
    high_lift = miner.filter_high_lift_rules(rules_fp, min_lift=1.2)
    print(miner.format_rules(high_lift, top_n=10))

    # 6. Hidden meta
    print("\n>>> Hidden meta (low support, high lift & confidence):")
    hidden = miner.find_hidden_meta(rules_fp, max_support=0.10, min_lift=1.2, min_confidence=0.4)
    print(miner.format_rules(hidden, top_n=10))

    # 7. Plot rules (saved to files)
    if not rules_fp.empty:
        fig_scatter, fig_bar = miner.plot_rules(rules_fp, top_n=15)
        fig_scatter.savefig("rules_scatter.png", dpi=150)
        fig_bar.savefig("rules_bar.png", dpi=150)
        print("\n>>> Plots saved to rules_scatter.png and rules_bar.png")
        plt.close("all")

    print("\nDone.")
