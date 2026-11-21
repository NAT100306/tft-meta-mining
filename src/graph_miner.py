"""
graph_miner.py - Module khai phá đồ thị: Co-occurrence Network, Louvain, Leiden, PageRank
"""

import numpy as np
import pandas as pd
import networkx as nx
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import Counter

try:
    import community as community_louvain  # python-louvain
except ImportError:
    community_louvain = None

try:
    import igraph as ig
    import leidenalg
except ImportError:
    ig = None
    leidenalg = None

try:
    from pyvis.network import Network as PyvisNetwork
except ImportError:
    PyvisNetwork = None


class GraphMiner:
    """Lớp khai phá đồ thị cho phân tích TFT meta-game."""

    def __init__(self):
        self.G = None
        self.partition_louvain = None
        self.partition_leiden = None
        self.pagerank_scores = None

    # ═══════════════ BUILD NETWORK ═══════════════
    def build_network(self, cooccurrence_df: pd.DataFrame,
                      min_weight: float = 0.01) -> nx.Graph:
        """
        Xây dựng đồ thị từ ma trận đồng xuất hiện.
        Nodes = champions/items, Edges = co-occurrence với trọng số.
        """
        G = nx.Graph()
        entities = cooccurrence_df.index.tolist()
        G.add_nodes_from(entities)

        for i, e1 in enumerate(entities):
            for j, e2 in enumerate(entities):
                if i < j:
                    w = cooccurrence_df.iloc[i, j]
                    if w > min_weight:
                        G.add_edge(e1, e2, weight=float(w))

        # Loại node cô lập
        isolated = list(nx.isolates(G))
        G.remove_nodes_from(isolated)

        self.G = G
        print(f"📊 Network: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, density={nx.density(G):.4f}")
        if isolated:
            print(f"   Removed {len(isolated)} isolated nodes")
        return G

    # ═══════════════ PAGERANK ═══════════════
    def compute_pagerank(self, G: nx.Graph = None, alpha: float = 0.85) -> tuple:
        """
        Tính PageRank cho đồ thị.
        Returns: (pagerank_dict, sorted_ranking as list of (node, score))
        """
        G = G or self.G
        pr = nx.pagerank(G, alpha=alpha, weight="weight")
        ranking = sorted(pr.items(), key=lambda x: x[1], reverse=True)
        self.pagerank_scores = pr
        print(f"🏆 PageRank Top 5 (α={alpha}):")
        for node, score in ranking[:5]:
            print(f"   {node}: {score:.4f}")
        return pr, ranking

    # ═══════════════ CENTRALITY ═══════════════
    def compute_centrality_metrics(self, G: nx.Graph = None) -> pd.DataFrame:
        """Tính tất cả centrality metrics."""
        G = G or self.G
        metrics = {
            "degree": nx.degree_centrality(G),
            "betweenness": nx.betweenness_centrality(G, weight="weight"),
            "closeness": nx.closeness_centrality(G),
        }
        try:
            metrics["eigenvector"] = nx.eigenvector_centrality(G, weight="weight", max_iter=1000)
        except nx.PowerIterationFailedConvergence:
            metrics["eigenvector"] = {n: 0 for n in G.nodes()}

        if self.pagerank_scores:
            metrics["pagerank"] = self.pagerank_scores

        df = pd.DataFrame(metrics)
        df.index.name = "node"
        return df.sort_values("degree", ascending=False)

    # ═══════════════ LOUVAIN ═══════════════
    def detect_communities_louvain(self, G: nx.Graph = None,
                                    resolution: float = 1.0) -> tuple:
        """
        Phát hiện cộng đồng bằng thuật toán Louvain.
        Returns: (partition_dict, modularity, community_summary_df)
        """
        G = G or self.G
        if community_louvain is None:
            raise ImportError("pip install python-louvain")

        partition = community_louvain.best_partition(G, weight="weight", resolution=resolution)
        modularity = community_louvain.modularity(partition, G, weight="weight")

        # Summary
        comm_members = {}
        for node, comm_id in partition.items():
            comm_members.setdefault(comm_id, []).append(node)

        summary_rows = []
        for comm_id, members in sorted(comm_members.items()):
            summary_rows.append({
                "community": comm_id,
                "size": len(members),
                "members": ", ".join(sorted(members)[:10]) + ("..." if len(members) > 10 else ""),
            })
        summary = pd.DataFrame(summary_rows)

        self.partition_louvain = partition
        print(f"🔵 Louvain (res={resolution}): {len(comm_members)} communities, modularity={modularity:.4f}")
        return partition, modularity, summary

    # ═══════════════ LEIDEN ═══════════════
    def detect_communities_leiden(self, G: nx.Graph = None,
                                   resolution: float = 1.0) -> tuple:
        """
        Phát hiện cộng đồng bằng thuật toán Leiden (cải tiến Louvain).
        Returns: (partition_dict, modularity, community_summary_df)
        """
        G = G or self.G
        if ig is None or leidenalg is None:
            print("⚠️ leidenalg/igraph not installed. Falling back to Louvain.")
            return self.detect_communities_louvain(G, resolution)

        # Convert networkx → igraph
        mapping = {node: i for i, node in enumerate(G.nodes())}
        reverse_mapping = {i: node for node, i in mapping.items()}
        edges = [(mapping[u], mapping[v]) for u, v in G.edges()]
        weights = [G[u][v].get("weight", 1.0) for u, v in G.edges()]

        ig_graph = ig.Graph(n=len(mapping), edges=edges, directed=False)
        ig_graph.es["weight"] = weights

        # Run Leiden
        partition_obj = leidenalg.find_partition(
            ig_graph,
            leidenalg.RBConfigurationVertexPartition,
            weights="weight",
            resolution_parameter=resolution,
        )

        # Convert back
        partition = {}
        for comm_id, members in enumerate(partition_obj):
            for member_idx in members:
                partition[reverse_mapping[member_idx]] = comm_id

        modularity = partition_obj.modularity

        # Summary
        comm_members = {}
        for node, comm_id in partition.items():
            comm_members.setdefault(comm_id, []).append(node)

        summary_rows = []
        for comm_id, members in sorted(comm_members.items()):
            summary_rows.append({
                "community": comm_id,
                "size": len(members),
                "members": ", ".join(sorted(members)[:10]) + ("..." if len(members) > 10 else ""),
            })
        summary = pd.DataFrame(summary_rows)

        self.partition_leiden = partition
        print(f"🟠 Leiden (res={resolution}): {len(comm_members)} communities, modularity={modularity:.4f}")
        return partition, modularity, summary

    # ═══════════════ COMPARE ═══════════════
    def compare_community_methods(self, G: nx.Graph = None) -> pd.DataFrame:
        """So sánh Louvain vs Leiden."""
        G = G or self.G
        results = []

        import time

        # Louvain
        t0 = time.time()
        part_l, mod_l, _ = self.detect_communities_louvain(G)
        time_l = time.time() - t0
        n_comm_l = len(set(part_l.values()))
        sizes_l = Counter(part_l.values())

        results.append({
            "method": "Louvain",
            "num_communities": n_comm_l,
            "modularity": round(mod_l, 4),
            "largest_community": max(sizes_l.values()),
            "smallest_community": min(sizes_l.values()),
            "execution_time_s": round(time_l, 4),
        })

        # Leiden
        t0 = time.time()
        part_d, mod_d, _ = self.detect_communities_leiden(G)
        time_d = time.time() - t0
        n_comm_d = len(set(part_d.values()))
        sizes_d = Counter(part_d.values())

        results.append({
            "method": "Leiden",
            "num_communities": n_comm_d,
            "modularity": round(mod_d, 4),
            "largest_community": max(sizes_d.values()),
            "smallest_community": min(sizes_d.values()),
            "execution_time_s": round(time_d, 4),
        })

        return pd.DataFrame(results)

    # ═══════════════ META ARCHETYPES ═══════════════
    def identify_meta_archetypes(self, G: nx.Graph, partition: dict,
                                  champion_data: dict = None) -> pd.DataFrame:
        """
        Xác định Meta Archetypes từ communities.
        champion_data: dict {name: {"traits": [...], "cost": int}}
        """
        G = G or self.G
        pr = self.pagerank_scores or dict(nx.pagerank(G, weight="weight"))

        comm_members = {}
        for node, comm_id in partition.items():
            comm_members.setdefault(comm_id, []).append(node)

        rows = []
        for comm_id, members in sorted(comm_members.items()):
            # Core champion = highest PageRank in community
            member_pr = {m: pr.get(m, 0) for m in members}
            core = max(member_pr, key=member_pr.get)

            # Dominant traits
            if champion_data:
                all_traits = []
                for m in members:
                    if m in champion_data:
                        all_traits.extend(champion_data[m].get("traits", []))
                trait_counter = Counter(all_traits)
                dominant_traits = [t for t, _ in trait_counter.most_common(3)]
            else:
                dominant_traits = []

            archetype_name = " + ".join(dominant_traits[:2]) if dominant_traits else f"Cluster_{comm_id}"

            rows.append({
                "community": comm_id,
                "archetype": archetype_name,
                "size": len(members),
                "core_champion": core,
                "core_pagerank": round(pr.get(core, 0), 4),
                "members": ", ".join(sorted(members)),
            })

        return pd.DataFrame(rows)

    # ═══════════════ VISUALIZE (STATIC) ═══════════════
    def visualize_network(self, G: nx.Graph = None, partition: dict = None,
                          pagerank: dict = None, output_path: str = None,
                          figsize: tuple = (14, 10)) -> plt.Figure:
        """Vẽ đồ thị mạng lưới tĩnh bằng matplotlib."""
        G = G or self.G
        fig, ax = plt.subplots(1, 1, figsize=figsize)

        pos = nx.spring_layout(G, k=1.5 / np.sqrt(G.number_of_nodes()),
                               iterations=50, seed=42, weight="weight")

        # Colors by community
        if partition:
            communities = set(partition.values())
            cmap = plt.cm.get_cmap("tab20", len(communities))
            node_colors = [cmap(partition.get(n, 0)) for n in G.nodes()]
        else:
            node_colors = "skyblue"

        # Sizes by PageRank
        if pagerank:
            sizes = [3000 * pagerank.get(n, 0.01) / max(pagerank.values()) + 100 for n in G.nodes()]
        else:
            sizes = 300

        # Edge widths
        edge_weights = [G[u][v].get("weight", 0.5) * 2 for u, v in G.edges()]

        nx.draw_networkx_edges(G, pos, alpha=0.2, width=edge_weights, ax=ax)
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=sizes,
                               alpha=0.8, ax=ax)

        # Label top nodes
        if pagerank:
            top_nodes = sorted(pagerank, key=pagerank.get, reverse=True)[:15]
            labels = {n: n for n in top_nodes}
        else:
            labels = {n: n for n in list(G.nodes())[:15]}

        nx.draw_networkx_labels(G, pos, labels, font_size=8, font_weight="bold", ax=ax)

        ax.set_title("TFT Champion Co-occurrence Network", fontsize=14, fontweight="bold")
        ax.axis("off")
        plt.tight_layout()

        if output_path:
            fig.savefig(output_path, dpi=150, bbox_inches="tight")
            print(f"💾 Saved: {output_path}")

        return fig

    # ═══════════════ VISUALIZE (INTERACTIVE) ═══════════════
    def visualize_interactive(self, G: nx.Graph = None, partition: dict = None,
                               pagerank: dict = None,
                               output_path: str = "network.html"):
        """Tạo visualization tương tác bằng pyvis."""
        G = G or self.G
        if PyvisNetwork is None:
            print("⚠️ pyvis not installed. Skipping interactive viz.")
            return None

        net = PyvisNetwork(height="700px", width="100%", bgcolor="#222222",
                           font_color="white", notebook=True)

        colors_palette = [
            "#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
            "#911eb4", "#42d4f4", "#f032e6", "#bfef45", "#fabed4",
            "#469990", "#dcbeff", "#9A6324", "#800000", "#aaffc3",
        ]

        pr = pagerank or {}
        max_pr = max(pr.values()) if pr else 1

        for node in G.nodes():
            size = 10 + 40 * (pr.get(node, 0.01) / max_pr)
            if partition:
                comm = partition.get(node, 0)
                color = colors_palette[comm % len(colors_palette)]
            else:
                color = "#42d4f4"
            title = f"{node}\nPageRank: {pr.get(node, 0):.4f}"
            if partition:
                title += f"\nCommunity: {partition.get(node, '?')}"
            net.add_node(node, label=node, size=size, color=color, title=title)

        for u, v, data in G.edges(data=True):
            w = data.get("weight", 0.5)
            net.add_edge(u, v, value=w, title=f"Weight: {w:.3f}")

        net.toggle_physics(True)
        net.save_graph(output_path)
        print(f"🌐 Interactive visualization saved: {output_path}")
        return output_path

    # ═══════════════ NETWORK STATS ═══════════════
    def get_network_stats(self, G: nx.Graph = None) -> dict:
        """Thống kê tổng quan mạng lưới."""
        G = G or self.G
        stats = {
            "num_nodes": G.number_of_nodes(),
            "num_edges": G.number_of_edges(),
            "density": round(nx.density(G), 4),
            "avg_clustering": round(nx.average_clustering(G, weight="weight"), 4),
            "num_components": nx.number_connected_components(G),
        }
        # Avg path length (only for connected graphs)
        if nx.is_connected(G):
            stats["avg_path_length"] = round(nx.average_shortest_path_length(G), 4)
            stats["diameter"] = nx.diameter(G)
        else:
            largest_cc = max(nx.connected_components(G), key=len)
            subG = G.subgraph(largest_cc)
            stats["avg_path_length"] = round(nx.average_shortest_path_length(subG), 4)
            stats["diameter"] = nx.diameter(subG)
            stats["note"] = f"Computed on largest component ({len(largest_cc)} nodes)"

        return stats


if __name__ == "__main__":
    # Demo with small example
    print("🧪 Graph Miner Demo")
    gm = GraphMiner()

    # Create sample co-occurrence matrix
    champs = ["Jinx", "Vi", "Ekko", "Warwick", "Silco",
              "Katarina", "Darius", "Swain", "Sion",
              "Lux", "Garen", "Poppy", "Galio"]
    n = len(champs)
    np.random.seed(42)
    mat = np.random.rand(n, n) * 0.3
    mat = (mat + mat.T) / 2
    np.fill_diagonal(mat, 0)
    # Boost Zaun cluster
    zaun = [0, 1, 2, 3, 4]
    for i in zaun:
        for j in zaun:
            if i != j:
                mat[i][j] += 0.4

    cooc_df = pd.DataFrame(mat, index=champs, columns=champs)

    G = gm.build_network(cooc_df, min_weight=0.1)
    pr, ranking = gm.compute_pagerank(G)
    centrality = gm.compute_centrality_metrics(G)
    print("\nCentrality metrics:\n", centrality.head())

    part, mod, summary = gm.detect_communities_louvain(G)
    print("\nCommunities:\n", summary)

    stats = gm.get_network_stats(G)
    print("\nNetwork stats:", stats)
    print("\n✅ Demo complete!")
