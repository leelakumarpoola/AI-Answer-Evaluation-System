import React, { useState, useEffect } from 'react';
import api from '../api/axios';
import { BookOpen, Users, TrendingUp, Award, ArrowDown, Search, Filter } from 'lucide-react';

const Results = () => {
  const [subjects, setSubjects] = useState([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState('');
  const [assessments, setAssessments] = useState([]);
  const [selectedAssessmentId, setSelectedAssessmentId] = useState('');
  const [selectedAssessment, setSelectedAssessment] = useState(null);

  const [loadingData, setLoadingData] = useState(false);
  const [results, setResults] = useState([]);
  const [error, setError] = useState(null);

  const [search, setSearch] = useState('');
  const [sortOrder, setSortOrder] = useState('desc');

  useEffect(() => { fetchSubjects(); }, []);

  useEffect(() => {
    if (selectedSubjectId) {
      fetchAssessments(selectedSubjectId);
      setSelectedAssessmentId('');
      setSelectedAssessment(null);
      setResults([]);
    } else {
      setAssessments([]);
      setSelectedAssessmentId('');
      setSelectedAssessment(null);
      setResults([]);
    }
  }, [selectedSubjectId]);

  useEffect(() => {
    if (selectedAssessmentId) {
      const a = assessments.find(a => String(a.id) === String(selectedAssessmentId));
      setSelectedAssessment(a || null);
      fetchResults(selectedAssessmentId);
    } else {
      setSelectedAssessment(null);
      setResults([]);
    }
  }, [selectedAssessmentId]);

  const fetchSubjects = async () => {
    try {
      const res = await api.get('/subjects/');
      setSubjects(res.data);
    } catch (err) { console.error(err); }
  };

  const fetchAssessments = async (subjectId) => {
    try {
      const res = await api.get(`/subjects/${subjectId}/exams`);
      setAssessments(res.data);
    } catch (err) { console.error(err); }
  };

  const fetchResults = async (examId) => {
    try {
      setLoadingData(true);
      setError(null);
      const res = await api.get(`/exams/${examId}/results`);
      setResults(res.data || []);
    } catch (err) {
      if (err.response?.status === 404 || err.response?.status === 400) {
        setResults([]);
      } else {
        setError('Unable to load results. Please check the backend connection and try again.');
      }
    } finally {
      setLoadingData(false);
    }
  };

  const filteredResults = results
    .filter(r => {
      const q = search.toLowerCase();
      return !q || r.student_name?.toLowerCase().includes(q) || r.roll_number?.toLowerCase().includes(q);
    })
    .sort((a, b) => {
      const diff = (b.total_marks || 0) - (a.total_marks || 0);
      return sortOrder === 'desc' ? diff : -diff;
    });

  const completedResults = results.filter(r => r.total_marks != null);
  const avg = completedResults.length > 0 ? (completedResults.reduce((s, r) => s + (r.total_marks || 0), 0) / completedResults.length).toFixed(1) : null;
  const highest = completedResults.length > 0 ? Math.max(...completedResults.map(r => r.total_marks || 0)) : null;
  const lowest = completedResults.length > 0 ? Math.min(...completedResults.map(r => r.total_marks || 0)) : null;

  const selectedSubject = subjects.find(s => String(s.id) === String(selectedSubjectId));

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-800">Results</h1>
        <p className="text-slate-500 mt-1">View evaluated student marks and results.</p>
      </div>

      {/* Selectors */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 mb-8 flex flex-col md:flex-row gap-4">
        <div className="flex-1">
          <label className="block text-sm font-medium text-slate-700 mb-1">Subject:</label>
          <select
            value={selectedSubjectId}
            onChange={(e) => setSelectedSubjectId(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="">-- Select Subject --</option>
            {subjects.map(s => (
              <option key={s.id} value={s.id}>{s.name} ({s.code}) - {s.class_section || s.department}</option>
            ))}
          </select>
        </div>
        <div className="flex-1">
          <label className="block text-sm font-medium text-slate-700 mb-1">Assessment:</label>
          <select
            value={selectedAssessmentId}
            onChange={(e) => setSelectedAssessmentId(e.target.value)}
            disabled={!selectedSubjectId || assessments.length === 0}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white disabled:bg-slate-50"
          >
            <option value="">-- Select Assessment --</option>
            {assessments.map(a => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* States */}
      {!selectedSubjectId || !selectedAssessmentId ? (
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-slate-200 text-center">
          <BookOpen className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-slate-800 mb-1">No Results Selected</h3>
          <p className="text-slate-500">Please select a subject and assessment to view results.</p>
        </div>
      ) : loadingData ? (
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-slate-200 text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-500">Loading results...</p>
        </div>
      ) : error ? (
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-red-200 text-center">
          <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-red-600 text-2xl">!</span>
          </div>
          <h3 className="text-lg font-medium text-slate-800 mb-2">Unable to Load Results</h3>
          <p className="text-slate-500 mb-4">{error}</p>
          <button onClick={() => fetchResults(selectedAssessmentId)} className="px-4 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-700 text-sm font-medium">
            Retry
          </button>
        </div>
      ) : completedResults.length === 0 ? (
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-slate-200 text-center">
          <Users className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-slate-800 mb-1">No Results Available</h3>
          <p className="text-slate-500 max-w-sm mx-auto">
            Results will appear here once the AI evaluation is completed. Please upload the required documents and start the evaluation.
          </p>
        </div>
      ) : (
        <>
          {/* Assessment header */}
          {(selectedSubject || selectedAssessment) && (
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 mb-6">
              <h2 className="text-xl font-bold text-slate-800">{selectedSubject?.name}</h2>
              <p className="text-slate-500">{selectedSubject?.code} · {selectedAssessment?.name}</p>
            </div>
          )}

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
              <div className="flex items-center mb-2">
                <Users className="w-4 h-4 text-slate-400 mr-2" />
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Students</p>
              </div>
              <p className="text-2xl font-bold text-slate-800">{completedResults.length}</p>
            </div>
            <div className="bg-blue-50 p-5 rounded-2xl shadow-sm border border-blue-100">
              <div className="flex items-center mb-2">
                <TrendingUp className="w-4 h-4 text-blue-400 mr-2" />
                <p className="text-xs font-medium text-blue-600 uppercase tracking-wide">Average</p>
              </div>
              <p className="text-2xl font-bold text-blue-800">{avg} <span className="text-sm font-medium">/ {selectedAssessment?.total_marks || '—'}</span></p>
            </div>
            <div className="bg-emerald-50 p-5 rounded-2xl shadow-sm border border-emerald-100">
              <div className="flex items-center mb-2">
                <Award className="w-4 h-4 text-emerald-400 mr-2" />
                <p className="text-xs font-medium text-emerald-600 uppercase tracking-wide">Highest</p>
              </div>
              <p className="text-2xl font-bold text-emerald-800">{highest} <span className="text-sm font-medium">/ {selectedAssessment?.total_marks || '—'}</span></p>
            </div>
            <div className="bg-amber-50 p-5 rounded-2xl shadow-sm border border-amber-100">
              <div className="flex items-center mb-2">
                <ArrowDown className="w-4 h-4 text-amber-400 mr-2" />
                <p className="text-xs font-medium text-amber-600 uppercase tracking-wide">Lowest</p>
              </div>
              <p className="text-2xl font-bold text-amber-800">{lowest} <span className="text-sm font-medium">/ {selectedAssessment?.total_marks || '—'}</span></p>
            </div>
          </div>

          {/* Search + Sort */}
          <div className="flex flex-col md:flex-row gap-3 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search student name or roll number..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              />
            </div>
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-slate-400" />
              <select
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value)}
                className="px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="desc">Sort: Highest First</option>
                <option value="asc">Sort: Lowest First</option>
              </select>
            </div>
          </div>

          {/* Results Table */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">#</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Reg. No.</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Student Name</th>
                    <th className="px-6 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">Marks</th>
                    <th className="px-6 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">Percentage</th>
                    <th className="px-6 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 bg-white">
                  {filteredResults.map((r, idx) => {
                    const pct = r.percentage != null ? r.percentage.toFixed(1) : null;
                    const passed = r.status === 'PASS' || r.status === 'COMPLETED';
                    return (
                      <tr key={r.student_id || idx} className="hover:bg-slate-50 transition-colors">
                        <td className="px-6 py-4 text-sm text-slate-500">{idx + 1}</td>
                        <td className="px-6 py-4 text-sm font-mono font-medium text-slate-800">{r.roll_number}</td>
                        <td className="px-6 py-4 text-sm font-medium text-slate-800">{r.student_name}</td>
                        <td className="px-6 py-4 text-sm text-center font-bold text-slate-800">
                          {r.total_marks != null ? `${r.total_marks} / ${r.maximum_marks || selectedAssessment?.total_marks || '—'}` : '—'}
                        </td>
                        <td className="px-6 py-4 text-sm text-center text-slate-600">{pct != null ? `${pct}%` : '—'}</td>
                        <td className="px-6 py-4 text-center">
                          <span className={`inline-block px-2 py-1 rounded-full text-xs font-bold ${passed ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                            {r.status || '—'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {filteredResults.length === 0 && (
                <div className="p-8 text-center text-slate-500 text-sm">No results match your search.</div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default Results;
