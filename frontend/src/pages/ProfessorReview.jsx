import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api/axios';
import { ChevronLeft, CheckCircle2, AlertCircle, Save } from 'lucide-react';

const ProfessorReview = () => {
  const { examId, studentId } = useParams();
  const [evaluations, setEvaluations] = useState([]);
  const [reviewPackages, setReviewPackages] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Form states per evaluation
  const [marks, setMarks] = useState({});
  const [remarks, setRemarks] = useState({});
  const [saving, setSaving] = useState({});

  useEffect(() => {
    fetchData();
  }, [examId, studentId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      // Fetch all evaluations for this exam
      const evalsRes = await api.get(`/exams/${examId}/evaluations`);
      
      // We need the student's roll number to filter. Let's fetch the student info.
      const studentRes = await api.get(`/students/${studentId}`);
      const rollNo = studentRes.data.roll_number;

      const studentEvals = evalsRes.data.evaluations.filter(e => e.student_roll_number === rollNo);
      setEvaluations(studentEvals);

      // Now fetch Full Review Package for each evaluation
      const packages = {};
      const initialMarks = {};
      const initialRemarks = {};

      for (let ev of studentEvals) {
        const pkgRes = await api.get(`/evaluations/${ev.evaluation_id}/review`);
        packages[ev.evaluation_id] = pkgRes.data;
        
        initialMarks[ev.evaluation_id] = pkgRes.data.professor_review.final_marks !== null 
          ? pkgRes.data.professor_review.final_marks 
          : pkgRes.data.ai_evaluation.ai_suggested_marks;
          
        initialRemarks[ev.evaluation_id] = pkgRes.data.professor_review.professor_remarks || '';
      }

      setReviewPackages(packages);
      setMarks(initialMarks);
      setRemarks(initialRemarks);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load review data');
    } finally {
      setLoading(false);
    }
  };

  const [globalError, setGlobalError] = useState(null);
  const [globalSuccess, setGlobalSuccess] = useState(null);

  const showError = (msg) => {
    setGlobalError(msg);
    setTimeout(() => setGlobalError(null), 5000);
  };

  const showSuccess = (msg) => {
    setGlobalSuccess(msg);
    setTimeout(() => setGlobalSuccess(null), 5000);
  };

  const handleSave = async (evalId) => {
    setSaving(prev => ({ ...prev, [evalId]: true }));
    try {
      await api.patch(`/evaluations/${evalId}/review`, {
        final_marks: parseFloat(marks[evalId]),
        professor_remarks: remarks[evalId]
      });
      showSuccess('Review updated successfully.');
      fetchData(); // Refresh to reflect status changes
    } catch (err) {
      showError(err.response?.data?.detail || 'Failed to update review.');
    } finally {
      setSaving(prev => ({ ...prev, [evalId]: false }));
    }
  };

  const handleApprove = async (evalId) => {
    try {
      await api.post(`/evaluations/${evalId}/approve`);
      showSuccess('Evaluation approved and locked.');
      fetchData();
    } catch (err) {
      showError(err.response?.data?.detail || 'Failed to approve evaluation.');
    }
  };

  if (loading) return <div className="text-center py-12 text-slate-500">Loading student evaluation...</div>;
  if (error) return <div className="max-w-4xl mx-auto p-4 text-red-700 bg-red-50 rounded-xl">{error}</div>;

  return (
    <div className="max-w-5xl mx-auto pb-12">
      <Link to={`/professor/exams/${examId}`} className="inline-flex items-center text-sm font-medium text-slate-500 hover:text-slate-800 mb-6 transition-colors">
        <ChevronLeft className="w-4 h-4 mr-1" />
        Back to Exam Details
      </Link>

      {globalError && (
        <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-xl border border-red-100 flex items-center">
          <AlertCircle className="w-5 h-5 mr-2" /> {globalError}
        </div>
      )}

      {globalSuccess && (
        <div className="mb-6 p-4 bg-emerald-50 text-emerald-700 rounded-xl border border-emerald-100 flex items-center">
          <CheckCircle2 className="w-5 h-5 mr-2" /> {globalSuccess}
        </div>
      )}

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-800">Student Evaluation Review</h1>
        <p className="text-slate-500 mt-1">Review AI evaluations, override marks, and provide feedback.</p>
      </div>

      {evaluations.length === 0 ? (
        <div className="bg-white p-8 rounded-2xl shadow-sm text-center border border-slate-200 text-slate-500">
          No evaluations found for this student. Please run the AI evaluation first.
        </div>
      ) : (
        <div className="space-y-8">
          {evaluations.map(ev => {
            const pkg = reviewPackages[ev.evaluation_id];
            if (!pkg) return null;

            const isApproved = pkg.professor_review.review_status === 'approved';

            return (
              <div key={ev.evaluation_id} className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
                <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50">
                  <h2 className="text-xl font-bold text-slate-800">
                    Question {pkg.question_info.question_number}
                  </h2>
                  <div className="flex items-center gap-4">
                    <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${isApproved ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`}>
                      {pkg.professor_review.review_status.replace('_', ' ')}
                    </span>
                  </div>
                </div>

                <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-8">
                  {/* Left Column: Context & Feedback */}
                  <div className="space-y-6">
                    <div>
                      <h3 className="text-sm font-bold text-slate-500 uppercase mb-2">Question Text</h3>
                      <p className="text-slate-800 bg-slate-50 p-4 rounded-xl border border-slate-100">
                        {pkg.question_info.question_text}
                      </p>
                    </div>
                    
                    <div>
                      <h3 className="text-sm font-bold text-slate-500 uppercase mb-2">Student Answer</h3>
                      <p className="text-slate-800 bg-blue-50 p-4 rounded-xl border border-blue-100 whitespace-pre-wrap">
                        {pkg.student_answer_info.extracted_text}
                      </p>
                    </div>

                    <div>
                      <h3 className="text-sm font-bold text-slate-500 uppercase mb-2">Model Answer</h3>
                      <p className="text-slate-800 bg-slate-50 p-4 rounded-xl border border-slate-100 whitespace-pre-wrap">
                        {pkg.model_answer_info.extracted_text || 'No explicit model answer text matched.'}
                      </p>
                    </div>

                    <div>
                      <h3 className="text-sm font-bold text-slate-500 uppercase mb-2">AI Feedback</h3>
                      <div className="text-slate-700 bg-emerald-50 p-4 rounded-xl border border-emerald-100">
                        {pkg.ai_evaluation.ai_feedback || 'No feedback generated.'}
                      </div>
                    </div>
                  </div>

                  {/* Right Column: Marks & Override */}
                  <div className="space-y-6">
                    <div className="bg-slate-50 p-6 rounded-xl border border-slate-200">
                      <div className="flex justify-between items-center mb-6">
                        <span className="text-slate-600 font-medium">Maximum Marks</span>
                        <span className="text-xl font-bold text-slate-800">{pkg.question_info.max_marks}</span>
                      </div>
                      <div className="flex justify-between items-center mb-6">
                        <span className="text-slate-600 font-medium">AI Suggested Marks</span>
                        <span className="text-xl font-bold text-blue-600">{pkg.ai_evaluation.ai_suggested_marks}</span>
                      </div>
                      
                      <hr className="border-slate-200 mb-6" />

                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm font-bold text-slate-700 mb-2">
                            Final Awarded Marks
                          </label>
                          <input 
                            type="number"
                            step="0.5"
                            min="0"
                            max={pkg.question_info.max_marks}
                            value={marks[ev.evaluation_id] ?? ''}
                            onChange={(e) => setMarks(prev => ({ ...prev, [ev.evaluation_id]: e.target.value }))}
                            disabled={isApproved}
                            className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-100 disabled:text-slate-500 font-bold text-lg"
                          />
                        </div>
                        
                        <div>
                          <label className="block text-sm font-bold text-slate-700 mb-2">
                            Professor Remarks (Optional)
                          </label>
                          <textarea 
                            rows={3}
                            value={remarks[ev.evaluation_id] ?? ''}
                            onChange={(e) => setRemarks(prev => ({ ...prev, [ev.evaluation_id]: e.target.value }))}
                            disabled={isApproved}
                            placeholder="Add your manual review notes here..."
                            className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-100 disabled:text-slate-500"
                          />
                        </div>

                        {!isApproved && (
                          <div className="flex gap-4 pt-4">
                            <button 
                              onClick={() => handleSave(ev.evaluation_id)}
                              disabled={saving[ev.evaluation_id]}
                              className="flex-1 bg-white text-slate-700 border border-slate-300 font-medium py-2 rounded-lg hover:bg-slate-50 disabled:opacity-50 flex justify-center items-center"
                            >
                              <Save className="w-4 h-4 mr-2" /> 
                              {saving[ev.evaluation_id] ? 'Saving...' : 'Save Draft'}
                            </button>
                            <button 
                              onClick={() => handleApprove(ev.evaluation_id)}
                              className="flex-1 bg-emerald-600 text-white font-medium py-2 rounded-lg hover:bg-emerald-700 transition-colors flex justify-center items-center"
                            >
                              <CheckCircle2 className="w-4 h-4 mr-2" /> Approve Final
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ProfessorReview;
