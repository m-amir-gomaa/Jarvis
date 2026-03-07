import sqlite3
import networkx as nx
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import os

class KnowledgeGraph:
    """In-process graph analyzer using networkx and sqlite entities."""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
            self.db_path = str(base_dir / "data" / "knowledge.db")
        else:
            self.db_path = db_path
            
    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def build_graph(self, limit: int = 1000) -> nx.DiGraph:
        """Construct a networkx graph from the last N extracted entities."""
        G = nx.DiGraph()
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT subject, relation, object, chunk_rowid 
                FROM entities 
                ORDER BY id DESC 
                LIMIT ?
            """, (limit,))
            for sub, rel, obj, rowid in cursor:
                # We can store the relation as an edge attribute
                G.add_edge(sub, obj, relation=rel, chunk_id=rowid)
        return G

    def get_related_entities(self, entity_name: str, depth: int = 2) -> List[Dict]:
        """Find immediate neighbors and relations for a given entity."""
        G = self.build_graph()
        if entity_name not in G:
            # Try a case-insensitive fuzzy match if exact fails
            matches = [n for n in G.nodes() if entity_name.lower() in n.lower()]
            if not matches:
                return []
            entity_name = matches[0]

        # Get ego graph (neighborhood)
        ego = nx.ego_graph(G, entity_name, radius=depth)
        
        results = []
        for u, v, data in ego.edges(data=True):
            results.append({
                "subject": u,
                "relation": data.get("relation"),
                "object": v,
                "chunk_id": data.get("chunk_id")
            })
        return results

    def get_recent_relations(self, limit: int = 100) -> List[Dict]:
        """Fetch the most recent relations for the dashboard."""
        results = []
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT subject, relation, object, id 
                FROM entities 
                ORDER BY id DESC 
                LIMIT ?
            """, (limit,))
            for sub, rel, obj, eid in cursor:
                results.append({
                    "id": eid,
                    "subject": sub,
                    "relation": rel,
                    "object": obj
                })
        return results

    def find_path(self, start_entity: str, end_entity: str) -> List[str]:
        """Find the shortest semantic path between two entities."""
        G = self.build_graph()
        try:
            return nx.shortest_path(G, source=start_entity, target=end_entity)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

if __name__ == "__main__":
    # Quick test
    kg = KnowledgeGraph()
    print("Building graph...")
    graph = kg.build_graph()
    print(f"Nodes: {graph.number_of_nodes()}, Edges: {graph.number_of_edges()}")
    
    if graph.number_of_nodes() > 0:
        first_node = list(graph.nodes())[0]
        print(f"Related to '{first_node}':")
        print(kg.get_related_entities(first_node))
