import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { BookOpen, FileText, Users } from 'lucide-react';
import api from '../api/axios';
import { Link } from 'react-router-dom';

const ProfessorDashboard = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState({ subjects: 0, exams: 0, students: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [subjectsRes, examsRes, studentsRes] = await Promise.all([
          api.get('/subjects/'),
          api.get('/exams/'),
          api.get('/students/')
        ]);
        
        setStats({
          subjects: subjectsRes.data.length,
          exams: examsRes.data.length,
          students: studentsRes.data.length
        });
      } catch (err) {
        setError('Unable to load dashboard statistics.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-800">Welcome, {user?.name || 'Professor'}</h1>
        <p className="text-slate-500 mt-1">Here is the overview of your evaluation system.</p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-xl border border-red-100">
          {error}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex items-center">
          <div className="p-4 bg-blue-50 text-blue-600 rounded-xl mr-4">
            <BookOpen className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-500">Total Subjects</p>
            <p className="text-2xl font-bold text-slate-800">
              {loading ? '...' : stats.subjects}
            </p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex items-center">
          <div className="p-4 bg-purple-50 text-purple-600 rounded-xl mr-4">
            <FileText className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-500">Your Exams</p>
            <p className="text-2xl font-bold text-slate-800">
              {loading ? '...' : stats.exams}
            </p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex items-center">
          <div className="p-4 bg-emerald-50 text-emerald-600 rounded-xl mr-4">
            <Users className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-500">Total Students</p>
            <p className="text-2xl font-bold text-slate-800">
              {loading ? '...' : `${stats.students}+`}
            </p>
          </div>
        </div>
      </div>

      {/* Quick Links / Actions */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-bold text-slate-800 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Link to="/professor/subjects" className="p-4 border border-slate-100 rounded-xl hover:bg-slate-50 transition-colors flex items-center">
            <div className="w-10 h-10 bg-slate-100 text-slate-600 rounded-lg flex items-center justify-center mr-4">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <p className="font-medium text-slate-800">Manage Subjects</p>
              <p className="text-sm text-slate-500">View or create new subjects</p>
            </div>
          </Link>
          <Link to="/professor/students" className="p-4 border border-slate-100 rounded-xl hover:bg-slate-50 transition-colors flex items-center">
            <div className="w-10 h-10 bg-slate-100 text-slate-600 rounded-lg flex items-center justify-center mr-4">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <p className="font-medium text-slate-800">View Students</p>
              <p className="text-sm text-slate-500">Browse the student directory</p>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default ProfessorDashboard;
