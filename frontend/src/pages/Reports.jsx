import React, { useState, useEffect, useMemo } from 'react';
import api from '../api/axios';
import { 
  BookOpen, BarChart3, TrendingUp, Award, ArrowDown, Users, CheckCircle2, 
  AlertCircle, PieChart, Clock, FileText, Search, Download, Printer, 
  ChevronRight, ExternalLink, Filter, Sparkles, X, Check
} from 'lucide-react';
import { Link } from 'react-router-dom';

const Reports = () => {
  const [subjects, setSubjects] = useState([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState('');
  const [assessments, setAssessments] = useState([]);
  const [selectedAssessmentId, setSelectedAssessmentId] = useState('');
  const [selectedAssessment, setSelectedAssessment] = useState(null);

  const [loadingData, setLoadingData] = useState(false);
  const [summary, setSummary] = useState(null);
  const [distribution, setDistribution] = useState(null);
  const [questionPerf, setQuestionPerf] = useState([]);
  const [studentPerf, setStudentPerf] = useState([]);
  const [completion, setCompletion] = useState(null);
  const [error, setError] = useState(null);

  // Student list filter & search
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL'); // 'ALL' | 'NEEDS_ACTION' | 'APPROVED' | 'AI_EVALUATED' | 'SCRIPT_UPLOADED' | 'NOT_SUBMITTED'
  const [hoveredSlice, setHoveredSlice] = useState(null);

  useEffect(() => { 
    fetchSubjects(); 
  }, []);

  useEffect(() => {
    if (selectedSubjectId) {
      fetchAssessments(selectedSubjectId);
      setSelectedAssessmentId('');
      setSelectedAssessment(null);
      clearData();
    } else {
      setAssessments([]);
      setSelectedAssessmentId('');
      setSelectedAssessment(null);
      clearData();
    }
  }, [selectedSubjectId]);

  useEffect(() => {
    if (selectedAssessmentId) {
      const a = assessments.find(a => String(a.id) === String(selectedAssessmentId));
      setSelectedAssessment(a || null);
      fetchReports(selectedAssessmentId);
    } else {
      setSelectedAssessment(null);
      clearData();
    }
  }, [selectedAssessmentId]);

  const clearData = () => {
    setSummary(null);
    setDistribution(null);
    setQuestionPerf([]);
    setStudentPerf([]);
    setCompletion(null);
    setError(null);
    setSearchQuery('');
    setStatusFilter('ALL');
  };

  const fetchSubjects = async () => {
    try {
      const res = await api.get('/subjects/');
      setSubjects(res.data);
    } catch (err) { 
      console.error(err); 
    }
  };

  const fetchAssessments = async (subjectId) => {
    try {
      const res = await api.get(`/subjects/${subjectId}/exams`);
      setAssessments(res.data);
    } catch (err) { 
      console.error(err); 
    }
  };

  const fetchReports = async (examId) => {
    try {
      setLoadingData(true);
      setError(null);
      const [summaryRes, distRes, qPerfRes, studentsRes, completionRes] = await Promise.all([
        api.get(`/exams/${examId}/reports/summary`).catch(() => ({ data: null })),
        api.get(`/exams/${examId}/reports/distribution`).catch(() => ({ data: null })),
        api.get(`/exams/${examId}/reports/questions`).catch(() => ({ data: [] })),
        api.get(`/exams/${examId}/reports/students`).catch(() => ({ data: [] })),
        api.get(`/exams/${examId}/reports/completion`).catch(() => ({ data: null }))
      ]);
      setSummary(summaryRes.data);
      setDistribution(distRes.data);
      setQuestionPerf(qPerfRes.data || []);
      setStudentPerf(studentsRes.data || []);
      setCompletion(completionRes.data || null);
    } catch (err) {
      setError('Unable to load reports. Please check the backend connection and try again.');
    } finally {
      setLoadingData(false);
    }
  };

  const selectedSubject = subjects.find(s => String(s.id) === String(selectedSubjectId));

  // ─────────────────────────────────────────────────────────────
  // Pie / Donut Chart Data Calculation
  // ─────────────────────────────────────────────────────────────
  const pieStats = useMemo(() => {
    if (!studentPerf || studentPerf.length === 0) {
      return {
        total: 0,
        approved: 0,
        aiEvaluated: 0,
        scriptUploaded: 0,
        notSubmitted: 0,
        slices: []
      };
    }

    const total = studentPerf.length;
    let approved = 0;
    let aiEvaluated = 0;
    let scriptUploaded = 0;
    let notSubmitted = 0;

    studentPerf.forEach(s => {
      const stage = s.evaluation_stage || (s.result_status === 'COMPLETED' ? 'approved' : (s.answer_script_id ? 'ai_evaluated' : 'not_submitted'));
      if (stage === 'approved') approved++;
      else if (stage === 'ai_evaluated') aiEvaluated++;
      else if (stage === 'script_uploaded') scriptUploaded++;
      else notSubmitted++;
    });

    const slices = [
      { key: 'APPROVED', label: 'Final Marks Published', count: approved, color: '#10B981', bgClass: 'bg-emerald-500', textClass: 'text-emerald-700', borderClass: 'border-emerald-200' },
      { key: 'AI_EVALUATED', label: 'AI Evaluated (Needs Review)', count: aiEvaluated, color: '#F59E0B', bgClass: 'bg-amber-500', textClass: 'text-amber-700', borderClass: 'border-amber-200' },
      { key: 'SCRIPT_UPLOADED', label: 'Script Uploaded (Pending AI)', count: scriptUploaded, color: '#6366F1', bgClass: 'bg-indigo-500', textClass: 'text-indigo-700', borderClass: 'border-indigo-200' },
      { key: 'NOT_SUBMITTED', label: 'Missing / Not Submitted', count: notSubmitted, color: '#94A3B8', bgClass: 'bg-slate-400', textClass: 'text-slate-600', borderClass: 'border-slate-200' }
    ];

    return { total, approved, aiEvaluated, scriptUploaded, notSubmitted, slices };
  }, [studentPerf]);

  // ─────────────────────────────────────────────────────────────
  // Filtered Students for the Tracker Table
  // ─────────────────────────────────────────────────────────────
  const filteredStudents = useMemo(() => {
    return studentPerf.filter(student => {
      const stage = student.evaluation_stage || (student.result_status === 'COMPLETED' ? 'approved' : (student.answer_script_id ? 'ai_evaluated' : 'not_submitted'));
      
      // Status filter
      if (statusFilter === 'NEEDS_ACTION') {
        if (stage !== 'ai_evaluated' && stage !== 'script_uploaded') return false;
      } else if (statusFilter === 'APPROVED') {
        if (stage !== 'approved') return false;
      } else if (statusFilter === 'AI_EVALUATED') {
        if (stage !== 'ai_evaluated') return false;
      } else if (statusFilter === 'SCRIPT_UPLOADED') {
        if (stage !== 'script_uploaded') return false;
      } else if (statusFilter === 'NOT_SUBMITTED') {
        if (stage !== 'not_submitted') return false;
      }

      // Search query filter (matches name, roll number, or email)
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesName = student.student_name?.toLowerCase().includes(q);
        const matchesRoll = student.roll_number?.toLowerCase().includes(q);
        const matchesEmail = student.email?.toLowerCase().includes(q);
        return matchesName || matchesRoll || matchesEmail;
      }

      return true;
    });
  }, [studentPerf, statusFilter, searchQuery]);

  // Export CSV
  const handleExportCSV = () => {
    if (!studentPerf || studentPerf.length === 0) return;

    const headers = ['Roll Number', 'Student Name', 'Email', 'Status', 'AI Suggested Marks', 'Final Marks', 'Max Marks', 'Percentage'];
    const rows = studentPerf.map(s => [
      `"${s.roll_number || ''}"`,
      `"${s.student_name || ''}"`,
      `"${s.email || ''}"`,
      `"${s.evaluation_stage || s.result_status}"`,
      s.ai_suggested_marks ?? '',
      s.total_marks ?? 0,
      s.maximum_marks ?? (selectedAssessment?.total_marks || ''),
      s.percentage != null ? `${s.percentage}%` : ''
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `${selectedSubject?.code || 'Subject'}_${selectedAssessment?.name || 'Assessment'}_Reports.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handlePrint = () => {
    window.print();
  };

  // SVG Donut calculation
  const renderDonutSlices = () => {
    const radius = 68;
    const strokeWidth = 24;
    const circumference = 2 * Math.PI * radius;
    let accumulated = 0;

    if (pieStats.total === 0) {
      return (
        <circle
          cx="100"
          cy="100"
          r={radius}
          fill="none"
          stroke="#E2E8F0"
          strokeWidth={strokeWidth}
        />
      );
    }

    return pieStats.slices.map((slice, i) => {
      const pct = slice.count / pieStats.total;
      const strokeDasharray = `${pct * circumference} ${circumference}`;
      const strokeDashoffset = -(accumulated * circumference);
      accumulated += pct;

      const isHovered = hoveredSlice === slice.key;

      return (
        <circle
          key={slice.key}
          cx="100"
          cy="100"
          r={radius}
          fill="none"
          stroke={slice.color}
          strokeWidth={isHovered ? strokeWidth + 4 : strokeWidth}
          strokeDasharray={strokeDasharray}
          strokeDashoffset={strokeDashoffset}
          className="transition-all duration-300 cursor-pointer"
          onMouseEnter={() => setHoveredSlice(slice.key)}
          onMouseLeave={() => setHoveredSlice(null)}
          onClick={() => setStatusFilter(statusFilter === slice.key ? 'ALL' : slice.key)}
        />
      );
    });
  };

  const renderDistributionBar = (count, max) => {
    const pct = max > 0 ? Math.round((count / max) * 100) : 0;
    return (
      <div className="flex items-center gap-3 flex-1">
        <div className="flex-1 bg-slate-100 rounded-full h-3 overflow-hidden">
          <div 
            className="bg-blue-600 h-3 rounded-full transition-all duration-500" 
            style={{ width: `${pct}%` }} 
          />
        </div>
        <span className="text-sm font-bold text-slate-700 w-12 text-right">{count}</span>
      </div>
    );
  };

  return (
    <div className="max-w-7xl mx-auto pb-12 print:p-0">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-800 tracking-tight">Reports & Analysis</h1>
          <p className="text-slate-500 mt-1">Detailed evaluation tracking, class analytics, and student-wise performance insights.</p>
        </div>

        {selectedAssessmentId && (
          <div className="flex items-center gap-3 print:hidden">
            <button
              onClick={handlePrint}
              className="inline-flex items-center px-4 py-2 border border-slate-300 rounded-xl text-sm font-semibold text-slate-700 bg-white hover:bg-slate-50 shadow-sm transition-all"
            >
              <Printer className="w-4 h-4 mr-2 text-slate-500" />
              Print Report
            </button>
            <button
              onClick={handleExportCSV}
              className="inline-flex items-center px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-xl text-sm font-semibold shadow-sm transition-all"
            >
              <Download className="w-4 h-4 mr-2" />
              Export CSV
            </button>
          </div>
        )}
      </div>

      {/* Selectors */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 mb-8 grid grid-cols-1 md:grid-cols-2 gap-4 print:hidden">
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-1.5">Select Subject:</label>
          <select
            value={selectedSubjectId}
            onChange={(e) => setSelectedSubjectId(e.target.value)}
            className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-slate-800 font-medium text-sm shadow-sm"
          >
            <option value="">-- Choose a Subject --</option>
            {subjects.map(s => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.code}) {s.class_section ? `· ${s.class_section}` : ''}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-1.5">Select Assessment:</label>
          <select
            value={selectedAssessmentId}
            onChange={(e) => setSelectedAssessmentId(e.target.value)}
            disabled={!selectedSubjectId || assessments.length === 0}
            className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-slate-800 font-medium text-sm shadow-sm disabled:bg-slate-50 disabled:text-slate-400"
          >
            <option value="">-- Choose an Assessment --</option>
            {assessments.map(a => (
              <option key={a.id} value={a.id}>
                {a.name} ({a.total_marks || 0} Marks)
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* States */}
      {!selectedSubjectId || !selectedAssessmentId ? (
        <div className="bg-white p-16 rounded-2xl shadow-sm border border-slate-200 text-center">
          <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-4 text-blue-600">
            <BarChart3 className="w-8 h-8" />
          </div>
          <h3 className="text-xl font-bold text-slate-800 mb-1">Select an Assessment</h3>
          <p className="text-slate-500 max-w-md mx-auto text-sm">
            Pick a subject and assessment from the dropdowns above to view interactive charts, evaluation tracking, and student performance.
          </p>
        </div>
      ) : loadingData ? (
        <div className="bg-white p-16 rounded-2xl shadow-sm border border-slate-200 text-center">
          <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-600 font-medium">Generating evaluation analytics & reports...</p>
        </div>
      ) : error ? (
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-red-200 text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <h3 className="text-lg font-bold text-slate-800 mb-1">Unable to Load Reports</h3>
          <p className="text-slate-500 mb-4 text-sm">{error}</p>
          <button 
            onClick={() => fetchReports(selectedAssessmentId)} 
            className="px-5 py-2.5 bg-slate-800 text-white rounded-xl hover:bg-slate-700 text-sm font-semibold shadow-sm"
          >
            Retry
          </button>
        </div>
      ) : (
        <>
          {/* Assessment Header Banner */}
          <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-indigo-950 p-6 md:p-8 rounded-2xl text-white shadow-md mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-white/20 text-white backdrop-blur-sm">
                  {selectedSubject?.code}
                </span>
                <span className="text-slate-300 text-sm">{selectedSubject?.name}</span>
              </div>
              <h2 className="text-2xl md:text-3xl font-extrabold">{selectedAssessment?.name}</h2>
              <p className="text-slate-400 text-sm mt-1">
                Total Marks: <span className="font-semibold text-white">{selectedAssessment?.total_marks || summary?.maximum_marks || 0}</span>
                {selectedAssessment?.exam_date && ` · Conducted on ${new Date(selectedAssessment.exam_date).toLocaleDateString()}`}
              </p>
            </div>

            <Link
              to={`/professor/exams/${selectedAssessmentId}`}
              className="inline-flex items-center px-4 py-2 bg-white/10 hover:bg-white/20 rounded-xl text-sm font-semibold backdrop-blur-sm text-white transition-all border border-white/10"
            >
              Open Evaluation Workspace
              <ExternalLink className="w-4 h-4 ml-2" />
            </Link>
          </div>

          {/* Quick Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
            <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
              <div className="flex items-center text-slate-500 text-xs font-bold uppercase tracking-wider mb-2">
                <Users className="w-4 h-4 mr-1.5 text-slate-400" />
                Enrolled
              </div>
              <p className="text-2xl font-black text-slate-800">{pieStats.total}</p>
              <p className="text-xs text-slate-400 mt-1">Total registered</p>
            </div>

            <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
              <div className="flex items-center text-indigo-600 text-xs font-bold uppercase tracking-wider mb-2">
                <FileText className="w-4 h-4 mr-1.5 text-indigo-500" />
                Scripts
              </div>
              <p className="text-2xl font-black text-indigo-700">
                {pieStats.approved + pieStats.aiEvaluated + pieStats.scriptUploaded}
              </p>
              <p className="text-xs text-slate-400 mt-1">Uploaded to exam</p>
            </div>

            <div className="bg-emerald-50/70 p-5 rounded-2xl shadow-sm border border-emerald-100">
              <div className="flex items-center text-emerald-700 text-xs font-bold uppercase tracking-wider mb-2">
                <CheckCircle2 className="w-4 h-4 mr-1.5 text-emerald-500" />
                Published
              </div>
              <p className="text-2xl font-black text-emerald-800">{pieStats.approved}</p>
              <p className="text-xs text-emerald-600 mt-1">Final marks uploaded</p>
            </div>

            <div className="bg-amber-50/70 p-5 rounded-2xl shadow-sm border border-amber-100">
              <div className="flex items-center text-amber-700 text-xs font-bold uppercase tracking-wider mb-2">
                <Clock className="w-4 h-4 mr-1.5 text-amber-500" />
                Needs Review
              </div>
              <p className="text-2xl font-black text-amber-800">{pieStats.aiEvaluated}</p>
              <p className="text-xs text-amber-600 mt-1">AI done, pending review</p>
            </div>

            <div className="bg-blue-50/70 p-5 rounded-2xl shadow-sm border border-blue-100">
              <div className="flex items-center text-blue-700 text-xs font-bold uppercase tracking-wider mb-2">
                <TrendingUp className="w-4 h-4 mr-1.5 text-blue-500" />
                Class Avg
              </div>
              <p className="text-2xl font-black text-blue-800">
                {summary?.average_marks != null ? Number(summary.average_marks).toFixed(1) : '—'}
              </p>
              <p className="text-xs text-blue-600 mt-1">
                {summary?.average_percentage != null ? `${summary.average_percentage}% average` : `out of ${selectedAssessment?.total_marks || 0}`}
              </p>
            </div>

            <div className="bg-purple-50/70 p-5 rounded-2xl shadow-sm border border-purple-100">
              <div className="flex items-center text-purple-700 text-xs font-bold uppercase tracking-wider mb-2">
                <Award className="w-4 h-4 mr-1.5 text-purple-500" />
                Top Score
              </div>
              <p className="text-2xl font-black text-purple-800">
                {summary?.highest_marks != null ? summary.highest_marks : '—'}
              </p>
              <p className="text-xs text-purple-600 mt-1">
                Low: {summary?.lowest_marks != null ? summary.lowest_marks : '—'}
              </p>
            </div>
          </div>

          {/* MAIN SECTION: Interactive Evaluation Pie Chart & Breakdown */}
          <div className="bg-white p-6 md:p-8 rounded-2xl shadow-sm border border-slate-200 mb-8">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-slate-100 gap-2">
              <div>
                <h3 className="text-xl font-bold text-slate-800 flex items-center">
                  <PieChart className="w-5 h-5 mr-2 text-blue-600" />
                  Evaluation Status & Final Marks Progress
                </h3>
                <p className="text-slate-500 text-sm mt-0.5">
                  Visual distribution of students whose evaluations are complete vs still pending review.
                </p>
              </div>

              {statusFilter !== 'ALL' && (
                <button
                  onClick={() => setStatusFilter('ALL')}
                  className="inline-flex items-center self-start sm:self-auto px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors"
                >
                  <X className="w-3.5 h-3.5 mr-1" />
                  Clear Filter
                </button>
              )}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center pt-6">
              {/* SVG Donut Chart */}
              <div className="lg:col-span-5 flex flex-col items-center justify-center">
                <div className="relative w-56 h-56 flex items-center justify-center">
                  <svg 
                    viewBox="0 0 200 200" 
                    className="w-full h-full transform -rotate-90 filter drop-shadow-sm"
                  >
                    {renderDonutSlices()}
                  </svg>

                  {/* Centered Stat Badge */}
                  <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center px-4">
                    {hoveredSlice ? (
                      (() => {
                        const hovered = pieStats.slices.find(s => s.key === hoveredSlice);
                        const pct = pieStats.total > 0 ? Math.round((hovered.count / pieStats.total) * 100) : 0;
                        return (
                          <>
                            <span className="text-3xl font-black text-slate-800">{pct}%</span>
                            <span className="text-xs font-semibold text-slate-500 mt-0.5 truncate max-w-[120px]">{hovered.label}</span>
                            <span className="text-xs font-bold text-slate-700">{hovered.count} students</span>
                          </>
                        );
                      })()
                    ) : (
                      <>
                        <span className="text-3xl font-black text-slate-800">{pieStats.approved} / {pieStats.total}</span>
                        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider mt-0.5">Published</span>
                        <span className="text-xs font-bold text-emerald-600">
                          {pieStats.total > 0 ? `${Math.round((pieStats.approved / pieStats.total) * 100)}% Complete` : ''}
                        </span>
                      </>
                    )}
                  </div>
                </div>

                <p className="text-xs text-slate-400 mt-4 text-center">
                  Click on any segment or card to filter students below
                </p>
              </div>

              {/* Interactive Legend Cards */}
              <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                {pieStats.slices.map((slice) => {
                  const pct = pieStats.total > 0 ? Math.round((slice.count / pieStats.total) * 100) : 0;
                  const isSelected = statusFilter === slice.key;

                  return (
                    <div
                      key={slice.key}
                      onClick={() => setStatusFilter(isSelected ? 'ALL' : slice.key)}
                      onMouseEnter={() => setHoveredSlice(slice.key)}
                      onMouseLeave={() => setHoveredSlice(null)}
                      className={`p-4 rounded-xl border transition-all cursor-pointer select-none ${
                        isSelected 
                          ? `${slice.borderClass} ring-2 ring-blue-500 shadow-md bg-white` 
                          : 'border-slate-200 hover:border-slate-300 hover:shadow-sm bg-slate-50/50'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className={`w-3 h-3 rounded-full ${slice.bgClass}`} />
                          <span className="text-xs font-bold text-slate-700">{slice.label}</span>
                        </div>
                        {isSelected && <Check className="w-4 h-4 text-blue-600" />}
                      </div>

                      <div className="flex items-baseline justify-between">
                        <span className="text-2xl font-black text-slate-800">{slice.count}</span>
                        <span className="text-sm font-semibold text-slate-500">{pct}%</span>
                      </div>

                      {/* Mini progress bar */}
                      <div className="w-full bg-slate-200/70 h-1.5 rounded-full mt-2.5 overflow-hidden">
                        <div 
                          className={`h-full ${slice.bgClass} rounded-full transition-all duration-500`} 
                          style={{ width: `${pct}%` }} 
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* EVALUATION TRACKER: Who Still Needs to be Evaluated */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 mb-8 overflow-hidden">
            <div className="p-6 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h3 className="text-xl font-bold text-slate-800 flex items-center">
                  <Users className="w-5 h-5 mr-2 text-indigo-600" />
                  Student Evaluation Tracker
                </h3>
                <p className="text-slate-500 text-sm mt-0.5">
                  Identify who has been evaluated, whose marks are published, and who still needs attention.
                </p>
              </div>

              {/* Search Box */}
              <div className="relative min-w-[280px]">
                <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search name, roll no, or email..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9.5 pr-8 py-2 text-sm border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                />
                {searchQuery && (
                  <button 
                    onClick={() => setSearchQuery('')}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>

            {/* Filter Tabs */}
            <div className="px-6 pt-3 border-b border-slate-100 flex flex-wrap items-center gap-2 overflow-x-auto">
              <button
                onClick={() => setStatusFilter('ALL')}
                className={`px-3.5 py-2 text-xs font-bold rounded-lg transition-all ${
                  statusFilter === 'ALL'
                    ? 'bg-slate-800 text-white shadow-sm'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                All Students ({pieStats.total})
              </button>
              <button
                onClick={() => setStatusFilter('NEEDS_ACTION')}
                className={`px-3.5 py-2 text-xs font-bold rounded-lg transition-all flex items-center gap-1.5 ${
                  statusFilter === 'NEEDS_ACTION'
                    ? 'bg-amber-500 text-white shadow-sm'
                    : 'text-amber-700 bg-amber-50 hover:bg-amber-100'
                }`}
              >
                <Clock className="w-3.5 h-3.5" />
                Needs Evaluation / Review ({pieStats.aiEvaluated + pieStats.scriptUploaded})
              </button>
              <button
                onClick={() => setStatusFilter('APPROVED')}
                className={`px-3.5 py-2 text-xs font-bold rounded-lg transition-all flex items-center gap-1.5 ${
                  statusFilter === 'APPROVED'
                    ? 'bg-emerald-600 text-white shadow-sm'
                    : 'text-emerald-700 bg-emerald-50 hover:bg-emerald-100'
                }`}
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                Published ({pieStats.approved})
              </button>
              <button
                onClick={() => setStatusFilter('NOT_SUBMITTED')}
                className={`px-3.5 py-2 text-xs font-bold rounded-lg transition-all flex items-center gap-1.5 ${
                  statusFilter === 'NOT_SUBMITTED'
                    ? 'bg-slate-600 text-white shadow-sm'
                    : 'text-slate-600 bg-slate-100 hover:bg-slate-200'
                }`}
              >
                Missing Script ({pieStats.notSubmitted})
              </button>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-700">
                <thead className="bg-slate-50/80 text-xs uppercase tracking-wider text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="py-3 px-6 font-bold">Student</th>
                    <th className="py-3 px-4 font-bold">Roll Number</th>
                    <th className="py-3 px-4 font-bold">Answer Sheet</th>
                    <th className="py-3 px-4 font-bold">Evaluation Status</th>
                    <th className="py-3 px-4 font-bold text-right">Marks</th>
                    <th className="py-3 px-6 font-bold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredStudents.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="text-center py-12 text-slate-400">
                        <Users className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        No students match the selected filter or search term.
                      </td>
                    </tr>
                  ) : (
                    filteredStudents.map((student, idx) => {
                      const stage = student.evaluation_stage || (student.result_status === 'COMPLETED' ? 'approved' : (student.answer_script_id ? 'ai_evaluated' : 'not_submitted'));
                      const maxMarks = student.maximum_marks || selectedAssessment?.total_marks || 10;
                      
                      // Status Badge configuration
                      let badge = null;
                      if (stage === 'approved') {
                        badge = (
                          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800">
                            <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-600" />
                            Final Marks Published
                          </span>
                        );
                      } else if (stage === 'ai_evaluated') {
                        badge = (
                          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800">
                            <Clock className="w-3.5 h-3.5 mr-1 text-amber-600" />
                            AI Done · Needs Approval
                          </span>
                        );
                      } else if (stage === 'script_uploaded') {
                        badge = (
                          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-indigo-100 text-indigo-800">
                            <Sparkles className="w-3.5 h-3.5 mr-1 text-indigo-600" />
                            Uploaded · Needs AI Eval
                          </span>
                        );
                      } else {
                        badge = (
                          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
                            No Script Uploaded
                          </span>
                        );
                      }

                      // Avatar Initials
                      const initials = (student.student_name || 'S')
                        .split(' ')
                        .map(n => n[0])
                        .slice(0, 2)
                        .join('')
                        .toUpperCase();

                      return (
                        <tr key={idx} className="hover:bg-slate-50/70 transition-colors">
                          {/* Student Details */}
                          <td className="py-3.5 px-6">
                            <div className="flex items-center gap-3">
                              <div className="w-9 h-9 rounded-full bg-slate-100 text-slate-700 flex items-center justify-center font-bold text-xs shrink-0 border border-slate-200">
                                {initials}
                              </div>
                              <div>
                                <p className="font-semibold text-slate-900 leading-tight">{student.student_name}</p>
                                <p className="text-xs text-slate-400 mt-0.5">{student.email || '—'}</p>
                              </div>
                            </div>
                          </td>

                          {/* Roll Number */}
                          <td className="py-3.5 px-4 font-mono text-xs font-semibold text-slate-600">
                            {student.roll_number}
                          </td>

                          {/* Answer Script */}
                          <td className="py-3.5 px-4">
                            {student.answer_script_id ? (
                              <span className="inline-flex items-center text-xs font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded-md">
                                <FileText className="w-3 h-3 mr-1 text-slate-500" />
                                Script #{student.answer_script_id}
                              </span>
                            ) : (
                              <span className="text-xs text-slate-400">Not Uploaded</span>
                            )}
                          </td>

                          {/* Status Badge */}
                          <td className="py-3.5 px-4">
                            {badge}
                          </td>

                          {/* Marks */}
                          <td className="py-3.5 px-4 text-right">
                            {stage === 'approved' ? (
                              <div>
                                <span className="font-extrabold text-slate-900">{student.total_marks}</span>
                                <span className="text-xs text-slate-400 font-medium"> / {maxMarks}</span>
                                <p className="text-xs font-bold text-emerald-600">{student.percentage}%</p>
                              </div>
                            ) : stage === 'ai_evaluated' ? (
                              <div>
                                <span className="font-bold text-amber-800">{student.ai_suggested_marks ?? '—'}</span>
                                <span className="text-xs text-amber-600 font-medium"> / {maxMarks}</span>
                                <p className="text-xs text-amber-500 font-semibold">AI Suggested</p>
                              </div>
                            ) : (
                              <span className="text-slate-400 font-mono text-xs">—</span>
                            )}
                          </td>

                          {/* Action */}
                          <td className="py-3.5 px-6 text-right">
                            <Link
                              to={`/professor/exams/${selectedAssessmentId}`}
                              className={`inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                                stage === 'ai_evaluated'
                                  ? 'bg-amber-500 hover:bg-amber-600 text-white shadow-sm'
                                  : stage === 'script_uploaded'
                                  ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm'
                                  : stage === 'approved'
                                  ? 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                                  : 'text-slate-500 hover:text-slate-800 hover:bg-slate-100'
                              }`}
                            >
                              {stage === 'ai_evaluated' && 'Review & Approve'}
                              {stage === 'script_uploaded' && 'Start AI Eval'}
                              {stage === 'approved' && 'View Script'}
                              {stage === 'not_submitted' && 'Upload'}
                              <ChevronRight className="w-3.5 h-3.5 ml-1" />
                            </Link>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            {/* Table Footer */}
            <div className="p-4 bg-slate-50 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>Showing {filteredStudents.length} of {studentPerf.length} students</span>
              <span>{pieStats.approved} Published · {pieStats.aiEvaluated} Awaiting Review · {pieStats.notSubmitted} Missing</span>
            </div>
          </div>

          {/* LOWER SECTION: Distribution & Question Breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            {/* Score Distribution */}
            {distribution && (
              <div className="bg-white p-6 md:p-8 rounded-2xl shadow-sm border border-slate-200">
                <h3 className="text-lg font-bold text-slate-800 mb-2 flex items-center">
                  <BarChart3 className="w-5 h-5 mr-2 text-blue-600" />
                  Score Distribution
                </h3>
                <p className="text-slate-500 text-xs mb-6">Class grade bracket breakdown based on published final marks.</p>

                <div className="space-y-4">
                  {Object.entries(distribution.distribution || distribution.buckets || {}).map(([range, count], idx) => {
                    const maxCount = Math.max(...Object.values(distribution.distribution || distribution.buckets || {}), 1);
                    return (
                      <div key={idx} className="flex items-center gap-3">
                        <span className="text-xs font-semibold text-slate-600 w-16 shrink-0">{range}%</span>
                        {renderDistributionBar(count, maxCount)}
                        <span className="text-xs text-slate-400 w-16 shrink-0 text-right">
                          {count} student{count !== 1 ? 's' : ''}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Question-wise Performance */}
            {questionPerf.length > 0 && (
              <div className="bg-white p-6 md:p-8 rounded-2xl shadow-sm border border-slate-200">
                <h3 className="text-lg font-bold text-slate-800 mb-2 flex items-center">
                  <TrendingUp className="w-5 h-5 mr-2 text-emerald-600" />
                  Question-wise Performance
                </h3>
                <p className="text-slate-500 text-xs mb-6">Average score per question across approved student evaluations.</p>

                <div className="space-y-4">
                  {questionPerf.map((q, idx) => {
                    const qMax = q.maximum_marks ?? 0;
                    const qAvg = q.average_marks ?? 0;
                    const pct = qMax > 0 ? Math.round((qAvg / qMax) * 100) : 0;
                    
                    let diffBadge = 'text-emerald-700 bg-emerald-50';
                    let diffLabel = 'Well Understood';
                    if (pct < 50) {
                      diffBadge = 'text-red-700 bg-red-50';
                      diffLabel = 'Needs Reinforcement';
                    } else if (pct < 75) {
                      diffBadge = 'text-amber-700 bg-amber-50';
                      diffLabel = 'Moderate';
                    }

                    return (
                      <div key={idx} className="p-3.5 rounded-xl border border-slate-100 hover:border-slate-200 transition-colors bg-slate-50/40">
                        <div className="flex justify-between items-center mb-1.5">
                          <span className="text-sm font-bold text-slate-800">Question {q.question_number}</span>
                          <div className="flex items-center gap-2">
                            <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${diffBadge}`}>
                              {diffLabel}
                            </span>
                            <span className="text-xs font-bold text-slate-700">
                              {qAvg != null ? Number(qAvg).toFixed(1) : '—'} / {qMax}
                            </span>
                          </div>
                        </div>

                        {q.question_text && (
                          <p className="text-xs text-slate-500 line-clamp-1 mb-2">{q.question_text}</p>
                        )}

                        <div className="bg-slate-200/80 rounded-full h-2 overflow-hidden">
                          <div 
                            className="bg-emerald-500 h-2 rounded-full transition-all duration-500" 
                            style={{ width: `${pct}%` }} 
                          />
                        </div>
                        <div className="flex justify-between text-[11px] text-slate-400 mt-1 font-medium">
                          <span>{pct}% average score</span>
                          <span>{q.students_evaluated || 0} evaluated</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Additional Summary Stats */}
          {summary && (
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
              <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-4">Summary Statistics</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <span className="text-xs text-slate-400 block font-medium">Median Marks</span>
                  <span className="text-lg font-extrabold text-slate-800">{summary.median_marks ?? '—'}</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <span className="text-xs text-slate-400 block font-medium">Class Pass Rate</span>
                  <span className="text-lg font-extrabold text-emerald-700">
                    {summary.pass_percentage != null ? `${Number(summary.pass_percentage).toFixed(1)}%` : (summary.average_percentage ? `${summary.average_percentage}%` : '—')}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <span className="text-xs text-slate-400 block font-medium">Standard Deviation</span>
                  <span className="text-lg font-extrabold text-slate-800">
                    {summary.std_deviation != null ? Number(summary.std_deviation).toFixed(2) : '—'}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <span className="text-xs text-slate-400 block font-medium">Evaluation Coverage</span>
                  <span className="text-lg font-extrabold text-blue-700">
                    {pieStats.total > 0 ? `${Math.round(((pieStats.approved + pieStats.aiEvaluated) / pieStats.total) * 100)}%` : '—'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default Reports;
