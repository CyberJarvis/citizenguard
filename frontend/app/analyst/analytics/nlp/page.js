'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import useAuthStore from '@/context/AuthContext';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import { useAnalystStore } from '@/stores/analystStore';
import { getNlpInsights } from '@/lib/api';
import {
  Brain,
  MessageSquare,
  Tag,
  Hash,
  TrendingUp,
  RefreshCw,
  ArrowLeft,
  ChevronDown,
  Loader2,
  Filter,
  Search,
  BarChart2,
  PieChart,
  AlertCircle,
  ThumbsUp,
  ThumbsDown,
  Minus
} from 'lucide-react';
import toast from 'react-hot-toast';

// Dynamic import for ApexCharts
const Chart = dynamic(() => import('react-apexcharts'), { ssr: false });

const dateRangeOptions = [
  { value: '7days', label: 'Last 7 Days' },
  { value: '30days', label: 'Last 30 Days' },
  { value: '90days', label: 'Last 90 Days' },
  { value: '1year', label: 'Last Year' }
];

const sentimentColors = {
  positive: '#22C55E',
  neutral: '#6B7280',
  negative: '#EF4444'
};

function NlpInsightsContent() {
  const router = useRouter();
  const { user } = useAuthStore();
  const { defaultDateRange } = useAnalystStore();

  const [dateRange, setDateRange] = useState(defaultDateRange);
  const [nlpData, setNlpData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showFilters, setShowFilters] = useState(false);
  const [hazardFilter, setHazardFilter] = useState('all');
  const [selectedKeyword, setSelectedKeyword] = useState(null);

  // Check authorization
  useEffect(() => {
    if (user && !['analyst', 'authority_admin'].includes(user.role)) {
      router.push('/dashboard');
    }
  }, [user, router]);

  // Fetch NLP data
  const fetchNlpData = async () => {
    setLoading(true);
    try {
      const response = await getNlpInsights({
        date_range: dateRange,
        hazard_type: hazardFilter !== 'all' ? hazardFilter : undefined
      });

      if (response.success) {
        setNlpData(response.data);
      }
    } catch (error) {
      console.error('Error fetching NLP data:', error);
      toast.error('Failed to load NLP insights');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNlpData();
  }, [dateRange, hazardFilter]);

  // Sentiment chart options
  const sentimentChartOptions = {
    chart: {
      type: 'donut',
      fontFamily: 'inherit'
    },
    labels: ['Positive', 'Neutral', 'Negative'],
    colors: [sentimentColors.positive, sentimentColors.neutral, sentimentColors.negative],
    legend: { position: 'bottom' },
    dataLabels: {
      enabled: true,
      formatter: (val) => `${val.toFixed(0)}%`
    },
    plotOptions: {
      pie: {
        donut: {
          size: '55%',
          labels: {
            show: true,
            total: {
              show: true,
              label: 'Total',
              formatter: (w) => w.globals.seriesTotals.reduce((a, b) => a + b, 0)
            }
          }
        }
      }
    }
  };

  const sentimentSeries = nlpData?.sentiment_distribution
    ? [
        nlpData.sentiment_distribution.positive || 0,
        nlpData.sentiment_distribution.neutral || 0,
        nlpData.sentiment_distribution.negative || 0
      ]
    : [];

  // Keywords trend chart
  const keywordsTrendOptions = {
    chart: {
      type: 'bar',
      toolbar: { show: false },
      fontFamily: 'inherit'
    },
    plotOptions: {
      bar: { horizontal: true, borderRadius: 4, barHeight: '60%' }
    },
    dataLabels: { enabled: false },
    xaxis: {
      categories: nlpData?.top_keywords?.slice(0, 10).map(k => k.keyword) || []
    },
    colors: ['#3B82F6'],
    grid: { borderColor: '#E5E7EB' }
  };

  // Entity chart
  const entityChartOptions = {
    chart: {
      type: 'treemap',
      toolbar: { show: false },
      fontFamily: 'inherit'
    },
    colors: ['#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#EF4444'],
    plotOptions: {
      treemap: {
        distributed: true,
        enableShades: false
      }
    },
    legend: { show: false },
    dataLabels: {
      enabled: true,
      style: { fontSize: '12px' },
      formatter: (text, { value }) => `${text}: ${value}`
    }
  };

  const entitySeries = nlpData?.entities ? [{
    data: nlpData.entities.slice(0, 15).map(e => ({
      x: e.entity,
      y: e.count
    }))
  }] : [];

  // Category sentiment chart
  const categorySentimentOptions = {
    chart: {
      type: 'bar',
      stacked: true,
      toolbar: { show: false },
      fontFamily: 'inherit'
    },
    plotOptions: {
      bar: { horizontal: false, borderRadius: 4, columnWidth: '60%' }
    },
    xaxis: {
      categories: nlpData?.category_sentiment?.map(c => c.category?.replace(/_/g, ' ')) || []
    },
    colors: [sentimentColors.positive, sentimentColors.neutral, sentimentColors.negative],
    legend: { position: 'top' },
    dataLabels: { enabled: false }
  };

  const categorySentimentSeries = nlpData?.category_sentiment ? [
    { name: 'Positive', data: nlpData.category_sentiment.map(c => c.positive || 0) },
    { name: 'Neutral', data: nlpData.category_sentiment.map(c => c.neutral || 0) },
    { name: 'Negative', data: nlpData.category_sentiment.map(c => c.negative || 0) }
  ] : [];

  // Summary stats
  const summaryStats = [
    {
      label: 'Reports Analyzed',
      value: nlpData?.total_analyzed?.toLocaleString() || 0,
      icon: MessageSquare,
      color: 'blue'
    },
    {
      label: 'Unique Keywords',
      value: nlpData?.unique_keywords?.toLocaleString() || 0,
      icon: Tag,
      color: 'green'
    },
    {
      label: 'Entities Found',
      value: nlpData?.total_entities?.toLocaleString() || 0,
      icon: Hash,
      color: 'purple'
    },
    {
      label: 'Avg Sentiment',
      value: nlpData?.avg_sentiment_score?.toFixed(2) || '0.00',
      icon: nlpData?.avg_sentiment_score >= 0.3 ? ThumbsUp :
            nlpData?.avg_sentiment_score <= -0.3 ? ThumbsDown : Minus,
      color: nlpData?.avg_sentiment_score >= 0.3 ? 'green' :
             nlpData?.avg_sentiment_score <= -0.3 ? 'red' : 'gray'
    }
  ];

  if (loading && !nlpData) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center">
            <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
            <p className="text-gray-600">Analyzing report text data...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="p-4 lg:p-6 space-y-6">
        {/* Page Header - Desktop Only */}
        <PageHeader />

        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push('/analyst/analytics')}
              className="p-2 hover:bg-gray-100 rounded-lg"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">NLP Insights</h1>
              <p className="text-gray-600 mt-1">Text analysis and keyword extraction</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
            >
              {dateRangeOptions.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>

            <button
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-lg hover:bg-gray-50"
            >
              <Filter className="w-4 h-4" />
              <span className="text-sm">Filters</span>
              <ChevronDown className={`w-4 h-4 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
            </button>

            <button
              onClick={fetchNlpData}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Filters */}
        {showFilters && (
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Hazard Type</label>
                <select
                  value={hazardFilter}
                  onChange={(e) => setHazardFilter(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">All Hazards</option>
                  <option value="high_waves">High Waves</option>
                  <option value="strong_currents">Strong Currents</option>
                  <option value="storm_surge">Storm Surge</option>
                  <option value="jellyfish">Jellyfish</option>
                  <option value="pollution">Pollution</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* Summary Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {summaryStats.map((stat, index) => (
            <div key={index} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between">
                <div className={`p-2 bg-${stat.color}-100 rounded-lg`}>
                  <stat.icon className={`w-5 h-5 text-${stat.color}-600`} />
                </div>
              </div>
              <div className="mt-3">
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                <p className="text-sm text-gray-600">{stat.label}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Sentiment Distribution */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Overall Sentiment Distribution</h3>
            {sentimentSeries.some(v => v > 0) ? (
              <Chart
                options={sentimentChartOptions}
                series={sentimentSeries}
                type="donut"
                height={300}
              />
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-500">
                No sentiment data available
              </div>
            )}
          </div>

          {/* Top Keywords */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Keywords</h3>
            {nlpData?.top_keywords?.length > 0 ? (
              <Chart
                options={keywordsTrendOptions}
                series={[{ data: nlpData.top_keywords.slice(0, 10).map(k => k.count) }]}
                type="bar"
                height={300}
              />
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-500">
                No keyword data available
              </div>
            )}
          </div>

          {/* Category Sentiment */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Sentiment by Category</h3>
            {categorySentimentSeries[0]?.data?.length > 0 ? (
              <Chart
                options={categorySentimentOptions}
                series={categorySentimentSeries}
                type="bar"
                height={300}
              />
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-500">
                No category sentiment data available
              </div>
            )}
          </div>

          {/* Named Entities */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Named Entities</h3>
            {entitySeries[0]?.data?.length > 0 ? (
              <Chart
                options={entityChartOptions}
                series={entitySeries}
                type="treemap"
                height={300}
              />
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-500">
                No entity data available
              </div>
            )}
          </div>
        </div>

        {/* Keyword Cloud Section */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Keyword Cloud</h3>
          <div className="flex flex-wrap gap-2 justify-center min-h-[200px] items-center">
            {nlpData?.top_keywords?.length > 0 ? (
              nlpData.top_keywords.slice(0, 30).map((keyword, idx) => {
                const maxCount = Math.max(...nlpData.top_keywords.map(k => k.count));
                const size = Math.max(0.8, (keyword.count / maxCount) * 1.5 + 0.5);
                const colors = ['text-blue-600', 'text-green-600', 'text-purple-600', 'text-amber-600', 'text-red-600'];

                return (
                  <button
                    key={idx}
                    onClick={() => setSelectedKeyword(keyword)}
                    className={`px-3 py-1.5 rounded-full border border-gray-200 hover:bg-gray-50 transition-all ${
                      selectedKeyword?.keyword === keyword.keyword ? 'bg-blue-50 border-blue-300' : ''
                    } ${colors[idx % colors.length]}`}
                    style={{ fontSize: `${size}rem` }}
                  >
                    {keyword.keyword}
                  </button>
                );
              })
            ) : (
              <p className="text-gray-500">No keywords available</p>
            )}
          </div>

          {/* Selected keyword details */}
          {selectedKeyword && (
            <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-gray-900">&quot;{selectedKeyword.keyword}&quot;</h4>
                  <p className="text-sm text-gray-600">
                    Appears {selectedKeyword.count} times in reports
                  </p>
                </div>
                <button
                  onClick={() => setSelectedKeyword(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  &times;
                </button>
              </div>
              {selectedKeyword.related_hazards && (
                <div className="mt-2">
                  <span className="text-sm text-gray-600">Related hazard types: </span>
                  <span className="text-sm text-gray-900">
                    {selectedKeyword.related_hazards.join(', ')}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Common Phrases */}
        {nlpData?.common_phrases?.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Common Phrases</h3>
            <div className="space-y-3">
              {nlpData.common_phrases.slice(0, 10).map((phrase, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-medium text-gray-400">#{idx + 1}</span>
                    <span className="text-gray-900">&quot;{phrase.phrase}&quot;</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      phrase.sentiment === 'positive' ? 'bg-green-100 text-green-700' :
                      phrase.sentiment === 'negative' ? 'bg-red-100 text-red-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {phrase.sentiment || 'neutral'}
                    </span>
                    <span className="text-sm text-gray-500">{phrase.count} occurrences</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* AI Insights */}
        {nlpData?.ai_insights && (
          <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-xl border border-purple-200 p-5">
            <div className="flex items-center gap-3 mb-4">
              <Brain className="w-6 h-6 text-purple-600" />
              <h3 className="text-lg font-semibold text-gray-900">AI-Generated Insights</h3>
            </div>
            <div className="space-y-3">
              {nlpData.ai_insights.map((insight, idx) => (
                <div key={idx} className="flex items-start gap-2">
                  <AlertCircle className="w-5 h-5 text-purple-600 mt-0.5 flex-shrink-0" />
                  <p className="text-gray-700">{insight}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}

export default function NlpInsights() {
  return <NlpInsightsContent />;
}
