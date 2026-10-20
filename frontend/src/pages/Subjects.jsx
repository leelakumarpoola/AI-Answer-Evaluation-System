import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/axios';
import { BookOpen, Plus, ChevronRight } from 'lucide-react';

const Subjects = () => {
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ name: '', code: '', department: '', class_section: '' });
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState(null);

  useEffect(() => {
    fetchSubjects();
  }, []);

  const fetchSubjects = async () => {
    try {
      setLoading(true);
      const response = await api.get('/subjects/');
      setSubjects(response.data);
    } catch (err) {
      setError('Unable to load subjects.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setFormError(null);
    setFormLoading(true);
    try {
      const response = await api.post('/subjects/', formData);
      setSubjects([...subjects, response.data]);
      setShowForm(false);
      setFormData({ name: '', code: '', department: '', class_section: '' });
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Unable to create subject.');
    } finally {
      setFormLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-800">My Subjects</h1>
          <p className="text-slate-500 mt-1">Manage and view all registered subjects.</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center px-4 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-700 transition-colors font-medium"
        >
          <Plus className="w-5 h-5 mr-2" />
          Create Subject
        </button>
      </div>

      {showForm && (
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 mb-8">
          <h2 className="text-lg font-bold text-slate-800 mb-4">Create New Subject</h2>
          {formError && (
            <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-md border border-red-100 whitespace-pre-wrap">
              {formError}
            </div>
          )}
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Subject Name</label>
                <input 
                  type="text" 
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  placeholder="e.g. Artificial Intelligence"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Course Code</label>
                <input 
                  type="text" 
                  required
                  value={formData.code}
                  onChange={(e) => setFormData({...formData, code: e.target.value})}
                  placeholder="e.g. BCSE304L"
                  pattern="^BCSE[0-9]{3}L$"
                  title="Must match format: BCSE###L"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Class/Section</label>
                <input 
                  type="text" 
                  required
                  value={formData.class_section}
                  onChange={(e) => setFormData({...formData, class_section: e.target.value})}
                  placeholder="e.g. CSE-A"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Department</label>
                <input 
                  type="text" 
                  required
                  value={formData.department}
                  onChange={(e) => setFormData({...formData, department: e.target.value})}
                  placeholder="e.g. Computer Science"
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
                {formLoading ? 'Saving...' : 'Save Subject'}
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

      {loading ? (
        <div className="text-center py-12 text-slate-500">Loading subjects...</div>
      ) : subjects.length === 0 ? (
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-slate-200 text-center">
          <BookOpen className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-slate-800 mb-1">No subjects found</h3>
          <p className="text-slate-500">Get started by creating your first subject.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {subjects.map(subject => (
            <div key={subject.id} className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 hover:shadow-md transition-shadow flex flex-col">
              <div className="flex-1 mb-6">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-xl font-bold text-slate-800">{subject.name}</h3>
                  <span className="inline-block px-3 py-1 bg-slate-100 text-slate-700 text-sm font-semibold rounded-full">
                    {subject.code}
                  </span>
                </div>
                <p className="text-slate-500">Class: {subject.class_section}</p>
                <p className="text-slate-500 text-sm">{subject.department}</p>
              </div>
              <div className="flex space-x-3">
                <Link 
                  to={`/professor/subjects/${subject.id}/exams`}
                  className="flex-1 flex items-center justify-center py-2.5 bg-slate-50 text-slate-700 hover:bg-slate-100 hover:text-slate-900 border border-slate-200 rounded-xl font-medium transition-colors"
                >
                  View Subject
                </Link>
                <Link 
                  to={`/professor/subjects/${subject.id}/exams?create=true`}
                  className="flex-1 flex items-center justify-center py-2.5 bg-slate-800 text-white hover:bg-slate-700 border border-slate-800 rounded-xl font-medium transition-colors"
                >
                  Create Assessment
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Subjects;
