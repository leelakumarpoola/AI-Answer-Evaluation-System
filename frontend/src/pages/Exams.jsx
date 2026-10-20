import React, { useState, useEffect } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import api from '../api/axios';
import { FileText, Plus, ChevronLeft, Calendar, Clock } from 'lucide-react';

const Exams = () => {
  const { subjectId } = useParams();
  const location = useLocation();
  const [subject, setSubject] = useState(null);
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    exam_type: 'Internal Assessment',
    exam_date: '',
    total_marks: 50,
    duration_minutes: 120
  });
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState(null);

  useEffect(() => {
    // Check if we should show the create form automatically
    const queryParams = new URLSearchParams(location.search);
    if (queryParams.get('create') === 'true') {
      setShowForm(true);
    }
  }, [location.search]);

  useEffect(() => {
    fetchData();
  }, [subjectId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [subjectRes, examsRes] = await Promise.all([
        api.get(`/subjects/${subjectId}`),
        api.get(`/subjects/${subjectId}/exams`)
      ]);
      setSubject(subjectRes.data);
      setExams(examsRes.data);
    } catch (err) {
      setError('Unable to load exams for this subject.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setFormError(null);
    setFormLoading(true);
    try {
      const payload = {
        name: formData.name,
        exam_type: formData.exam_type,
        subject_id: parseInt(subjectId),
        exam_date: formData.exam_date || null,
        total_marks: parseInt(formData.total_marks),
        duration_minutes: parseInt(formData.duration_minutes) || null
      };

      const response = await api.post('/exams/', payload);
      setExams([...exams, response.data]);
      setShowForm(false);
      setFormData({
        name: '',
        exam_type: 'Internal Assessment',
        exam_date: '',
        total_marks: 50,
        duration_minutes: 120
      });
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Unable to create assessment.');
    } finally {
      setFormLoading(false);
    }
  };

  if (loading) {
    return <div className="text-center py-12 text-slate-500">Loading...</div>;
  }

  return (
    <div className="max-w-5xl mx-auto">
      <Link to="/professor/dashboard" className="inline-flex items-center text-sm font-medium text-slate-500 hover:text-slate-800 mb-6 transition-colors">
        <ChevronLeft className="w-4 h-4 mr-1" />
        Back to Dashboard
      </Link>

      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4 bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
        <div>
          <h1 className="text-3xl font-bold text-slate-800 mb-2">
            {subject ? subject.name : 'Subject Details'}
          </h1>
          {subject && (
            <div className="text-slate-600 font-medium flex flex-wrap gap-x-4 gap-y-2">
              <span>Course Code: {subject.code}</span>
              <span>Class: {subject.class_section || subject.department}</span>
            </div>
          )}
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center px-4 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-700 transition-colors font-medium whitespace-nowrap"
        >
          <Plus className="w-5 h-5 mr-2" />
          Create Assessment
        </button>
      </div>

      {showForm && (
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 mb-8">
          <h2 className="text-lg font-bold text-slate-800 mb-4">Create New Assessment</h2>
          {formError && (
            <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-md border border-red-100">
              {formError}
            </div>
          )}
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">Assessment Name</label>
                <input 
                  type="text" 
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  placeholder="e.g. Internal Assessment 1"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Assessment Type</label>
                <select 
                  required
                  value={formData.exam_type}
                  onChange={(e) => setFormData({...formData, exam_type: e.target.value})}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 bg-white"
                >
                  <option value="Internal Assessment">Internal Assessment</option>
                  <option value="Terminal Examination">Terminal Examination</option>
                  <option value="Assignment">Assignment</option>
                  <option value="Quiz">Quiz</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Total Marks</label>
                <input 
                  type="number" 
                  required
                  min="1"
                  value={formData.total_marks}
                  onChange={(e) => setFormData({...formData, total_marks: e.target.value})}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Assessment Date (Optional)</label>
                <input 
                  type="date" 
                  value={formData.exam_date}
                  onChange={(e) => setFormData({...formData, exam_date: e.target.value})}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Duration (Minutes, Optional)</label>
                <input 
                  type="number" 
                  min="1"
                  value={formData.duration_minutes}
                  onChange={(e) => setFormData({...formData, duration_minutes: e.target.value})}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500"
                />
              </div>
            </div>
            <div className="flex justify-end space-x-3 pt-2">
              <button 
                type="button" 
                onClick={() => setShowForm(false)}
                className="px-4 py-2 text-slate-600 font-medium hover:bg-slate-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button 
                type="submit" 
                disabled={formLoading}
                className="px-6 py-2 bg-slate-800 text-white font-medium rounded-lg hover:bg-slate-700 disabled:opacity-50 transition-colors"
              >
                {formLoading ? 'Saving...' : 'Save Assessment'}
              </button>
            </div>
          </form>
        </div>
      )}

      {error && (
        <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-xl border border-red-100">
          {error}
        </div>
      )}

      {exams.length === 0 && !error ? (
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-slate-200 text-center">
          <FileText className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-slate-800 mb-1">No assessments created yet</h3>
          <p className="text-slate-500">Create an assessment to begin processing answer scripts.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {exams.map(exam => (
            <div key={exam.id} className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-xl font-bold text-slate-800">{exam.name}</h3>
                  <p className="text-sm text-slate-500 mt-1">Type: <span className="font-medium text-slate-700">{exam.exam_type}</span></p>
                </div>
                <div className="bg-emerald-50 text-emerald-700 px-3 py-1 rounded-lg text-sm font-bold border border-emerald-100">
                  {exam.total_marks} Marks
                </div>
              </div>
              
              <div className="space-y-2 mb-6">
                <div className="flex items-center text-sm text-slate-600">
                  <Calendar className="w-4 h-4 mr-2 text-slate-400" />
                  {exam.exam_date || 'Date not set'}
                </div>
                <div className="flex items-center text-sm text-slate-600">
                  <Clock className="w-4 h-4 mr-2 text-slate-400" />
                  {exam.duration_minutes ? `${exam.duration_minutes} minutes` : 'Duration not set'}
                </div>
              </div>

              <Link 
                to={`/professor/exams/${exam.id}`}
                className="block text-center w-full py-2 bg-slate-50 hover:bg-slate-100 text-slate-800 font-medium rounded-xl border border-slate-200 transition-colors"
              >
                View Assessment Details
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Exams;
