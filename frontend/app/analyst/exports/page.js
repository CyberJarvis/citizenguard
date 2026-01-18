'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import useAuthStore from '@/context/AuthContext';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import {
  getExportJobs,
  createExportJob,
  deleteExportJob,
  getScheduledReports,
  createScheduledReport,
  deleteScheduledReport
} from '@/lib/api';
import {
  Download,
  FileText,
  FileSpreadsheet,
  File,
  Plus,
  RefreshCw,
  Trash2,
  X,
  CheckCircle2,
  Clock,
  AlertCircle,
  Loader2,
  Calendar,
  Filter,
  ChevronDown,
  Settings,
  Play,
  Pause,
  MoreVertical,
  Database,
  TrendingUp,
  Map,
  Bell
} from 'lucide-react';
import toast from 'react-hot-toast';
import Cookies from 'js-cookie';

const exportFormats = [
  { value: 'csv', label: 'CSV', icon: FileText, description: 'Comma-separated values' },
  { value: 'excel', label: 'Excel', icon: FileSpreadsheet, description: 'Microsoft Excel format' },
  { value: 'pdf', label: 'PDF', icon: File, description: 'Portable Document Format' }
];

const exportTypes = [
  { value: 'reports', label: 'Hazard Reports', description: 'All hazard reports with details', icon: Database },
  { value: 'analytics', label: 'Analytics Summary', description: 'Statistics, trends & metrics', icon: TrendingUp },
  { value: 'geo', label: 'Geographic Data', description: 'Location-based data with coordinates', icon: Map },
  { value: 'trends', label: 'Trend Data', description: 'Time-series trend analysis', icon: Bell }
];

const dateRangeOptions = [
  { value: '7days', label: 'Last 7 Days' },
  { value: '30days', label: 'Last 30 Days' },
  { value: '90days', label: 'Last 90 Days' },
  { value: '1year', label: 'Last Year' },
  { value: 'all', label: 'All Time' }
];

const scheduleOptions = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' }
];

const statusColors = {
  pending: { bg: 'bg-amber-100', text: 'text-amber-700', icon: Clock },
  processing: { bg: 'bg-blue-100', text: 'text-blue-700', icon: Loader2 },
  completed: { bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircle2 },
  failed: { bg: 'bg-red-100', text: 'text-red-700', icon: AlertCircle }
};

// API base URL for direct downloads
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

function ExportCenterContent() {
  const router = useRouter();
  const { user } = useAuthStore();

  const [exportJobs, setExportJobs] = useState([]);
  const [isExporting, setExporting] = useState(false);
  const [isExportModalOpen, setExportModalOpen] = useState(false);
  const [downloadingJobId, setDownloadingJobId] = useState(null);

  const [loading, setLoading] = useState(true);
  const [scheduledReports, setScheduledReports] = useState([]);
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [activeTab, setActiveTab] = useState('exports');

  // Export form state
  const [exportForm, setExportForm] = useState({
    export_type: 'reports',
    format: 'csv',
    date_range: '30days',
    filters: {},
    include_charts: false
  });

  // Schedule form state
  const [scheduleForm, setScheduleForm] = useState({
    name: '',
    export_type: 'reports',
    format: 'csv',
    schedule_type: 'weekly',
    filters: {}
  });

  const openExportModal = () => setExportModalOpen(true);
  const closeExportModal = () => setExportModalOpen(false);

  // Check authorization
  useEffect(() => {
    if (user && !['analyst', 'authority_admin'].includes(user.role)) {
      router.push('/dashboard');
    }
  }, [user, router]);

  // Fetch export jobs
  const fetchExportJobs = async () => {
    setLoading(true);
    try {
      const response = await getExportJobs();
      if (response.success) {
        setExportJobs(response.data.jobs || []);
      }
    } catch (error) {
      console.error('Error fetching export jobs:', error);
      toast.error('Failed to load export jobs');
    } finally {
      setLoading(false);
    }
  };

  // Fetch scheduled reports
  const fetchScheduledReports = async () => {
    try {
      const response = await getScheduledReports();
      if (response.success) {
        setScheduledReports(response.data.reports || []);
      }
    } catch (error) {
      console.error('Error fetching scheduled reports:', error);
    }
  };

  useEffect(() => {
    fetchExportJobs();
    fetchScheduledReports();
  }, []);

  // Auto-refresh for pending jobs
  useEffect(() => {
    const hasPendingJobs = exportJobs.some(j => j.status === 'pending' || j.status === 'processing');
    if (hasPendingJobs) {
      const interval = setInterval(fetchExportJobs, 5000);
      return () => clearInterval(interval);
    }
  }, [exportJobs]);

  // Create export job
  const handleCreateExport = async () => {
    setExporting(true);
    try {
      const response = await createExportJob({
        export_type: exportForm.export_type,
        export_format: exportForm.format,
        date_range: { relative: exportForm.date_range },
        query_config: exportForm.filters || {},
        columns: null
      });

      if (response.success) {
        const exportData = response.data;
        if (exportData.status === 'completed') {
          toast.success('Export completed! Click Download to get your file.');
        } else if (exportData.status === 'failed') {
          toast.error('Export failed: ' + (exportData.error_message || 'Unknown error'));
        } else {
          toast.success('Export job created');
        }
        closeExportModal();
        fetchExportJobs();
      }
    } catch (error) {
      console.error('Error creating export:', error);
      toast.error('Failed to create export: ' + (error.response?.data?.detail || error.message));
    } finally {
      setExporting(false);
    }
  };

  // Download export - Direct file download
  const handleDownload = async (job) => {
    if (job.status !== 'completed') {
      toast.error('Export is not ready yet');
      return;
    }

    setDownloadingJobId(job.job_id);
    try {
      const token = Cookies.get('access_token');
      const downloadUrl = `${API_BASE_URL}/analyst/export/${job.job_id}/download`;

      // Create a fetch request with auth header
      const response = await fetch(downloadUrl, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Download failed');
      }

      // Get filename from content-disposition header or use default
      const contentDisposition = response.headers.get('content-disposition');
      let filename = job.file_name || `export_${job.job_id}.${job.export_format || 'csv'}`;
      if (contentDisposition) {
        const match = contentDisposition.match(/filename=(.+)/);
        if (match) {
          filename = match[1].replace(/"/g, '');
        }
      }

      // Convert response to blob and download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success('Download started');
    } catch (error) {
      console.error('Error downloading export:', error);
      toast.error('Failed to download export');
    } finally {
      setDownloadingJobId(null);
    }
  };

  // Delete export job
  const handleDeleteJob = async (jobId) => {
    if (!confirm('Are you sure you want to delete this export?')) return;

    try {
      const response = await deleteExportJob(jobId);
      if (response.success) {
        toast.success('Export deleted');
        fetchExportJobs();
      }
    } catch (error) {
      console.error('Error deleting export:', error);
      toast.error('Failed to delete export');
    }
  };

  // Create scheduled report
  const handleCreateSchedule = async () => {
    if (!scheduleForm.name.trim()) {
      toast.error('Name is required');
      return;
    }

    try {
      const response = await createScheduledReport({
        name: scheduleForm.name,
        report_type: scheduleForm.export_type,
        export_format: scheduleForm.format,
        schedule_type: scheduleForm.schedule_type,
        query_config: scheduleForm.filters || {},
        schedule_time: "09:00",
        sections: ["summary", "trends"]
      });

      if (response.success) {
        toast.success('Scheduled report created');
        setShowScheduleModal(false);
        fetchScheduledReports();
        setScheduleForm({
          name: '',
          export_type: 'reports',
          format: 'csv',
          schedule_type: 'weekly',
          filters: {}
        });
      }
    } catch (error) {
      console.error('Error creating schedule:', error);
      toast.error('Failed to create scheduled report');
    }
  };

  // Delete scheduled report
  const handleDeleteSchedule = async (scheduleId) => {
    if (!confirm('Are you sure you want to delete this scheduled report?')) return;

    try {
      const response = await deleteScheduledReport(scheduleId);
      if (response.success) {
        toast.success('Scheduled report deleted');
        fetchScheduledReports();
      }
    } catch (error) {
      console.error('Error deleting schedule:', error);
      toast.error('Failed to delete scheduled report');
    }
  };

  if (loading && exportJobs.length === 0) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center">
            <Loader2 className="w-12 h-12 text-[#0d4a6f] animate-spin mx-auto mb-4" />
            <p className="text-gray-600">Loading export center...</p>
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
        <div className="bg-gradient-to-r from-[#0d4a6f] to-[#083a57] rounded-2xl shadow-lg p-6 text-white relative overflow-hidden">
          <div className="absolute bottom-0 left-0 right-0 opacity-10">
            <svg viewBox="0 0 1440 120" className="w-full h-12">
              <path fill="white" d="M0,32L48,37.3C96,43,192,53,288,58.7C384,64,480,64,576,58.7C672,53,768,43,864,42.7C960,43,1056,53,1152,58.7C1248,64,1344,64,1392,64L1440,64L1440,120L1392,120C1344,120,1248,120,1152,120C1056,120,960,120,864,120C768,120,672,120,576,120C480,120,384,120,288,120C192,120,96,120,48,120L0,120Z"></path>
            </svg>
          </div>
          <div className="relative z-10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-3">
                <div className="p-2 bg-white/20 rounded-xl backdrop-blur-sm">
                  <Download className="w-6 h-6 text-white" />
                </div>
                Export Center
              </h1>
              <p className="text-[#9ecbec] mt-1">
                Download data and schedule automated reports
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => openExportModal()}
                className="flex items-center gap-2 px-4 py-2 bg-white/10 border border-white/20 rounded-xl hover:bg-white/20 transition-colors text-white"
              >
                <Plus className="w-4 h-4" />
                New Export
              </button>
              <button
                onClick={fetchExportJobs}
                disabled={loading}
                className="flex items-center gap-2 px-3 py-2 bg-white/10 border border-white/20 rounded-xl hover:bg-white/20 transition-colors text-white"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200">
          <div className="flex gap-6">
            <button
              onClick={() => setActiveTab('exports')}
              className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'exports'
                  ? 'border-[#0d4a6f] text-[#0d4a6f]'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Export Jobs ({exportJobs.length})
            </button>
            <button
              onClick={() => setActiveTab('scheduled')}
              className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'scheduled'
                  ? 'border-[#0d4a6f] text-[#0d4a6f]'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Scheduled Reports ({scheduledReports.length})
            </button>
          </div>
        </div>

        {/* Export Jobs Tab */}
        {activeTab === 'exports' && (
          <div className="space-y-4">
            {/* Quick Export Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {exportTypes.map((type) => {
                const TypeIcon = type.icon || FileText;
                return (
                  <button
                    key={type.value}
                    onClick={() => {
                      setExportForm({ ...exportForm, export_type: type.value });
                      openExportModal();
                    }}
                    className="p-5 bg-white rounded-xl border border-gray-200 hover:border-[#1a6b9a] hover:shadow-lg transition-all text-left group"
                  >
                    <div className="w-12 h-12 bg-[#e8f4fc] rounded-xl flex items-center justify-center mb-3 group-hover:bg-[#c5e1f5] transition-colors">
                      <TypeIcon className="w-6 h-6 text-[#0d4a6f]" />
                    </div>
                    <h3 className="font-semibold text-gray-900">{type.label}</h3>
                    <p className="text-sm text-gray-500 mt-1">{type.description}</p>
                  </button>
                );
              })}
            </div>

            {/* Export Jobs List */}
            <div className="bg-white rounded-xl border border-gray-200">
              <div className="p-4 border-b border-gray-200">
                <h3 className="font-semibold text-gray-900">Recent Exports</h3>
              </div>
              {exportJobs.length > 0 ? (
                <div className="divide-y divide-gray-100">
                  {exportJobs.map((job) => {
                    const status = statusColors[job.status] || statusColors.pending;
                    const StatusIcon = status.icon;
                    const jobFormat = job.export_format || job.format || 'csv';
                    const FormatIcon = jobFormat === 'excel' ? FileSpreadsheet :
                                       jobFormat === 'pdf' ? File : FileText;

                    return (
                      <div key={job.job_id} className="p-4 hover:bg-gray-50">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            <div className="p-2 bg-gray-100 rounded-lg">
                              <FormatIcon className="w-5 h-5 text-gray-600" />
                            </div>
                            <div>
                              <h4 className="font-medium text-gray-900">
                                {exportTypes.find(t => t.value === job.export_type)?.label || job.export_type}
                              </h4>
                              <div className="flex items-center gap-3 text-sm text-gray-500">
                                <span>{(job.export_format || job.format || 'csv').toUpperCase()}</span>
                                <span>•</span>
                                <span>
                                  {typeof job.date_range === 'object'
                                    ? (dateRangeOptions.find(d => d.value === job.date_range?.relative)?.label || job.date_range?.relative || 'Custom')
                                    : (dateRangeOptions.find(d => d.value === job.date_range)?.label || job.date_range || 'Custom range')}
                                </span>
                                <span>•</span>
                                <span>{new Date(job.created_at).toLocaleString()}</span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-3">
                            <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${status.bg} ${status.text}`}>
                              <StatusIcon className={`w-3 h-3 ${job.status === 'processing' ? 'animate-spin' : ''}`} />
                              {job.status}
                            </span>

                            {job.status === 'completed' && (
                              <button
                                onClick={() => handleDownload(job)}
                                disabled={downloadingJobId === job.job_id}
                                className="flex items-center gap-1 px-3 py-1.5 bg-[#0d4a6f] text-white text-sm rounded-xl hover:bg-[#083a57] disabled:bg-[#1a6b9a] disabled:cursor-wait"
                              >
                                {downloadingJobId === job.job_id ? (
                                  <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Downloading...
                                  </>
                                ) : (
                                  <>
                                    <Download className="w-4 h-4" />
                                    Download
                                  </>
                                )}
                              </button>
                            )}

                            <button
                              onClick={() => handleDeleteJob(job.job_id)}
                              className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>

                        {job.status === 'completed' && job.file_size && (
                          <div className="mt-2 text-sm text-gray-500">
                            File size: {(job.file_size / 1024).toFixed(1)} KB
                            {job.record_count && ` • ${job.record_count} records`}
                          </div>
                        )}

                        {job.status === 'failed' && job.error_message && (
                          <div className="mt-2 text-sm text-red-600">
                            Error: {job.error_message}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="p-12 text-center">
                  <Download className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No exports yet</h3>
                  <p className="text-gray-500 mb-4">Create your first export to download data</p>
                  <button
                    onClick={() => openExportModal()}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-[#0d4a6f] text-white rounded-xl hover:bg-[#083a57]"
                  >
                    <Plus className="w-4 h-4" />
                    Create Export
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Scheduled Reports Tab */}
        {activeTab === 'scheduled' && (
          <div className="space-y-4">
            <div className="flex justify-end">
              <button
                onClick={() => setShowScheduleModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-[#0d4a6f] text-white rounded-xl hover:bg-[#083a57]"
              >
                <Plus className="w-4 h-4" />
                New Schedule
              </button>
            </div>

            <div className="bg-white rounded-xl border border-gray-200">
              <div className="p-4 border-b border-gray-200">
                <h3 className="font-semibold text-gray-900">Automated Reports</h3>
              </div>
              {scheduledReports.length > 0 ? (
                <div className="divide-y divide-gray-100">
                  {scheduledReports.map((schedule) => (
                    <div key={schedule.schedule_id} className="p-4 hover:bg-gray-50">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className={`p-2 rounded-lg ${schedule.is_active ? 'bg-green-100' : 'bg-gray-100'}`}>
                            <Calendar className={`w-5 h-5 ${schedule.is_active ? 'text-green-600' : 'text-gray-400'}`} />
                          </div>
                          <div>
                            <h4 className="font-medium text-gray-900">{schedule.name}</h4>
                            <div className="flex items-center gap-3 text-sm text-gray-500">
                              <span className="capitalize">{schedule.schedule_type}</span>
                              <span>•</span>
                              <span>{exportTypes.find(t => t.value === schedule.report_type)?.label || schedule.report_type} ({(schedule.export_format || schedule.format || 'pdf').toUpperCase()})</span>
                              {schedule.next_run && (
                                <>
                                  <span>•</span>
                                  <span>Next: {new Date(schedule.next_run).toLocaleDateString()}</span>
                                </>
                              )}
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-1 text-xs rounded-full ${
                            schedule.is_active
                              ? 'bg-green-100 text-green-700'
                              : 'bg-gray-100 text-gray-600'
                          }`}>
                            {schedule.is_active ? 'Active' : 'Paused'}
                          </span>
                          <button
                            onClick={() => handleDeleteSchedule(schedule.schedule_id)}
                            className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-12 text-center">
                  <Calendar className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No scheduled reports</h3>
                  <p className="text-gray-500 mb-4">Set up automated exports on a schedule</p>
                  <button
                    onClick={() => setShowScheduleModal(true)}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-[#0d4a6f] text-white rounded-xl hover:bg-[#083a57]"
                  >
                    <Plus className="w-4 h-4" />
                    Create Schedule
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Export Modal */}
        {isExportModalOpen && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl max-w-xl w-full shadow-2xl max-h-[90vh] flex flex-col">
              <div className="p-5 border-b border-gray-200 flex-shrink-0">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-bold text-gray-900">Create Export</h2>
                  <button onClick={closeExportModal} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                    <X className="w-5 h-5 text-gray-500" />
                  </button>
                </div>
              </div>

              <div className="p-5 space-y-5 overflow-y-auto flex-1">
                {/* Export Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Data to Export</label>
                  <div className="grid grid-cols-2 gap-3">
                    {exportTypes.map((type) => {
                      const TypeIcon = type.icon || FileText;
                      return (
                        <button
                          key={type.value}
                          onClick={() => setExportForm({ ...exportForm, export_type: type.value })}
                          className={`p-3 text-left rounded-xl border-2 transition-all ${
                            exportForm.export_type === type.value
                              ? 'border-[#1a6b9a] bg-[#e8f4fc] shadow-sm'
                              : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                          }`}
                        >
                          <div className="flex items-center gap-2 mb-1">
                            <TypeIcon className={`w-4 h-4 ${exportForm.export_type === type.value ? 'text-[#0d4a6f]' : 'text-gray-400'}`} />
                            <p className="font-medium text-gray-900 text-sm">{type.label}</p>
                          </div>
                          <p className="text-xs text-gray-500">{type.description}</p>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Format */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">File Format</label>
                  <div className="flex gap-3">
                    {exportFormats.map((format) => (
                      <button
                        key={format.value}
                        onClick={() => setExportForm({ ...exportForm, format: format.value })}
                        className={`flex-1 flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${
                          exportForm.format === format.value
                            ? 'border-[#1a6b9a] bg-[#e8f4fc] shadow-sm'
                            : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                        }`}
                      >
                        <format.icon className={`w-6 h-6 ${exportForm.format === format.value ? 'text-[#0d4a6f]' : 'text-gray-400'}`} />
                        <div className="text-center">
                          <span className="font-semibold text-sm block">{format.label}</span>
                          <span className="text-xs text-gray-500">{format.description}</span>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Date Range */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Date Range</label>
                  <div className="grid grid-cols-3 gap-2">
                    {dateRangeOptions.map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => setExportForm({ ...exportForm, date_range: opt.value })}
                        className={`p-2 text-sm rounded-lg border-2 transition-all ${
                          exportForm.date_range === opt.value
                            ? 'border-[#1a6b9a] bg-[#e8f4fc] text-[#0d4a6f] font-medium'
                            : 'border-gray-200 hover:border-gray-300 text-gray-600'
                        }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Export Summary */}
                <div className="bg-gray-50 rounded-xl p-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Export Summary</h4>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500 block">Data Type</span>
                      <span className="font-medium text-gray-900">
                        {exportTypes.find(t => t.value === exportForm.export_type)?.label}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">Format</span>
                      <span className="font-medium text-gray-900">
                        {exportFormats.find(f => f.value === exportForm.format)?.label}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">Period</span>
                      <span className="font-medium text-gray-900">
                        {dateRangeOptions.find(d => d.value === exportForm.date_range)?.label}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="p-5 border-t border-gray-200 flex justify-end gap-3 flex-shrink-0 bg-gray-50 rounded-b-2xl">
                <button
                  onClick={closeExportModal}
                  className="px-5 py-2.5 text-gray-700 border border-gray-300 rounded-xl hover:bg-gray-100 font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateExport}
                  disabled={isExporting}
                  className="flex items-center gap-2 px-6 py-2.5 bg-[#0d4a6f] text-white rounded-xl hover:bg-[#083a57] disabled:bg-[#1a6b9a] disabled:cursor-wait font-medium shadow-lg shadow-[#0d4a6f]/25 transition-all"
                >
                  {isExporting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4" />
                      Generate Export
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Schedule Modal */}
        {showScheduleModal && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl max-h-[90vh] flex flex-col">
              <div className="p-5 border-b border-gray-200 flex-shrink-0">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-bold text-gray-900">Create Scheduled Report</h2>
                  <button onClick={() => setShowScheduleModal(false)} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                    <X className="w-5 h-5 text-gray-500" />
                  </button>
                </div>
              </div>

              <div className="p-5 space-y-4 overflow-y-auto flex-1">
                {/* Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Report Name</label>
                  <input
                    type="text"
                    value={scheduleForm.name}
                    onChange={(e) => setScheduleForm({ ...scheduleForm, name: e.target.value })}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a] focus:border-[#1a6b9a] transition-colors"
                    placeholder="Weekly Analytics Report"
                  />
                </div>

                {/* Export Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Report Type</label>
                  <select
                    value={scheduleForm.export_type}
                    onChange={(e) => setScheduleForm({ ...scheduleForm, export_type: e.target.value })}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a] focus:border-[#1a6b9a] transition-colors"
                  >
                    {exportTypes.map((type) => (
                      <option key={type.value} value={type.value}>{type.label}</option>
                    ))}
                  </select>
                </div>

                {/* Format */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Format</label>
                  <select
                    value={scheduleForm.format}
                    onChange={(e) => setScheduleForm({ ...scheduleForm, format: e.target.value })}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a] focus:border-[#1a6b9a] transition-colors"
                  >
                    {exportFormats.map((format) => (
                      <option key={format.value} value={format.value}>{format.label}</option>
                    ))}
                  </select>
                </div>

                {/* Schedule */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Schedule</label>
                  <select
                    value={scheduleForm.schedule_type}
                    onChange={(e) => setScheduleForm({ ...scheduleForm, schedule_type: e.target.value })}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a] focus:border-[#1a6b9a] transition-colors"
                  >
                    {scheduleOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="p-5 border-t border-gray-200 flex justify-end gap-3 flex-shrink-0 bg-gray-50 rounded-b-2xl">
                <button
                  onClick={() => setShowScheduleModal(false)}
                  className="px-5 py-2.5 text-gray-700 border border-gray-300 rounded-xl hover:bg-gray-100 font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateSchedule}
                  className="flex items-center gap-2 px-6 py-2.5 bg-[#0d4a6f] text-white rounded-xl hover:bg-[#083a57] font-medium shadow-lg shadow-[#0d4a6f]/25 transition-all"
                >
                  <Calendar className="w-4 h-4" />
                  Create Schedule
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}

export default function ExportCenter() {
  return <ExportCenterContent />;
}
