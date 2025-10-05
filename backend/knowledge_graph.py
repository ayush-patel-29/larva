"""
Fast Neo4j Knowledge Graph Engine for NASA Bioscience Publications
Optimized for cloud deployment with minimal dependencies
"""

from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
import numpy as np
from collections import defaultdict
import json
import re
from typing import Dict, List, Tuple
import os
from dotenv import load_dotenv

load_dotenv()

class BioscienceKnowledgeGraph:
    def __init__(self, embedding_model=None, neo4j_uri=None, neo4j_user=None, neo4j_password=None):
        self.embedding_model = embedding_model
        
        # Neo4j connection
        self.neo4j_uri = neo4j_uri or os.getenv('NEO4J_URI')
        self.neo4j_user = neo4j_user or os.getenv('NEO4J_USER')
        self.neo4j_password = neo4j_password or os.getenv('NEO4J_PASSWORD')
        
        # Enforce remote-only usage (no localhost defaults)
        if not self.neo4j_uri or not self.neo4j_user or not self.neo4j_password:
            raise RuntimeError("NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD must be set as environment variables for remote Neo4j.")
        if any(h in self.neo4j_uri for h in ['localhost', '127.0.0.1']) or self.neo4j_uri.startswith('bolt://'):
            raise RuntimeError("Local Neo4j URIs are not allowed. Provide a remote 'neo4j+s://' or 'neo4j://<host>' URI via NEO4J_URI.")
        
        print(f"🔗 Connecting to Neo4j: {self.neo4j_uri}")
        
        # Create driver with proper configuration
        if self.neo4j_uri.startswith('neo+s://') or self.neo4j_uri.startswith('neo4j+s://'):
            # Cloud connection (encryption is implied by the URI; do NOT pass encrypted/trust)
            self.driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password),
                max_connection_lifetime=30 * 60,
                max_connection_pool_size=50,
                connection_acquisition_timeout=2 * 60,
            )
        else:
            # Local/self-managed
            self.driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password),
                max_connection_lifetime=30 * 60,
                max_connection_pool_size=50,
                connection_acquisition_timeout=2 * 60,
            )
        
        # Test connection
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            print("✓ Connected to Neo4j successfully")
        except Exception as e:
            print(f"⚠️ Neo4j connection failed: {e}")
            print("Please check your Neo4j credentials")
            raise
        
        # Simple entity patterns (no spaCy needed)
        self.entity_patterns = {
            'genes_proteins': [
                r'\b[A-Z][A-Z0-9]{2,9}\b',  # Gene symbols
                r'\b(?:protein|gene|mRNA|DNA|RNA)\b',  # Common terms
            ],
            'organisms': [
                r'\b(?:mice|mouse|human|drosophila|arabidopsis|rat|zebrafish|cell|cells)\b',
            ],
            'conditions': [
                r'\b(?:microgravity|spaceflight|radiation|hypoxia|hypergravity|control|treatment)\b',
            ],
            'measurements': [
                r'\d+\.?\d*\s*(?:mm|cm|m|g|kg|mg|μm|nm|Gy|cGy|%)',
            ],
            'processes': [
                r'\b(?:expression|transcription|metabolism|apoptosis|differentiation|proliferation)\b',
            ]
        }
        
        # Initialize Neo4j database
        self._initialize_neo4j()

    def _initialize_neo4j(self):
        """Initialize Neo4j database with constraints and indexes"""
        with self.driver.session() as session:
            # Create constraints for uniqueness
            session.run("CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE")
            session.run("CREATE CONSTRAINT article_id IF NOT EXISTS FOR (a:Article) REQUIRE a.article_id IS UNIQUE")
            
            # Create indexes for performance
            session.run("CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)")
            session.run("CREATE INDEX article_title IF NOT EXISTS FOR (a:Article) ON (a.title)")
            
            print("✓ Neo4j database initialized with constraints and indexes")

    def close(self):
        """Close Neo4j driver connection"""
        if self.driver:
            self.driver.close()

    def extract_entities_fast(self, text: str) -> Dict[str, List[str]]:
        """Fast entity extraction using only regex patterns"""
        entities = defaultdict(list)
        
        # Pattern-based extraction only (no spaCy)
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                entities[entity_type].extend(matches)
        
        # Clean and deduplicate
        for entity_type in entities:
            entities[entity_type] = list(set([
                e.strip().lower() for e in entities[entity_type] 
                if len(e.strip()) > 2
            ]))
            
        return dict(entities)

    def build_graph(self, articles: List[Dict]) -> Dict:
        """Build the complete knowledge graph in Neo4j"""
        print("Building Neo4j knowledge graph...")
        
        # Clear existing data
        self._clear_neo4j_data()
        
        # Insert articles and entities
        self._insert_articles_and_entities(articles)
        
        # Build relationships
        self._build_neo4j_relationships()
        
        # Calculate importance scores
        self._calculate_neo4j_importance()
        
        # Get graph stats
        stats = self._get_neo4j_stats()
        
        print(f"✓ Built Neo4j graph with {stats['nodes']} nodes and {stats['edges']} edges")
        return stats

    def _clear_neo4j_data(self):
        """Clear existing Neo4j data"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("✓ Cleared existing Neo4j data")

    def _insert_articles_and_entities(self, articles: List[Dict]):
        """Insert articles and entities into Neo4j"""
        with self.driver.session() as session:
            for article in articles:
                if not article.get('has_results'):
                    continue
                
                # Insert article
                session.run(
                    """
                    MERGE (a:Article {article_id: $article_id})
                    SET a.title = $title,
                        a.link = $link,
                        a.results_summary = $results_summary,
                        a.results_full = $results_full
                    """,
                    article_id=article['article_id'],
                    title=article.get('title', ''),
                    link=article.get('link', ''),
                    results_summary=article.get('results_summary', ''),
                    results_full=article.get('results_full', ''),
                )
                
                # Extract and insert entities
                text = f"{article.get('title', '')} {article.get('results_full', '')} {article.get('results_summary', '')}"
                entities = self.extract_entities_fast(text)
                
                for entity_type, entity_list in entities.items():
                    for entity_name in entity_list:
                        # Insert entity
                        session.run(
                            """
                            MERGE (e:Entity {name: $name})
                            SET e.type = $type,
                                e.frequency = COALESCE(e.frequency, 0) + 1
                            """,
                            name=entity_name,
                            type=entity_type,
                        )
                        
                        # Connect entity to article
                        session.run(
                            """
                            MATCH (a:Article {article_id: $article_id})
                            MATCH (e:Entity {name: $entity_name})
                            MERGE (a)-[:MENTIONS]->(e)
                            """,
                            article_id=article['article_id'],
                            entity_name=entity_name,
                        )
        
        print("✓ Inserted articles and entities into Neo4j")

    def _build_neo4j_relationships(self):
        """Build relationships between entities in Neo4j"""
        with self.driver.session() as session:
            # Find co-occurring entities and create relationships
            session.run(
                """
                MATCH (e1:Entity)-[:MENTIONS]-(a:Article)-[:MENTIONS]-(e2:Entity)
                WHERE e1.name < e2.name
                WITH e1, e2, count(a) as co_occurrence_count
                WHERE co_occurrence_count >= 2
                MERGE (e1)-[r:CO_OCCURS_WITH]->(e2)
                SET r.weight = toFloat(co_occurrence_count),
                    r.co_occurrence_count = co_occurrence_count,
                    r.shared_articles = co_occurrence_count
                """
            )
        
        print("✓ Built entity relationships in Neo4j")

    def _calculate_neo4j_importance(self):
        """Calculate importance scores using Neo4j algorithms"""
        with self.driver.session() as session:
            # Calculate degree using Neo4j 5-compatible syntax
            session.run(
                """
                MATCH (e:Entity)
                WITH e, size([(e)-[:CO_OCCURS_WITH]-() | 1]) AS deg
                SET e.degree = deg
                """
            )
            
            # Calculate importance score (simplified for speed)
            session.run(
                """
                MATCH (e:Entity)
                WITH e, coalesce(e.frequency, 0) AS freq, coalesce(e.degree, 0) AS deg
                SET e.importance = freq * log(toFloat(deg) + 1)
                """
            )
        
        print("✓ Calculated importance scores in Neo4j")

    def _get_neo4j_stats(self) -> Dict:
        """Get Neo4j graph statistics"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (n)
                RETURN 
                    count(n) as total_nodes,
                    count { (n)-[r]-() } as total_edges
                """
            ).single()
            
            if not result:
                return {'nodes': 0, 'edges': 0}
            
            total_nodes = result.get('total_nodes', 0)
            total_edges = result.get('total_edges', 0)
            try:
                undirected_edges = (total_edges or 0) // 2
            except Exception:
                undirected_edges = 0
            
            return {
                'nodes': total_nodes or 0,
                'edges': undirected_edges,
            }

    def get_top_entities(self, n: int = 20) -> List[Dict]:
        """Get top N most important entities from Neo4j"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (e:Entity)
                WHERE e.importance IS NOT NULL
                RETURN e.name as name, e.importance as importance, 
                       e.frequency as frequency, e.degree as degree
                ORDER BY e.importance DESC
                LIMIT $limit
                """,
                limit=n,
            )
            
            entities = []
            for record in result:
                entities.append(
                    {
                        'name': record['name'],
                        'importance': record['importance'],
                        'frequency': record['frequency'],
                        'degree': record['degree'],
                    }
                )
            
            return entities

    def get_entity_relationships(self, entity: str, max_connections: int = 10) -> List[Dict]:
        """Get relationships for a specific entity from Neo4j"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (e1:Entity {name: $entity_name})-[r:CO_OCCURS_WITH]-(e2:Entity)
                RETURN e2.name as target, r.weight as weight, 
                       r.co_occurrence_count as co_occurrence_count,
                       r.shared_articles as shared_articles
                ORDER BY r.weight DESC
                LIMIT $limit
                """,
                entity_name=entity,
                limit=max_connections,
            )
            
            relationships = []
            for record in result:
                relationships.append(
                    {
                        'target': record['target'],
                        'weight': record['weight'],
                        'co_occurrence_count': record['co_occurrence_count'],
                        'shared_articles': record['shared_articles'],
                    }
                )
            
            return relationships

    def get_graph_data(self) -> Dict:
        """Get graph data for visualization from Neo4j.
        Returns a cohesive subgraph: first selects top entities by importance (cap for perf),
        then returns ALL relations among those nodes (no artificial LIMIT on edges).
        """
        with self.driver.session() as session:
            # Get nodes
            nodes_result = session.run(
                """
                MATCH (e:Entity)
                WHERE e.importance IS NOT NULL
                RETURN e.name as id, e.name as label, e.importance as importance,
                       e.frequency as frequency, e.degree as degree
                ORDER BY e.importance DESC
                LIMIT 150
                """
            )
            
            nodes = []
            for record in nodes_result:
                nodes.append(
                    {
                        'id': record['id'],
                        'label': record['label'],
                        'size': (record['importance'] or 1) * 5,
                        'frequency': record['frequency'] or 0,
                        'degree': record['degree'] or 0,
                    }
                )
            
            # Get edges among the selected nodes only (no LIMIT)
            node_names = [n['id'] for n in nodes]
            edges_result = session.run(
                """
                MATCH (e1:Entity)-[r:CO_OCCURS_WITH]-(e2:Entity)
                WHERE e1.name IN $names AND e2.name IN $names
                RETURN e1.name as source, e2.name as target, r.weight as weight,
                       r.co_occurrence_count as co_occurrence_count
                """,
                names=node_names,
            )
            
            edges = []
            for record in edges_result:
                edges.append(
                    {
                        'source': record['source'],
                        'target': record['target'],
                        'weight': record['weight'] or 1,
                        'co_occurrence_count': record['co_occurrence_count'] or 0,
                    }
                )
            
            return {
                'nodes': nodes,
                'edges': edges,
                'stats': {
                    'total_nodes': len(nodes),
                    'total_edges': len(edges),
                    'density': len(edges) / max(len(nodes) * (len(nodes) - 1) / 2, 1) if len(nodes) > 1 else 0,
                },
            }

    def find_communities(self) -> Dict:
        """Find communities/clusters in the Neo4j graph"""
        with self.driver.session() as session:
            # Simple clustering based on entity types and degrees
            result = session.run(
                """
                MATCH (e:Entity)
                WHERE e.importance IS NOT NULL
                RETURN e.name as name, e.type as type, e.degree as degree
                ORDER BY e.importance DESC
                """
            )
            
            communities = defaultdict(list)
            for record in result:
                entity_name = record['name']
                entity_type = record['type']
                degree = record['degree'] or 0
                
                # Cluster by type and degree
                if degree > 5:
                    communities[f"high_degree_{entity_type}"].append(entity_name)
                elif degree > 2:
                    communities[f"medium_degree_{entity_type}"].append(entity_name)
                else:
                    communities[f"low_degree_{entity_type}"].append(entity_name)
            
            return dict(communities)