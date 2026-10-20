import React, { useState, useEffect } from 'react';
import api from '../api/axios.jsx';
import { BookOpen, FileText, CheckCircle2, Eye, Download, X, AlertCircle } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';

const StudentResults = () => {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedResult, setSelectedResult] = useState(null);

  const [showViewer, setShowViewer] = useState(false);
  const [viewerUrl, setViewerUrl] = useState('');
  const [viewerTitle, setViewerTitle] = useState('');

  const fetchResults = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/students/me/results');
      setResults(res.data || []);
    } catch (err) {
      setError('Unable to load results. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchResults(); }, []);

  const openDocumentViewer = async (examId, answerScriptId, type) => {
    try {
      if (type === 'answer_script') {
        setViewerUrl(`${API_BASE}/answer-scripts/${answerScriptId}/download`);
        setViewerTitle('My Answer Sheet');
      } else {
        const res = await api.get(`/exams/${examId}/documents`);
        const doc = res.data.find(d => d.document_type === type);
        if (!doc) {
          alert('Document not found or not published yet.');
          return;
        }
        setViewerUrl(`${API_BASE}/exams/${examId}/documents/${doc.id}/download`);
        setViewerTitle(type === 'question_paper' ? 'Question Paper' : 'Model Answer');
      }
      setShowViewer(true);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to open document.');
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-slate-800">My Results</h1>
          <p className="text-slate-500 mt-1">View your examination results and AI feedback.</p>
        </div>
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-slate-200 text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-500">Loading results...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {showViewer && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-5xl h-[90vh] rounded-2xl flex flex-col shadow-2xl overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
              <h3 className="font-bold text-lg text-slate-800">{viewerTitle}</h3>
              <div className="flex items-center gap-4">
                <a href={viewerUrl} target="_blank" rel="noreferrer" className="flex items-center text-sm font-medium text-blue-600 hover:text-blue-800">
                  <Download className="w-4 h-4 mr-1" /> Open in New Tab
                </a>
                <button onClick={() => setShowViewer(false)} className="text-slate-400 hover:text-slate-600">
                  <X className="w-6 h-6" />
                </button>
              </div>
            </div>
            <div className="flex-1 bg-slate-100 p-4">
              <iframe src={viewerUrl} className="w-full h-full rounded border border-slate-200 shadow-inner" title={viewerTitle} />
            </div>
          </div>
        </div>
      )}

      {!selectedResult ? (
        <>
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-slate-800">My Results</h1>
            <p className="text-slate-500 mt-1">View your examination results and AI feedback.</p>
          </div>

          {error ? (
            <div className="bg-white p-12 rounded-2xl shadow-sm border border-red-200 text-center">
              <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
              <p className="text-red-600 mb-4">{error}</p>
              <button onClick={fetchResults} className="px-4 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-700 text-sm font-medium">Retry</button>
            </div>
          ) : results.length === 0 ? (
            <div className="bg-white p-12 rounded-2xl shadow-sm border border-slate-200 text-center">
              <BookOpen className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-800 mb-1">No Results Available Yet</h3>
              <p className="text-slate-500 max-w-sm mx-auto">Results will appear here after your professor completes the evaluation.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {results.map((result, idx) => (
                <div key={idx}
                  className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 hover:border-blue-300 transition-all cursor-pointer group"
                  onClick={() => setSelectedResult(result)}>
                  <div className="flex flex-col md:flex-row justify-between md:items-center gap-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-bold px-2 py-1 rounded bg-blue-50 text-blue-700 uppercase tracking-wider">{result.course_code}</span>
                        <span className={`text-xs font-bold px-2 py-1 rounded uppercase tracking-wider ${result.status === 'COMPLETED' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>
                          {result.status === 'COMPLETED' ? 'Evaluated' : (result.status || 'Pending').replace('_', ' ')}
                        </span>
                      </div>
                      <h3 className="text-xl font-bold text-slate-800 group-hover:text-blue-600 transition-colors">{result.exam_name}</h3>
                      <p className="text-sm text-slate-500 mt-1">{result.subject}</p>
                    </div>
                    {result.status === 'COMPLETED' ? (
                      <div className="text-right">
                        <div className="text-3xl font-black text-emerald-600">
                          {result.total_marks} <span className="text-lg text-slate-400 font-medium">/ {result.maximum_marks}</span>
                        </div>
                        <p className="text-sm font-bold text-slate-500">{result.percentage}%</p>
                      </div>
                    ) : (
                      <div className="text-right">
                        <div className="text-lg font-medium text-slate-500 italic">Result Pending</div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        <div className="space-y-6">
          <button onClick={() => setSelectedResult(null)} className="flex items-center text-sm font-medium text-slate-500 hover:text-slate-800 transition-colors">
            ← Back to all results
          </button>

          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="p-8 border-b border-slate-100 bg-slate-50 text-center">
              <h2 className="text-2xl font-bold text-slate-800 mb-2">{selectedResult.exam_name}</h2>
              <p className="text-slate-500 mb-6">{selectedResult.subject} ({selectedResult.course_code})</p>
              {selectedResult.status === 'COMPLETED' ? (
                <div className="inline-flex flex-col items-center justify-center p-6 bg-white rounded-2xl shadow-sm border border-emerald-100">
                  <span className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-1">Final Score</span>
                  <div className="text-5xl font-black text-emerald-600 mb-1">
                    {selectedResult.total_marks} <span className="text-2xl text-slate-300">/ {selectedResult.maximum_marks}</span>
                  </div>
                  <span className="text-emerald-600 font-medium bg-emerald-50 px-3 py-1 rounded-full">{selectedResult.percentage}%</span>
                </div>
              ) : (
                <div className="inline-flex items-center p-4 bg-amber-50 text-amber-700 rounded-xl border border-amber-100">
                  Result is currently pending. Detailed feedback is not yet available.
                </div>
              )}
            </div>

            {selectedResult.status === 'COMPLETED' && (
              <div className="p-6 bg-slate-50 border-b border-slate-200 flex flex-wrap gap-4 justify-center">
                <button onClick={() => openDocumentViewer(selectedResult.exam_id, null, 'question_paper')}
                  className="flex items-center px-4 py-2 bg-white border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 shadow-sm">
                  <FileText className="w-4 h-4 mr-2 text-slate-400" /> View Question Paper
                </button>
                <button onClick={() => openDocumentViewer(selectedResult.exam_id, selectedResult.answer_script_id, 'answer_script')}
                  className="flex items-center px-4 py-2 bg-blue-600 border border-transparent rounded-lg text-sm font-medium text-white hover:bg-blue-700 shadow-sm">
                  <Eye className="w-4 h-4 mr-2" /> View My Answer Sheet
                </button>
                <button onClick={() => openDocumentViewer(selectedResult.exam_id, null, 'model_answer')}
                  className="flex items-center px-4 py-2 bg-white border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 shadow-sm">
                  <CheckCircle2 className="w-4 h-4 mr-2 text-emerald-500" /> View Model Answer
                </button>
              </div>
            )}

            {selectedResult.status === 'COMPLETED' && selectedResult.questions?.length > 0 && (
              <div className="p-8">
                <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center">
                  <FileText className="w-5 h-5 mr-2 text-blue-500" /> Question-wise Feedback
                </h3>
                <div className="space-y-6">
                  {selectedResult.questions.map((q, idx) => (
                    <div key={idx} className="border border-slate-200 rounded-xl overflow-hidden">
                      <div className="bg-slate-50 px-6 py-4 flex justify-between items-center border-b border-slate-200">
                        <h4 className="font-bold text-slate-800 text-lg">Question {q.question_number}</h4>
                        <div className="text-right">
                          <span className="text-2xl font-black text-emerald-600">{q.final_marks}</span>
                          <span className="text-slate-400 font-medium"> / {q.maximum_marks}</span>
                        </div>
                      </div>
                      <div className="p-6 space-y-4">
                        {q.ai_feedback && (
                          <div>
                            <h5 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">AI Feedback</h5>
                            <div className="bg-blue-50/50 text-slate-700 p-4 rounded-xl border border-blue-100 whitespace-pre-wrap">{q.ai_feedback}</div>
                          </div>
                        )}
                        {q.professor_remarks && (
                          <div>
                            <h5 className="text-xs font-bold text-amber-600 uppercase tracking-wider mb-2">Professor Remarks</h5>
                            <div className="bg-amber-50 text-slate-800 p-4 rounded-xl border border-amber-100">{q.professor_remarks}</div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default StudentResults;
