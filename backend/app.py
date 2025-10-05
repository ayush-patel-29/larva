# Flask API for Space Biology Knowledge Engine

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
from sentence_transformers import SentenceTransformer
import chromadb
from typing import Dict, List
from collections import Counter, defaultdict
import os
from knowledge_graph import BioscienceKnowledgeGraph
from ai_services import GroqAIService
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for Next.js frontend

# Configuration
DATA_FILE = './nasa_articles_scraped_20251004_070858.json'

# Global variables
articles_data = []
embedding_model = None
chroma_client = None
collection = None
entity_stats = {}
relationship_stats = {}
knowledge_graph = None
ai_service = None

def initialize():
    """Initialize models and load data"""
    global articles_data, embedding_model, chroma_client, collection, entity_stats, relationship_stats, knowledge_graph, ai_service
    
    print("Initializing API server...")
    
    # Load articles data
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        articles_data = json.load(f)
    
    print(f"✓ Loaded {len(articles_data)} articles")
    
    # Load embedding model
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    print("✓ Loaded embedding model")
    
    # Initialize ChromaDB
    chroma_client = chromadb.Client()
    collection = chroma_client.create_collection(
        name="space_biology_articles",
        metadata={"description": "NASA space biology research"}
    )
    
    # Index articles
    index_articles()
    
    # Initialize Neo4j Knowledge Graph (remote-only via env)
    try:
        knowledge_graph = BioscienceKnowledgeGraph(embedding_model)
        print("✓ Connected to Neo4j knowledge graph")
        
        # Build graph from articles JSON into Neo4j only if empty, or if no importances found
        try:
            existing = knowledge_graph._get_neo4j_stats() or {'nodes': 0, 'edges': 0}
            if (existing.get('nodes') or 0) > 0:
                print(f"ℹ️ Knowledge graph already present: nodes={existing.get('nodes', 0)}, edges={existing.get('edges', 0)}. Skipping rebuild.")
                # Sanity check: ensure visualization data has nodes (importance computed)
                try:
                    gd = knowledge_graph.get_graph_data()
                    if (gd.get('stats', {}).get('total_nodes') or 0) == 0:
                        print("ℹ️ No entities with importance found; recalculating importance and relationships...")
                        knowledge_graph._build_neo4j_relationships()
                        knowledge_graph._calculate_neo4j_importance()
                        gd2 = knowledge_graph.get_graph_data()
                        if (gd2.get('stats', {}).get('total_nodes') or 0) == 0:
                            print("ℹ️ Graph still empty for visualization; rebuilding from articles...")
                            stats = knowledge_graph.build_graph(articles_data)
                            print(f"✓ Rebuilt knowledge graph: nodes={stats.get('nodes', 0)}, edges={stats.get('edges', 0)}")
                except Exception as ie:
                    print(f"⚠️ Graph data check failed: {ie}")
            else:
                stats = knowledge_graph.build_graph(articles_data)
                print(f"✓ Knowledge graph built remotely: nodes={stats.get('nodes', 0)}, edges={stats.get('edges', 0)}")
        except Exception as e:
            print(f"⚠️ Failed to verify/build knowledge graph: {e}")
    except Exception as e:
        print(f"⚠️ Knowledge graph initialization failed: {e}")
        
    
    # Initialize AI Service (with placeholder API key)
    groq_api_key = os.getenv('GROQ_API_KEY', 'your-groq-api-key-here')
    if groq_api_key != 'your-groq-api-key-here':
        ai_service = GroqAIService(groq_api_key)
        print("✓ Initialized AI service")
    else:
        print("⚠️ Groq API key not set - AI features will be limited")
        ai_service = None
    
    print("✓ API server ready!")

def index_articles():
    """Index all articles into ChromaDB"""
    global entity_stats, relationship_stats
    
    print("Indexing articles...")
    doc_id = 0
    
    for article in articles_data:
        if not article.get('has_results'):
            continue
        
        # Index results_full and results_summary
        texts_to_index = []
        
        if article.get('results_full'):
            # Split into chunks (max 500 chars each)
            full_text = article['results_full']
            chunks = [full_text[i:i+500] for i in range(0, len(full_text), 400)]
            texts_to_index.extend(chunks)
        
        if article.get('results_summary'):
            texts_to_index.append(article['results_summary'])
        
        # Generate embeddings and store
        for text in texts_to_index:
            if len(text.strip()) < 50:
                continue
                
            doc_id += 1
            embedding = embedding_model.encode(text).tolist()
            
            collection.add(
                documents=[text],
                embeddings=[embedding],
                ids=[f"doc_{doc_id}"],
                metadatas=[{
                    'article_id': article['article_id'],
                    'title': article['title'][:100],
                    'link': article['link']
                }]
            )
    
    print(f"✓ Indexed {doc_id} document chunks")

# Initialize on startup
initialize()

# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'API is running',
        'total_articles': len(articles_data)
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get knowledge base statistics"""
    articles_with_results = len([a for a in articles_data if a.get('has_results')])
    
    return jsonify({
        'total_articles': len(articles_data),
        'articles_with_results': articles_with_results,
        'articles_without_results': len(articles_data) - articles_with_results
    })

@app.route('/api/articles', methods=['GET'])
def get_articles():
    """Get all articles with pagination"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    has_results = request.args.get('has_results', None)
    
    filtered = articles_data
    if has_results is not None:
        has_results_bool = has_results.lower() == 'true'
        filtered = [a for a in articles_data if a.get('has_results') == has_results_bool]
    
    start = (page - 1) * per_page
    end = start + per_page
    
    return jsonify({
        'articles': filtered[start:end],
        'total': len(filtered),
        'page': page,
        'per_page': per_page,
        'total_pages': (len(filtered) + per_page - 1) // per_page
    })

@app.route('/api/article/<article_id>', methods=['GET'])
def get_article(article_id):
    """Get single article by ID"""
    article = next((a for a in articles_data if a['article_id'] == article_id), None)
    
    if article:
        return jsonify(article)
    else:
        return jsonify({'error': 'Article not found'}), 404

@app.route('/api/search', methods=['POST'])
def semantic_search():
    """
    Semantic search endpoint
    Body: { "query": "your search query", "top_k": 10 }
    """
    try:
        data = request.json
        query = data.get('query', '')
        top_k = data.get('top_k', 10)
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Generate query embedding
        query_embedding = embedding_model.encode(query).tolist()
        
        # Search
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, 50)
        )
        
        # Format results
        formatted_results = []
        seen_articles = set()
        
        for idx in range(len(results['documents'][0])):
            article_id = results['metadatas'][0][idx]['article_id']
            
            # Get full article
            article = next((a for a in articles_data if a['article_id'] == article_id), None)
            
            if article and article_id not in seen_articles:
                seen_articles.add(article_id)
                formatted_results.append({
                    'article_id': article_id,
                    'title': article['title'],
                    'link': article['link'],
                    'matched_text': results['documents'][0][idx],
                    'similarity': 1 - results['distances'][0][idx] if 'distances' in results else None
                })
        
        return jsonify({
            'query': query,
            'results': formatted_results,
            'total': len(formatted_results)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/keywords', methods=['POST'])
def keyword_search():
    """
    Simple keyword search
    Body: { "keywords": ["microgravity", "bone"], "match_all": false }
    """
    try:
        data = request.json
        keywords = data.get('keywords', [])
        match_all = data.get('match_all', False)
        
        if not keywords:
            return jsonify({'error': 'Keywords are required'}), 400
        
        results = []
        
        for article in articles_data:
            if not article.get('has_results'):
                continue
            
            # Search in title and results
            searchable_text = (
                article.get('title', '') + ' ' +
                article.get('results_full', '') + ' ' +
                article.get('results_summary', '')
            ).lower()
            
            # Check keyword matches
            matches = [kw.lower() in searchable_text for kw in keywords]
            
            if match_all:
                if all(matches):
                    results.append({
                        'article_id': article['article_id'],
                        'title': article['title'],
                        'link': article['link'],
                        'matched_keywords': keywords
                    })
            else:
                if any(matches):
                    matched = [kw for kw, match in zip(keywords, matches) if match]
                    results.append({
                        'article_id': article['article_id'],
                        'title': article['title'],
                        'link': article['link'],
                        'matched_keywords': matched
                    })
        
        return jsonify({
            'keywords': keywords,
            'match_all': match_all,
            'results': results,
            'total': len(results)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/extract/entities', methods=['POST'])
def extract_entities_from_text():
    """
    Extract entities from provided text
    Body: { "text": "your text here" }
    """
    try:
        import re
        
        data = request.json
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        
        # Extract genes/proteins (uppercase acronyms)
        genes = re.findall(r'\b[A-Z][A-Z0-9]{2,9}\b', text)
        
        # Extract numbers with units (measurements)
        measurements = re.findall(r'\d+\.?\d*\s*(?:mm|cm|m|g|kg|mg|Î¼m|nm|Gy|cGy|%)', text)
        
        # Extract organisms
        organisms = []
        organism_patterns = ['mice', 'mouse', 'human', 'drosophila', 'arabidopsis', 'cells']
        for pattern in organism_patterns:
            if pattern in text.lower():
                organisms.append(pattern)
        
        return jsonify({
            'genes_proteins': list(set(genes)),
            'measurements': list(set(measurements)),
            'organisms': list(set(organisms)),
            'text_length': len(text)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/summary', methods=['GET'])
def get_summary():
    """Get summary of all articles"""
    try:
        # Keywords frequency
        all_text = ' '.join([
            a.get('title', '') + ' ' + 
            a.get('results_summary', '')
            for a in articles_data if a.get('has_results')
        ]).lower()
        
        # Common space biology terms
        keywords_to_count = [
            'microgravity', 'spaceflight', 'radiation', 'bone', 'muscle',
            'gene', 'cell', 'protein', 'mice', 'expression', 'tissue',
            'astronaut', 'iss', 'space', 'atrophy', 'metabolism'
        ]
        
        keyword_counts = {
            kw: all_text.count(kw) for kw in keywords_to_count
        }
        
        # Sort by frequency
        sorted_keywords = sorted(
            keyword_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return jsonify({
            'total_articles': len(articles_data),
            'articles_with_results': len([a for a in articles_data if a.get('has_results')]),
            'top_keywords': sorted_keywords[:15]
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# KNOWLEDGE GRAPH ENDPOINTS
# ============================================================================

@app.route('/api/knowledge-graph', methods=['GET'])
def get_knowledge_graph():
    """Get the complete knowledge graph data"""
    try:
        if not knowledge_graph:
            return jsonify({'error': 'Knowledge graph not initialized'}), 500
        
        graph_data = knowledge_graph.get_graph_data()
        # Self-heal: if empty, try recalculating importance/relationships and rebuild if needed
        if (graph_data.get('stats', {}).get('total_nodes') or 0) == 0:
            try:
                knowledge_graph._build_neo4j_relationships()
                knowledge_graph._calculate_neo4j_importance()
                graph_data = knowledge_graph.get_graph_data()
            except Exception:
                pass
        if (graph_data.get('stats', {}).get('total_nodes') or 0) == 0:
            try:
                stats = knowledge_graph.build_graph(articles_data)
                graph_data = knowledge_graph.get_graph_data()
                print(f"ℹ️ Graph rebuilt via API request: nodes={stats.get('nodes', 0)}, edges={stats.get('edges', 0)}")
            except Exception as e:
                print(f"⚠️ Graph rebuild failed: {e}")

        top_entities = knowledge_graph.get_top_entities(20)
        
        return jsonify({
            'graph': graph_data,
            'top_entities': top_entities,
            'stats': {
                'total_nodes': graph_data['stats']['total_nodes'],
                'total_edges': graph_data['stats']['total_edges'],
                'density': graph_data['stats']['density']
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/knowledge-graph/entity/<entity_name>', methods=['GET'])
def get_entity_details(entity_name):
    """Get details and relationships for a specific entity"""
    try:
        if not knowledge_graph:
            return jsonify({'error': 'Knowledge graph not initialized'}), 500
        
        relationships = knowledge_graph.get_entity_relationships(entity_name)
        
        # Get articles mentioning this entity
        related_articles = []
        for article in articles_data:
            if article.get('has_results'):
                text = f"{article.get('title', '')} {article.get('results_full', '')} {article.get('results_summary', '')}"
                if entity_name.lower() in text.lower():
                    related_articles.append({
                        'article_id': article['article_id'],
                        'title': article['title'],
                        'link': article['link']
                    })
        
        return jsonify({
            'entity': entity_name,
            'relationships': relationships,
            'related_articles': related_articles[:10],  # Limit to 10 articles
            'total_articles': len(related_articles)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/knowledge-graph/communities', methods=['GET'])
def get_communities():
    """Get community/cluster information from the knowledge graph"""
    try:
        if not knowledge_graph:
            return jsonify({'error': 'Knowledge graph not initialized'}), 500
        
        communities = knowledge_graph.find_communities()
        
        return jsonify({
            'communities': communities,
            'total_communities': len(communities)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# AI ENDPOINTS
# ============================================================================

@app.route('/api/ai/summarize', methods=['POST'])
def ai_summarize_article():
    """Generate AI summary for an article"""
    try:
        if not ai_service:
            return jsonify({'error': 'AI service not available'}), 503
        
        data = request.json
        article_id = data.get('article_id')
        
        if not article_id:
            return jsonify({'error': 'article_id is required'}), 400
        
        # Find article
        article = next((a for a in articles_data if a['article_id'] == article_id), None)
        if not article:
            return jsonify({'error': 'Article not found'}), 404
        
        summary = ai_service.summarize_article(article)
        return jsonify(summary)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/topics', methods=['GET'])
def ai_generate_topics():
    """Generate AI-powered topic clusters"""
    try:
        if not ai_service:
            return jsonify({'error': 'AI service not available'}), 503
        
        topics = ai_service.generate_topic_clusters(articles_data)
        return jsonify(topics)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/insights', methods=['GET'])
def ai_generate_insights():
    """Generate AI insights about the research corpus"""
    try:
        if not ai_service:
            return jsonify({'error': 'AI service not available'}), 503
        
        # Get knowledge graph data
        graph_data = {
            'top_entities': knowledge_graph.get_top_entities(20) if knowledge_graph else []
        }
        
        insights = ai_service.generate_insights(articles_data, graph_data)
        return jsonify(insights)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/ask', methods=['POST'])
def ai_ask_question():
    """Answer questions about the research corpus"""
    try:
        if not ai_service:
            return jsonify({'error': 'AI service not available'}), 503
        
        data = request.json
        question = data.get('question', '')
        
        if not question:
            return jsonify({'error': 'question is required'}), 400
        
        # Get knowledge graph data
        graph_data = {
            'top_entities': knowledge_graph.get_top_entities(20) if knowledge_graph else []
        }
        
        answer = ai_service.answer_question(question, articles_data, graph_data)
        return jsonify(answer)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/sentiment', methods=['GET'])
def ai_sentiment_analysis():
    """Analyze sentiment of research outcomes"""
    try:
        if not ai_service:
            return jsonify({'error': 'AI service not available'}), 503
        
        sentiment = ai_service.generate_sentiment_analysis(articles_data)
        return jsonify(sentiment)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# DASHBOARD ANALYTICS ENDPOINTS
# ============================================================================

@app.route('/api/dashboard/overview', methods=['GET'])
def get_dashboard_overview():
    """Get comprehensive dashboard overview data"""
    try:
        # Basic stats
        articles_with_results = len([a for a in articles_data if a.get('has_results')])
        
        # Knowledge graph stats
        graph_stats = {}
        if knowledge_graph:
            graph_data = knowledge_graph.get_graph_data()
            graph_stats = {
                'total_nodes': graph_data['stats']['total_nodes'],
                'total_edges': graph_data['stats']['total_edges'],
                'density': graph_data['stats']['density']
            }
        
        # AI insights (if available)
        ai_insights = {}
        if ai_service:
            try:
                graph_data = {'top_entities': knowledge_graph.get_top_entities(20) if knowledge_graph else []}
                ai_insights = ai_service.generate_insights(articles_data, graph_data)
            except:
                ai_insights = {'error': 'AI insights unavailable'}
        
        return jsonify({
            'basic_stats': {
                'total_articles': len(articles_data),
                'articles_with_results': articles_with_results,
                'articles_without_results': len(articles_data) - articles_with_results
            },
            'knowledge_graph': graph_stats,
            'ai_insights': ai_insights,
            'last_updated': '2024-01-01T00:00:00Z'  # You can make this dynamic
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting API server...")
    print("Server started at http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
