import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../api/axios';
import { BookOpen, Award, CheckCircle2, AlertCircle } from 'lucide-react';

const StudentDashboard = () => {
  const { user, logout } = useAuth();
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchResults();
  }, []);

  const fetchResults = async () => {
    try {
      setLoading(true);
      const response = await api.get('/students/me/results');
      setResults(response.data);
    } catch (err) {
      setError('Unable to load your examination results.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-[#F8FAFC]">
      {/* Sidebar for Student */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col hidden md:flex">
        <div className="p-6 border-b border-slate-100">
          <h1 className="text-xl font-bold text-slate-800">AI Evaluator</h1>
          <p className="text-xs text-slate-500 mt-1">Student Portal</p>
        </div>

        <div className="flex-1 py-6 px-4 space-y-1">
          <div className="flex items-center px-4 py-3 text-sm font-medium rounded-xl bg-slate-800 text-white shadow-sm">
            <BookOpen className="w-5 h-5 mr-3 text-white" />
            My Results
          </div>
        </div>

        <div className="p-4 border-t border-slate-100">
          <div className="flex items-center px-4 py-3 mb-2 bg-slate-50 rounded-xl border border-slate-100">
            <div className="w-8 h-8 flex items-center justify-center bg-slate-200 rounded-full text-slate-600 mr-3 font-bold">
              {user?.name?.[0] || 'S'}
            </div>
            <div className="overflow-hidden">
              <p className="text-sm font-semibold text-slate-800 truncate">{user?.name}</p>
              <p className="text-xs text-slate-500 truncate">{user?.roll_number || user?.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="flex w-full items-center px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-xl transition-colors"
          >
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        <header className="bg-white border-b border-slate-200 px-8 py-4 flex items-center justify-between md:hidden">
          <h1 className="text-lg font-bold text-slate-800">AI Evaluator</h1>
          <button onClick={logout} className="text-sm font-medium text-red-600">Logout</button>
        </header>

        <div className="flex-1 overflow-auto p-4 md:p-8">
          <div className="max-w-4xl mx-auto">
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-slate-800">Welcome, {user?.name || 'Student'}</h1>
              <p className="text-slate-500 mt-1">View your examination results and AI feedback.</p>
            </div>

            {error && (
              <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-xl border border-red-100">
                {error}
              </div>
            )}

            {loading ? (
              <div className="text-center py-12 text-slate-500">Loading your results...</div>
            ) : results.length === 0 ? (
              <div className="bg-white p-12 rounded-2xl shadow-sm border border-slate-200 text-center">
                <BookOpen className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-slate-800 mb-1">No results available</h3>
                <p className="text-slate-500">You don't have any evaluated examination scripts yet.</p>
              </div>
            ) : (
              <div className="space-y-6">
                {results.map((result, idx) => (
                  <div key={idx} className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
                    <div className="p-6 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div>
                        <h2 className="text-xl font-bold text-slate-800">{result.exam_name}</h2>
                        <p className="text-slate-500 mt-1">{result.subject_name} • {result.subject_code}</p>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className="text-sm text-slate-500 mb-1">Percentage</p>
                          <p className="text-xl font-bold text-blue-600">{result.percentage}%</p>
                        </div>
                        <div className="h-10 w-px bg-slate-200 hidden md:block"></div>
                        <div className="text-right">
                          <p className="text-sm text-slate-500 mb-1">Total Marks</p>
                          <p className="text-xl font-bold text-slate-800">{result.total_marks} / {result.maximum_marks}</p>
                        </div>
                      </div>
                    </div>

                    <div className="p-6 bg-slate-50">
                      <h3 className="text-sm font-bold text-slate-700 uppercase mb-4">Question-wise Breakdown</h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {result.evaluations && result.evaluations.map((ev, i) => (
                          <div key={i} className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                            <div className="flex justify-between items-center mb-2">
                              <span className="font-bold text-slate-700">Q{ev.question_number}</span>
                              <span className="px-2 py-1 bg-emerald-50 text-emerald-700 text-xs font-bold rounded">
                                {ev.final_marks !== null ? ev.final_marks : ev.awarded_marks} / {ev.max_marks}
                              </span>
                            </div>
                            {ev.feedback && ev.feedback.length > 0 && (
                              <div className="mt-2 text-sm text-slate-600 line-clamp-2">
                                "{ev.feedback[0].feedback_text}"
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default StudentDashboard;
