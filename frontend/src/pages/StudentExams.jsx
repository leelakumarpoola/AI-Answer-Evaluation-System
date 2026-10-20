import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/axios.jsx';
import { BookOpen, AlertCircle, Search } from 'lucide-react';

const StatusBadge = ({ status }) => {
  const map = {
    COMPLETED:      { label: 'Evaluated',         cls: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
    PENDING_REVIEW: { label: 'Under Review',       cls: 'bg-blue-100 text-blue-700 border-blue-200' },
    PENDING:        { label: 'Evaluation Pending', cls: 'bg-amber-100 text-amber-700 border-amber-200' },
    NOT_SUBMITTED:  { label: 'Not Submitted',      cls: 'bg-slate-100 text-slate-600 border-slate-200' },
  };
  const s = map[status] || { label: status || 'Pending', cls: 'bg-slate-100 text-slate-600 border-slate-200' };
  return (
    <span className={`inline-block text-xs font-bold px-2.5 py-1 rounded-full border ${s.cls}`}>
      {s.label}
    </span>
  );
};

const StudentExams = () => {
  const [myExams, setMyExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');

  const fetchExams = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/students/me/exams');
      setMyExams(res.data || []);
    } catch (err) {
      setError('Unable to load your exams. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchExams(); }, []);

  const filtered = myExams.filter(e => {
    const q = search.toLowerCase();
    return !q || e.exam_name?.toLowerCase().includes(q) || e.subject_name?.toLowerCase().includes(q) || e.subject_code?.toLowerCase().includes(q);
  });

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-800">My Exams</h1>
        <p className="text-slate-500 mt-1">All your assessments across all subjects.</p>
      </div>

      {!loading && myExams.length > 0 && (
        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search by exam name, subject or course code..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      )}

      {loading ? (
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-slate-200 text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-500">Loading assessments...</p>
        </div>
      ) : error ? (
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-red-200 text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-red-600 mb-4">{error}</p>
          <button onClick={fetchExams} className="px-4 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-700 text-sm font-medium">Retry</button>
        </div>
      ) : myExams.length === 0 ? (
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-slate-200 text-center">
          <BookOpen className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-slate-800 mb-1">No Exams Available</h3>
          <p className="text-slate-500 max-w-sm mx-auto">
            Exams will appear here once your professor uploads your answer sheet.
          </p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-200 text-center">
          <p className="text-slate-500">No exams match your search.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(exam => (
            <div key={exam.exam_id} className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200 hover:border-blue-200 transition-all">
              <div className="flex flex-col md:flex-row justify-between md:items-center gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-mono">{exam.subject_code}</span>
                    <span className="text-xs text-slate-500">{exam.subject_name}</span>
                  </div>
                  <h3 className="text-base font-bold text-slate-800">{exam.exam_name}</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Max Marks: {exam.total_marks || exam.maximum_marks || '—'}
                    {exam.exam_date && <> · {new Date(exam.exam_date).toLocaleDateString()}</>}
                  </p>
                </div>
                <div className="flex items-center gap-4 shrink-0">
                  <div className="text-right">
                    {exam.status === 'COMPLETED' ? (
                      <>
                        <div className="text-xl font-black text-emerald-600">
                          {exam.score} <span className="text-sm text-slate-400 font-medium">/ {exam.maximum_marks || exam.total_marks}</span>
                        </div>
                        {exam.percentage != null && (
                          <p className="text-xs font-bold text-slate-500">{exam.percentage}%</p>
                        )}
                      </>
                    ) : (
                      <p className="text-sm font-medium text-amber-600 italic">Pending</p>
                    )}
                    <div className="mt-1">
                      <StatusBadge status={exam.status} />
                    </div>
                  </div>
                  <Link
                    to={`/student/exam/${exam.exam_id}`}
                    className="px-4 py-2 bg-slate-800 text-white rounded-lg text-sm font-semibold hover:bg-slate-700 transition-colors whitespace-nowrap"
                  >
                    View Exam
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default StudentExams;
