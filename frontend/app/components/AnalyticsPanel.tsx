'use client';

import { useState } from 'react';
import { 
  Brain, 
  TrendingUp, 
  Eye, 
  Network, 
  Heart, 
  BarChart3, 
  Activity, 
  Layers,
  Save,
  EyeOff,
  ChevronDown,
  ChevronRight
} from 'lucide-react';

interface AnalyticsPanelProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  topics: any;
  insights: any;
  selectedEntity: string | null;
  dashboardData: any;
  knowledgeGraphData: any;
}

const tabs = [
  { id: 'ai-insights', label: 'AI Insights', icon: Brain },
  { id: 'main-topics', label: 'Main Topics', icon: TrendingUp },
  { id: 'influential', label: 'Influential', icon: BarChart3 },
  { id: 'blind-spots', label: 'Blind Spots', icon: Eye },
  { id: 'relations', label: 'Relations', icon: Network },
  { id: 'sentiment', label: 'Sentiment', icon: Heart },
  { id: 'stats', label: 'Stats', icon: BarChart3 },
  { id: 'trends', label: 'Trends', icon: Activity },
  { id: 'structure', label: 'Structure', icon: Layers },
];

export function AnalyticsPanel({ 
  activeTab, 
  onTabChange, 
  topics, 
  insights, 
  selectedEntity,
  dashboardData,
  knowledgeGraphData 
}: AnalyticsPanelProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['main-topics']));

  // Basic frontend cleanup to avoid showing stopwords/noise as concepts
  const STOPWORDS = new Set<string>([
    'the','and','for','with','were','was','are','is','of','in','to','on','by','from','as','at','it','that','this','an','a','or','be','we','our','their','its','pmc','new','group','control','mouse','mice'
  ]);

  const normalizeConcept = (name: string) => name?.trim().toLowerCase();
  const isMeaningful = (name: string) => {
    const n = normalizeConcept(name);
    if (!n) return false;
    if (STOPWORDS.has(n)) return false;
    // Require at least 3 alphanumeric characters total
    const alnum = n.replace(/[^a-z0-9]/gi, '');
    if (alnum.length < 3) return false;
    // Filter out common filler tokens and numeric-only strings
    if (/^\d+$/.test(alnum)) return false;
    return true;
  };

  const toggleSection = (sectionId: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId);
    } else {
      newExpanded.add(sectionId);
    }
    setExpandedSections(newExpanded);
  };

  const renderMainTopics = () => {
    if (!topics?.topics) {
      return (
        <div className="text-center py-8 text-gray-500">
          <Brain className="h-12 w-12 mx-auto mb-4 text-gray-300" />
          <p>AI topic analysis not available</p>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">Main Research Topics</h3>
          <button className="text-blue-600 hover:text-blue-700 text-sm font-medium">
            AI: Summarize Topics
          </button>
        </div>
        
        <p className="text-sm text-gray-600 mb-4">
          Focus on these for high-level understanding
        </p>

        {topics.topics.map((topic: any, index: number) => (
          <div key={index} className="border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-medium text-gray-900">
                {index + 1}. {topic.name}
              </h4>
              <span className="text-sm text-gray-500">
                {topic.percentage}% | {topic.concepts?.length || 0} concepts
              </span>
            </div>
            
            <p className="text-sm text-gray-600 mb-3">
              {topic.description}
            </p>
            
            <div className="flex flex-wrap gap-1">
              {topic.concepts?.slice(0, 8).map((concept: string, i: number) => (
                <span
                  key={i}
                  className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                >
                  {concept}
                </span>
              ))}
              {topic.concepts?.length > 8 && (
                <span className="text-xs text-gray-500">
                  +{topic.concepts.length - 8} more
                </span>
              )}
            </div>
          </div>
        ))}

        <div className="flex space-x-2">
          <button className="flex items-center space-x-1 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm">
            <Save className="h-4 w-4" />
            <span>Save to notes</span>
          </button>
          <button className="flex items-center space-x-1 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm">
            <EyeOff className="h-4 w-4" />
            <span>Hide High-Level Ideas</span>
          </button>
        </div>
      </div>
    );
  };

  const renderInfluentialConcepts = () => {
    const topEntitiesRaw = knowledgeGraphData?.top_entities || [];

    // Deduplicate by normalized name and filter out stopwords/noise
    const seen = new Set<string>();
    const topEntities = topEntitiesRaw
      .filter((e: any) => isMeaningful(e?.name))
      .filter((e: any) => {
        const key = normalizeConcept(e.name);
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      // Prefer higher importance/frequency
      .sort((a: any, b: any) => (b.importance || 0) - (a.importance || 0));
    
    if (topEntities.length === 0) {
      return (
        <div className="text-center py-4 text-gray-500">
          <p>No concept data available</p>
        </div>
      );
    }

    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">Most Influential Concepts</h3>
          <button className="text-blue-600 hover:text-blue-700 text-sm font-medium">
            Reveal Underlying Ideas
          </button>
        </div>

        <div className="space-y-2">
          {topEntities.slice(0, 12).map((entity: any, index: number) => (
            <div
              key={entity.name}
              className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition-colors ${
                selectedEntity === entity.name 
                  ? 'bg-blue-100 border border-blue-200' 
                  : 'hover:bg-gray-50'
              }`}
              onClick={() => {
                if (selectedEntity === entity.name) {
                  // Deselect logic would be handled by parent
                } else {
                  // Select logic would be handled by parent
                }
              }}
            >
              <div className="flex items-center space-x-2">
                <div 
                  className={`w-3 h-3 rounded-full ${
                    entity.degree > 10 ? 'bg-blue-500' :
                    entity.degree > 5 ? 'bg-green-500' : 'bg-gray-400'
                  }`}
                />
                <span className="text-sm font-medium">{entity.name}</span>
              </div>
              <span className="text-xs text-gray-500">
                {entity.frequency} mentions
              </span>
            </div>
          ))}
        </div>

        <div className="flex space-x-2">
          <button className="flex items-center space-x-1 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm">
            <Save className="h-4 w-4" />
            <span>Save to notes</span>
          </button>
        </div>
      </div>
    );
  };

  const renderAIInsights = () => {
    if (!insights) {
      return (
        <div className="text-center py-8 text-gray-500">
          <Brain className="h-12 w-12 mx-auto mb-4 text-gray-300" />
          <p>AI insights not available</p>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        <div>
          <h3 className="font-semibold text-gray-900 mb-3">Research Trends</h3>
          <div className="space-y-2">
            {insights.trends?.map((trend: string, index: number) => (
              <div key={index} className="p-3 bg-blue-50 rounded-lg">
                <p className="text-sm text-blue-900">{trend}</p>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="font-semibold text-gray-900 mb-3">Knowledge Gaps</h3>
          <div className="space-y-2">
            {insights.gaps?.map((gap: string, index: number) => (
              <div key={index} className="p-3 bg-yellow-50 rounded-lg">
                <p className="text-sm text-yellow-900">{gap}</p>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="font-semibold text-gray-900 mb-3">Emerging Areas</h3>
          <div className="space-y-2">
            {insights.emerging_areas?.map((area: string, index: number) => (
              <div key={index} className="p-3 bg-green-50 rounded-lg">
                <p className="text-sm text-green-900">{area}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderStats = () => {
    const stats = dashboardData?.basic_stats;
    const graphStats = dashboardData?.knowledge_graph;

    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="text-2xl font-bold text-blue-900">
              {stats?.total_articles || 0}
            </div>
            <div className="text-sm text-blue-700">Total Articles</div>
          </div>
          
          <div className="bg-green-50 p-4 rounded-lg">
            <div className="text-2xl font-bold text-green-900">
              {stats?.articles_with_results || 0}
            </div>
            <div className="text-sm text-green-700">With Results</div>
          </div>
        </div>

        {graphStats && (
          <div className="space-y-3">
            <h4 className="font-medium text-gray-900">Knowledge Graph</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Nodes:</span>
                <span className="font-medium">{graphStats.total_nodes}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Edges:</span>
                <span className="font-medium">{graphStats.total_edges}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Density:</span>
                <span className="font-medium">{(graphStats.density * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'ai-insights':
        return renderAIInsights();
      case 'main-topics':
        return renderMainTopics();
      case 'influential':
        return (
          <div className="space-y-4">
            {renderInfluentialConcepts()}
          </div>
        );
      case 'stats':
        return renderStats();
      default:
        return (
          <div className="text-center py-8 text-gray-500">
            <p>Content for {activeTab} coming soon...</p>
          </div>
        );
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <div className="flex overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`flex items-center space-x-1 px-3 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="h-4 w-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {renderContent()}
      </div>

      {/* Influential concepts are now shown only under the 'Influential' tab */}
    </div>
  );
}
