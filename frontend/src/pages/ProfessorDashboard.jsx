import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { BookOpen, FileText, Users, CheckCircle2, AlertCircle, BarChart3, PlayCircle } from 'lucide-react';
import api from '../api/axios';
import { Link } from 'react-router-dom';

const ProfessorDashboard = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState({
    subjects: 0,
    exams: 0,
    students: 0,
    pending: 0,
    completed: 0,
    approved: 0
  });
  const [recentSubjects, setRecentSubjects] = useState([]);
  const [recentExams, setRecentExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        // Fetch all needed data
        const [statsRes, subjectsRes, examsRes] = await Promise.all([
          api.get('/dashboard/stats'),
          api.get('/subjects/'),
          api.get('/exams/')
        ]);
        
        setStats(statsRes.data);

        setRecentSubjects(subjectsRes.data.slice(-5).reverse());
        setRecentExams(examsRes.data.slice(-5).reverse());
      } catch (err) {
        setError('Unable to load dashboard statistics.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  if (loading) {
    return <div className="p-8 text-center text-slate-500">Loading dashboard...</div>;
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-800">Welcome, {user?.name || 'Professor'}</h1>
        <p className="text-slate-500 mt-1">Here is the overview of your evaluation system.</p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-xl border border-red-100 flex items-center">
          <AlertCircle className="w-5 h-5 mr-2" /> {error}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <p className="text-sm font-medium text-slate-500">Total Subjects</p>
          <p className="text-2xl font-bold text-slate-800 mt-1">{stats.subjects}</p>
        </div>
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <p className="text-sm font-medium text-slate-500">Total Assessments</p>
          <p className="text-2xl font-bold text-slate-800 mt-1">{stats.exams}</p>
        </div>
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <p className="text-sm font-medium text-slate-500">Total Students</p>
          <p className="text-2xl font-bold text-slate-800 mt-1">{stats.students}</p>
        </div>
        <div className="bg-amber-50 p-6 rounded-2xl shadow-sm border border-amber-100">
          <p className="text-sm font-medium text-amber-700">Pending</p>
          <p className="text-2xl font-bold text-amber-800 mt-1">{stats.pending}</p>
        </div>
        <div className="bg-blue-50 p-6 rounded-2xl shadow-sm border border-blue-100">
          <p className="text-sm font-medium text-blue-700">Completed</p>
          <p className="text-2xl font-bold text-blue-800 mt-1">{stats.completed}</p>
        </div>
        <div className="bg-emerald-50 p-6 rounded-2xl shadow-sm border border-emerald-100">
          <p className="text-sm font-medium text-emerald-700">Approved</p>
          <p className="text-2xl font-bold text-emerald-800 mt-1">{stats.approved}</p>
        </div>
      </div>

      {/* Reports & Analytics Quick Access Card */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-indigo-950 rounded-2xl p-6 text-white shadow-md flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/30 text-blue-200 border border-blue-400/30">
              Interactive Analytics
            </span>
            <span className="text-xs text-slate-300">Live Evaluation Tracking</span>
          </div>
          <h3 className="text-xl font-bold">Reports & Evaluation Status Breakdown</h3>
          <p className="text-sm text-slate-300 max-w-2xl">
            Track student evaluations with interactive pie charts, see whose final marks are published, and view a real-time roster of students who still need grading or review.
          </p>
        </div>

        <Link
          to="/professor/reports"
          className="inline-flex items-center px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-semibold shadow-sm transition-all shrink-0"
        >
          <BarChart3 className="w-4 h-4 mr-2" />
          View Reports & Charts
        </Link>
      </div>

      <div className="mt-8">
        <div className="flex justify-between items-center mb-6 border-b border-slate-200 pb-2">
          <h2 className="text-2xl font-bold text-slate-800">My Subjects</h2>
          <Link to="/professor/subjects" className="text-sm font-medium text-blue-600 hover:underline">Manage Subjects</Link>
        </div>
        
        {recentSubjects.length === 0 ? (
          <div className="bg-white p-12 rounded-2xl shadow-sm border border-slate-200 text-center">
             <BookOpen className="w-12 h-12 text-slate-300 mx-auto mb-4" />
             <h3 className="text-lg font-medium text-slate-800 mb-1">No subjects found</h3>
             <p className="text-slate-500 mb-4">You haven't created any subjects yet.</p>
             <Link to="/professor/subjects" className="inline-flex items-center px-4 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-700 transition-colors">
               Create Subject
             </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {recentSubjects.map(sub => {
              // Calculate number of exams for this subject
              // Assuming recentExams has all exams from api.get('/exams/') which it might if not paginated.
              // We'll filter based on subject_id. If exams API doesn't return all, this count might be partial,
              // but typically we'd have a subject.exams_count. For now we use what we have.
              const subjectExamsCount = recentExams.filter(e => e.subject_id === sub.id).length;
              
              return (
                <div key={sub.id} className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col">
                  <div className="mb-4">
                    <h3 className="text-xl font-bold text-slate-800">{sub.name}</h3>
                    <p className="text-slate-500">Course Code: {sub.code}</p>
                    <p className="text-slate-500">Class: {sub.class_section || sub.department}</p>
                  </div>
                  
                  <div className="text-sm font-medium text-slate-700 mb-6 bg-slate-50 inline-block px-3 py-1 rounded-md border border-slate-100 self-start">
                    {subjectExamsCount} Assessment{subjectExamsCount !== 1 ? 's' : ''}
                  </div>
                  
                  <div className="mt-auto flex space-x-3">
                    <Link 
                      to={`/professor/subjects/${sub.id}/exams`}
                      className="flex-1 py-2 px-4 bg-slate-100 text-slate-800 text-center rounded-lg hover:bg-slate-200 transition-colors font-medium text-sm"
                    >
                      View Subject
                    </Link>
                    <Link 
                      to={`/professor/subjects/${sub.id}/exams?create=true`}
                      className="flex-1 py-2 px-4 bg-slate-800 text-white text-center rounded-lg hover:bg-slate-700 transition-colors font-medium text-sm"
                    >
                      Create Assessment
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Quick Access - Evaluation, Results, Reports */}
      <div className="mt-8">
        <div className="flex justify-between items-center mb-6 border-b border-slate-200 pb-2">
          <h2 className="text-2xl font-bold text-slate-800">Workflow</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-blue-100 flex flex-col">
            <div className="p-3 bg-blue-50 rounded-xl w-fit mb-4">
              <PlayCircle className="w-7 h-7 text-blue-600" />
            </div>
            <h3 className="text-lg font-bold text-slate-800 mb-1">Evaluation</h3>
            <p className="text-slate-500 text-sm mb-6">Monitor and manage answer-sheet evaluation for each assessment.</p>
            <div className="mt-auto">
              <Link to="/professor/evaluations" className="block w-full py-2 px-4 bg-blue-600 text-white text-center rounded-lg hover:bg-blue-700 transition-colors font-medium text-sm">
                View Evaluation
              </Link>
            </div>
          </div>

          <div className="bg-white p-6 rounded-2xl shadow-sm border border-emerald-100 flex flex-col">
            <div className="p-3 bg-emerald-50 rounded-xl w-fit mb-4">
              <CheckCircle2 className="w-7 h-7 text-emerald-600" />
            </div>
            <h3 className="text-lg font-bold text-slate-800 mb-1">Results</h3>
            <p className="text-slate-500 text-sm mb-6">View evaluated student marks and results by subject and assessment.</p>
            <div className="mt-auto">
              <Link to="/professor/results" className="block w-full py-2 px-4 bg-emerald-600 text-white text-center rounded-lg hover:bg-emerald-700 transition-colors font-medium text-sm">
                View Results
              </Link>
            </div>
          </div>

          <div className="bg-white p-6 rounded-2xl shadow-sm border border-purple-100 flex flex-col">
            <div className="p-3 bg-purple-50 rounded-xl w-fit mb-4">
              <BarChart3 className="w-7 h-7 text-purple-600" />
            </div>
            <h3 className="text-lg font-bold text-slate-800 mb-1">Reports & Analysis</h3>
            <p className="text-slate-500 text-sm mb-6">View performance reports and analytics for each assessment.</p>
            <div className="mt-auto">
              <Link to="/professor/reports" className="block w-full py-2 px-4 bg-purple-600 text-white text-center rounded-lg hover:bg-purple-700 transition-colors font-medium text-sm">
                View Reports & Analysis
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfessorDashboard;
