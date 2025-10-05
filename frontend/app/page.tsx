'use client';

import { useState, useEffect } from 'react';
import { KnowledgeGraph } from './components/KnowledgeGraph';
import { AnalyticsPanel } from './components/AnalyticsPanel';
import { Header } from './components/Header';
import { LoadingSpinner } from './components/LoadingSpinner';
import { ErrorMessage } from './components/ErrorMessage';

interface DashboardData {
  basic_stats: {
    total_articles: number;
    articles_with_results: number;
    articles_without_results: number;
  };
  knowledge_graph: {
    total_nodes: number;
    total_edges: number;
    density: number;
  };
  ai_insights: any;
  last_updated: string;
}

export default function Home() {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [knowledgeGraphData, setKnowledgeGraphData] = useState<any>(null);
  const [topics, setTopics] = useState<any>(null);
  const [insights, setInsights] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('main-topics');
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  const [entityDetails, setEntityDetails] = useState<any | null>(null);
  const [entityLoading, setEntityLoading] = useState(false);

  const API_BASE = process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, '') || 'http://localhost:5000/api';

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load dashboard overview
      const overviewResponse = await fetch(`${API_BASE}/dashboard/overview`);
      if (!overviewResponse.ok) throw new Error('Failed to load dashboard data');
      const overviewData = await overviewResponse.json();
      setDashboardData(overviewData);

      // Load knowledge graph
      const graphResponse = await fetch(`${API_BASE}/knowledge-graph`);
      if (!graphResponse.ok) {
        const body = await graphResponse.text();
        // eslint-disable-next-line no-console
        console.error('[Home] knowledge-graph fetch failed', graphResponse.status, body);
        throw new Error(`Knowledge graph API failed (${graphResponse.status})`);
      }
      const graphData = await graphResponse.json();
      // eslint-disable-next-line no-console
      console.log('[Home] knowledge-graph data', {
        nodes: graphData?.graph?.nodes?.length || 0,
        edges: graphData?.graph?.edges?.length || 0,
        topEntities: graphData?.top_entities?.length || 0,
      });
      setKnowledgeGraphData(graphData);

      // Load AI topics (optional)
      try {
      const topicsResponse = await fetch(`${API_BASE}/ai/topics`);
      if (topicsResponse.ok) {
        const topicsData = await topicsResponse.json();
        setTopics(topicsData);
      }
      } catch {}

      // Load AI insights (optional)
      try {
      const insightsResponse = await fetch(`${API_BASE}/ai/insights`);
      if (insightsResponse.ok) {
        const insightsData = await insightsResponse.json();
        setInsights(insightsData);
      }
      } catch {}

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleEntitySelect = (entityName: string) => {
    setSelectedEntity(entityName);
  };

  const handleEntityDeselect = () => {
    setSelectedEntity(null);
    setEntityDetails(null);
  };

  useEffect(() => {
    const fetchEntity = async () => {
      if (!selectedEntity) return;
      try {
        setEntityLoading(true);
        const res = await fetch(`${API_BASE}/knowledge-graph/entity/${encodeURIComponent(selectedEntity)}`);
        if (!res.ok) throw new Error('Failed to load entity');
        const data = await res.json();
        setEntityDetails(data);
      } catch (e) {
        // eslint-disable-next-line no-console
        console.error('[Home] entity fetch failed', e);
        setEntityDetails(null);
      } finally {
        setEntityLoading(false);
      }
    };
    fetchEntity();
  }, [selectedEntity]);

  const renderEntityPanel = () => {
    if (!selectedEntity) return null;
    const rels = entityDetails?.relationships || [];
    const arts = entityDetails?.related_articles || [];
    // Simple client-side summary
    const summary = (() => {
      if (!entityDetails) return 'Loading details...';
      const topRels = rels.slice(0, 5).map((r: any) => r.target);
      const count = arts.length;
      if (count === 0) return `No related articles found for ${selectedEntity}.`;
      return `Top connections: ${topRels.join(', ')}. ${count} related articles available.`;
    })();

    return (
      <div className="w-96 p-4">
        <div className="bg-white rounded-lg shadow-sm h-full flex flex-col">
          <div className="p-4 border-b border-gray-200 flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold text-gray-900">{selectedEntity}</h3>
              <p className="text-xs text-gray-500">Entity details</p>
            </div>
            <button onClick={handleEntityDeselect} className="text-xs px-2 py-1 border rounded hover:bg-gray-50">Close</button>
          </div>
          <div className="p-4 space-y-3 overflow-y-auto">
            <div className="text-sm text-gray-700">
              {entityLoading ? 'Loading...' : summary}
            </div>
            {rels.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-2">Relationships</h4>
                <ul className="space-y-1 text-sm">
                  {rels.slice(0, 20).map((r: any, i: number) => (
                    <li key={`${r.target}-${i}`} className="flex justify-between">
                      <span className="text-gray-700">{r.target}</span>
                      <span className="text-gray-400">w={r.weight}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-2">Related Articles</h4>
              {arts.length === 0 ? (
                <div className="text-sm text-gray-500">No articles found.</div>
              ) : (
                <ul className="space-y-2 text-sm">
                  {arts.slice(0, 15).map((a: any) => (
                    <li key={a.article_id} className="">
                      <a href={a.link} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
                        {a.title}
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <ErrorMessage message={error} onRetry={loadDashboardData} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header 
        totalArticles={dashboardData?.basic_stats.total_articles || 0}
        lastUpdated={dashboardData?.last_updated}
      />
      
      <div className="flex h-[calc(100vh-64px)]">
        {/* Knowledge Graph Panel - Left Side */}
        <div className="flex-1 p-4">
          <div className="bg-white rounded-lg shadow-sm h-full">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">
                Knowledge Graph
              </h2>
              <p className="text-sm text-gray-600">
                Interactive visualization of research concepts and relationships
              </p>
            </div>
            
            <div className="h-[calc(100%-80px)] p-4">
              {knowledgeGraphData ? (
                <KnowledgeGraph
                  data={knowledgeGraphData}
                  onEntitySelect={handleEntitySelect}
                  onEntityDeselect={handleEntityDeselect}
                  selectedEntity={selectedEntity}
                />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500">
                  Knowledge graph data not available
                </div>
              )}
            </div>
          </div>
        </div>
        {/* Right Side: Entity Panel if selected, else Analytics Panel */}
        {selectedEntity ? (
          renderEntityPanel()
        ) : (
          <div className="w-96 p-4">
            <div className="bg-white rounded-lg shadow-sm h-full">
              <AnalyticsPanel
                activeTab={activeTab}
                onTabChange={setActiveTab}
                topics={topics}
                insights={insights}
                selectedEntity={selectedEntity}
                dashboardData={dashboardData}
                knowledgeGraphData={knowledgeGraphData}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
