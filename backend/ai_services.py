"""
AI Services using the official Groq Python SDK for NASA Bioscience Dashboard
Handles summarization, topic modeling, and insight generation
"""

import os
import json
from typing import Dict, List, Optional
import logging
from collections import defaultdict, Counter
import re
from groq import Groq
import httpx
from dotenv import load_dotenv

load_dotenv()

class GroqAIService:
    def __init__(self, api_key: str = None):
        # Prefer explicit api_key, otherwise fall back to env
        api_key = api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set. Provide it via constructor or environment.")
        # Workaround httpx>=0.27 removal of 'proxies' kwarg used by some SDK versions
        # By supplying our own httpx.Client, we bypass the SDK's internal wrapper
        httpx_client = httpx.Client()
        self.client = Groq(api_key=api_key, http_client=httpx_client)
        # Allow model selection via env; default to a fast instant model
        self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        
    def summarize_article(self, article: Dict) -> Dict:
        """Generate AI summary for a single article"""
        try:
            title = article.get('title', '')
            results_full = article.get('results_full', '')
            results_summary = article.get('results_summary', '')
            
            # Combine text for summarization
            text_to_summarize = f"Title: {title}\n\nResults: {results_full}\n\nSummary: {results_summary}"
            
            prompt = f"""
            Analyze this NASA bioscience research article and provide a structured summary:
            
            {text_to_summarize}
            
            Please provide:
            1. Key Findings (2-3 bullet points)
            2. Research Methods Used
            3. Biological Systems Studied
            4. Space Environment Effects Observed
            5. Potential Applications/Implications
            
            Format as JSON with these keys: key_findings, methods, biological_systems, space_effects, applications
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000,
            )
            
            # Try to parse JSON response
            try:
                summary = json.loads(response.choices[0].message.content)
            except json.JSONDecodeError:
                # Fallback to text response
                summary = {
                    "key_findings": [response.choices[0].message.content],
                    "methods": ["Analysis of research article"],
                    "biological_systems": ["Various biological systems"],
                    "space_effects": ["Space environment effects"],
                    "applications": ["Research applications"]
                }
            
            return {
                "article_id": article.get('article_id'),
                "title": title,
                "ai_summary": summary,
                "confidence": 0.8
            }
            
        except Exception as e:
            logging.error(f"Error summarizing article {article.get('article_id')}: {str(e)}")
            return {
                "article_id": article.get('article_id'),
                "title": article.get('title', ''),
                "ai_summary": {"error": "Summary generation failed"},
                "confidence": 0.0
            }
    
    def generate_topic_clusters(self, articles: List[Dict]) -> Dict:
        """Generate AI-powered topic clusters from articles"""
        try:
            # Prepare text for topic analysis
            article_texts = []
            for article in articles[:50]:  # Limit for API efficiency
                if article.get('has_results'):
                    text = f"{article.get('title', '')} {article.get('results_summary', '')}"
                    article_texts.append(text[:500])  # Truncate for efficiency
            
            combined_text = "\n\n".join(article_texts)
            
            prompt = f"""
            Analyze these NASA bioscience research articles and identify the main research topics:
            
            {combined_text}
            
            Please identify 4-6 main research topics and for each topic:
            1. Topic name (2-3 words)
            2. Key concepts/terms (5-8 terms)
            3. Percentage of articles that fit this topic
            4. Brief description (1-2 sentences)
            
            Format as JSON with this structure:
            {{
                "topics": [
                    {{
                        "name": "Topic Name",
                        "concepts": ["concept1", "concept2", ...],
                        "percentage": 25,
                        "description": "Brief description"
                    }}
                ]
            }}
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=1500,
            )
            
            try:
                topics_data = json.loads(response.choices[0].message.content)
                return topics_data
            except json.JSONDecodeError:
                # Fallback topic generation
                return self._fallback_topic_generation(articles)
                
        except Exception as e:
            logging.error(f"Error generating topic clusters: {str(e)}")
            return self._fallback_topic_generation(articles)
    
    def _fallback_topic_generation(self, articles: List[Dict]) -> Dict:
        """Fallback topic generation using keyword analysis"""
        # Extract common terms
        all_text = ' '.join([
            f"{a.get('title', '')} {a.get('results_summary', '')}"
            for a in articles if a.get('has_results')
        ]).lower()
        
        # Common bioscience terms
        keywords = [
            'microgravity', 'spaceflight', 'bone', 'muscle', 'immune',
            'cell', 'gene', 'protein', 'radiation', 'tissue', 'metabolism',
            'expression', 'differentiation', 'apoptosis', 'proliferation'
        ]
        
        keyword_counts = {kw: all_text.count(kw) for kw in keywords}
        sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Create simple topics
        topics = []
        if sorted_keywords[0][1] > 0:
            topics.append({
                "name": "Microgravity Effects",
                "concepts": ["microgravity", "spaceflight", "bone", "muscle"],
                "percentage": 30,
                "description": "Research on how microgravity affects biological systems"
            })
        
        if any(kw in ['immune', 'cell', 'gene'] for kw, count in sorted_keywords[:5]):
            topics.append({
                "name": "Cellular Biology",
                "concepts": ["cell", "gene", "protein", "expression"],
                "percentage": 25,
                "description": "Cellular and molecular responses to space environment"
            })
        
        return {"topics": topics}
    
    def generate_insights(self, articles: List[Dict], knowledge_graph_data: Dict) -> Dict:
        """Generate AI insights about the research corpus"""
        try:
            # Prepare data for insight generation
            top_entities = knowledge_graph_data.get('top_entities', [])[:10]
            entity_names = [e['name'] for e in top_entities]
            
            # Sample articles for analysis
            sample_articles = [a for a in articles if a.get('has_results')][:20]
            article_summaries = [a.get('results_summary', '')[:200] for a in sample_articles]
            
            prompt = f"""
            Based on this NASA bioscience research corpus, generate key insights:
            
            Top Research Concepts: {', '.join(entity_names)}
            
            Sample Research Findings:
            {chr(10).join(article_summaries)}
            
            Please provide:
            1. Key Research Trends (3-4 trends)
            2. Knowledge Gaps (2-3 gaps)
            3. Emerging Research Areas (2-3 areas)
            4. Research Impact Assessment (overall impact level and reasoning)
            
            Format as JSON:
            {{
                "trends": ["trend1", "trend2", ...],
                "gaps": ["gap1", "gap2", ...],
                "emerging_areas": ["area1", "area2", ...],
                "impact_assessment": {{
                    "level": "high/medium/low",
                    "reasoning": "explanation"
                }}
            }}
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=1200,
            )
            
            try:
                insights = json.loads(response.choices[0].message.content)
                return insights
            except json.JSONDecodeError:
                return self._fallback_insights(articles, entity_names)
                
        except Exception as e:
            logging.error(f"Error generating insights: {str(e)}")
            return self._fallback_insights(articles, [])
    
    def _fallback_insights(self, articles: List[Dict], entity_names: List[str]) -> Dict:
        """Fallback insight generation"""
        return {
            "trends": [
                "Focus on microgravity effects on biological systems",
                "Increasing research on cellular and molecular responses",
                "Growing interest in space medicine applications"
            ],
            "gaps": [
                "Long-term space mission effects",
                "Individual variation in space adaptation",
                "Countermeasure effectiveness"
            ],
            "emerging_areas": [
                "Personalized space medicine",
                "AI-driven space biology research",
                "Synthetic biology in space"
            ],
            "impact_assessment": {
                "level": "high",
                "reasoning": "Research addresses critical human spaceflight challenges"
            }
        }
    
    def answer_question(self, question: str, articles: List[Dict], 
                       knowledge_graph_data: Dict) -> Dict:
        """Answer questions about the research corpus"""
        try:
            # Find relevant articles
            relevant_articles = []
            question_lower = question.lower()
            
            for article in articles:
                if article.get('has_results'):
                    text = f"{article.get('title', '')} {article.get('results_summary', '')}".lower()
                    if any(word in text for word in question_lower.split()):
                        relevant_articles.append(article)
            
            # Limit to top 5 most relevant
            relevant_articles = relevant_articles[:5]
            
            if not relevant_articles:
                return {
                    "answer": "I couldn't find relevant information to answer your question.",
                    "confidence": 0.0,
                    "sources": []
                }
            
            # Prepare context
            context = "\n\n".join([
                f"Article: {a.get('title', '')}\nSummary: {a.get('results_summary', '')[:300]}"
                for a in relevant_articles
            ])
            
            prompt = f"""
            Based on this NASA bioscience research context, answer the question:
            
            Question: {question}
            
            Research Context:
            {context}
            
            Please provide a concise, evidence-based answer. If the information is not available, say so clearly.
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500,
            )
            
            answer = response.choices[0].message.content
            
            return {
                "answer": answer,
                "confidence": 0.8,
                "sources": [a.get('article_id') for a in relevant_articles]
            }
            
        except Exception as e:
            logging.error(f"Error answering question: {str(e)}")
            return {
                "answer": "I encountered an error while processing your question.",
                "confidence": 0.0,
                "sources": []
            }
    
    def generate_sentiment_analysis(self, articles: List[Dict]) -> Dict:
        """Analyze sentiment of research outcomes"""
        try:
            # Extract results summaries
            results_texts = [
                a.get('results_summary', '') for a in articles 
                if a.get('has_results') and a.get('results_summary')
            ][:30]  # Limit for API efficiency
            
            combined_results = "\n\n".join(results_texts)
            
            prompt = f"""
            Analyze the sentiment of these research findings from NASA bioscience studies:
            
            {combined_results}
            
            Please categorize the sentiment as:
            1. Positive (beneficial findings, successful outcomes)
            2. Negative (adverse effects, concerning results)
            3. Neutral (descriptive findings, mixed results)
            
            Provide:
            - Overall sentiment distribution (percentages)
            - Key positive findings (3-4 examples)
            - Key negative findings (3-4 examples)
            - Neutral findings (2-3 examples)
            
            Format as JSON with sentiment distribution and examples.
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=800,
            )
            
            try:
                sentiment_data = json.loads(response.choices[0].message.content)
                return sentiment_data
            except json.JSONDecodeError:
                return self._fallback_sentiment_analysis(articles)
                
        except Exception as e:
            logging.error(f"Error in sentiment analysis: {str(e)}")
            return self._fallback_sentiment_analysis(articles)
    
    def _fallback_sentiment_analysis(self, articles: List[Dict]) -> Dict:
        """Fallback sentiment analysis"""
        return {
            "sentiment_distribution": {
                "positive": 40,
                "negative": 30,
                "neutral": 30
            },
            "positive_findings": [
                "Successful adaptation mechanisms identified",
                "Effective countermeasures developed",
                "New therapeutic targets discovered"
            ],
            "negative_findings": [
                "Significant bone density loss observed",
                "Immune system suppression documented",
                "Muscle atrophy in microgravity"
            ],
            "neutral_findings": [
                "Baseline measurements established",
                "Methodology validation completed",
                "Control group comparisons made"
            ]
        }
