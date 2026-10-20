import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api/axios.jsx';
import {
  ChevronLeft, FileText, BookOpen, CheckCircle2, Clock,
  AlertCircle, Eye, X, ExternalLink
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';
const token = () => localStorage.getItem('access_token');

// Status helpers
const StatusBadge = ({ status }) => {
  const map = {
    COMPLETED:      { label: 'Evaluated',         cls: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
    PENDING_REVIEW: { label: 'Under Review',       cls: 'bg-blue-100 text-blue-700 border-blue-200' },
    PENDING:        { label: 'Evaluation Pending', cls: 'bg-amber-100 text-amber-700 border-amber-200' },
    NOT_SUBMITTED:  { label: 'Not Submitted',      cls: 'bg-slate-100 text-slate-600 border-slate-200' },
  };
  const s = map[status] || { label: status || 'Pending', cls: 'bg-slate-100 text-slate-600 border-slate-200' };
  return (
    <span className={`inline-block text-xs font-bold px-3 py-1 rounded-full border ${s.cls}`}>
      {s.label}
    </span>
  );
};

// Inline PDF viewer modal
const DocumentViewer = ({ url, title, onClose }) => (
  <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
    <div className="bg-white w-full max-w-5xl h-[92vh] rounded-2xl flex flex-col shadow-2xl overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50 shrink-0">
        <h3 className="font-bold text-lg text-slate-800">{title}</h3>
        <div className="flex items-center gap-3">
          <a href={url} target="_blank" rel="noreferrer"
            className="flex items-center text-sm font-medium text-blue-600 hover:text-blue-800 transition-colors">
            <ExternalLink className="w-4 h-4 mr-1" /> Open in New Tab
          </a>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 transition-colors">
            <X className="w-6 h-6" />
          </button>
        </div>
      </div>
      <div className="flex-1 bg-slate-100 p-3 overflow-hidden">
        <iframe
          src={url}
          className="w-full h-full rounded border border-slate-200 shadow-inner"
          title={title}
        />
      </div>
    </div>
  </div>
);

// Single document card with availability check
const DocumentCard = ({ title, description, icon: Icon, iconColor, available, availableMsg, unavailableMsg, onView }) => (
  <div className={`rounded-xl border p-5 flex flex-col ${available ? 'border-slate-200 bg-white' : 'border-slate-100 bg-slate-50'}`}>
    <div className="flex items-center gap-3 mb-3">
      <div className={`p-2 rounded-lg ${available ? iconColor : 'bg-slate-100'}`}>
        <Icon className={`w-5 h-5 ${available ? 'text-white' : 'text-slate-400'}`} />
      </div>
      <h4 className="font-bold text-slate-800">{title}</h4>
    </div>
    <p className="text-xs text-slate-500 mb-4 flex-1">{description}</p>

    {available ? (
      <div>
        <div className="flex items-center gap-1.5 text-emerald-700 text-xs font-semibold mb-3">
          <CheckCircle2 className="w-3.5 h-3.5" /> {availableMsg}
        </div>
        <button
          onClick={onView}
          className="w-full py-2 px-4 bg-slate-800 text-white rounded-lg text-sm font-semibold hover:bg-slate-700 transition-colors flex items-center justify-center gap-2"
        >
          <Eye className="w-4 h-4" /> View {title}
        </button>
      </div>
    ) : (
      <div className="flex items-center gap-1.5 text-slate-400 text-xs font-medium">
        <Clock className="w-3.5 h-3.5" /> {unavailableMsg}
      </div>
    )}
  </div>
);

const StudentExamDetail = () => {
  const { examId } = useParams();

  const [examInfo, setExamInfo] = useState(null);
  const [result, setResult] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [answerScript, setAnswerScript] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Viewer
  const [viewer, setViewer] = useState(null); // { url, title }

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch exam info (accessible by students via get_current_user)
      const examRes = await api.get(`/exams/${examId}`);
      setExamInfo(examRes.data);

      // Fetch documents for this exam (backend checks student has answer script)
      const docsRes = await api.get(`/exams/${examId}/documents`).catch(() => ({ data: [] }));
      setDocuments(docsRes.data || []);

      // Fetch the student's answer script for this exam
      const myExamsRes = await api.get('/students/me/exams');
      const myExam = (myExamsRes.data || []).find(e => String(e.exam_id) === String(examId));
      if (myExam) {
        setAnswerScript({ id: myExam.answer_script_id });
        // Set result from my exams endpoint
        if (myExam.status === 'COMPLETED') {
          setResult({
            total_marks: myExam.score,
            maximum_marks: myExam.maximum_marks,
            percentage: myExam.percentage,
            status: myExam.status,
          });
        } else {
          setResult({ status: myExam.status, total_marks: null, maximum_marks: myExam.maximum_marks });
        }
      }

      // Try to get detailed result with question-wise breakdown
      try {
        const detailRes = await api.get(`/students/me/results`);
        const detail = (detailRes.data || []).find(r => String(r.exam_id) === String(examId));
        if (detail) setResult(detail);
      } catch (_) {}

    } catch (err) {
      setError('Unable to load exam details. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [examId]);

  const getDoc = (type) => documents.find(d => d.document_type === type);

  const openDoc = (doc) => {
    if (!doc) return;
    const url = `${API_BASE}/exams/${examId}/documents/${doc.id}/download`;
    setViewer({ url, title: doc.document_type === 'question_paper' ? 'Question Paper' : 'Model Answer' });
  };

  const openScript = () => {
    if (!answerScript) return;
    const url = `${API_BASE}/answer-scripts/${answerScript.id}/download`;
    setViewer({ url, title: 'My Answer Sheet' });
  };

  const qpDoc   = getDoc('question_paper');
  const maDoc   = getDoc('model_answer');
  const hasScript = !!answerScript;

  const subject = examInfo?.subject;
  const isEvaluated = result?.status === 'COMPLETED';
  const examTotalMarks = examInfo?.total_marks;

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-slate-200 text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-500">Loading exam details...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-red-200 text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-slate-800 mb-2">Unable to Load Exam</h3>
          <p className="text-slate-500 mb-4">{error}</p>
          <button onClick={fetchData} className="px-4 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-700 text-sm font-medium">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Document Viewer Modal */}
      {viewer && <DocumentViewer url={viewer.url} title={viewer.title} onClose={() => setViewer(null)} />}

      {/* Back button */}
      <Link to="/student/dashboard" className="inline-flex items-center text-sm font-medium text-slate-500 hover:text-slate-800 transition-colors">
        <ChevronLeft className="w-4 h-4 mr-1" /> Back to Dashboard
      </Link>

      {/* Exam Header */}
      <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-200">
        <div className="flex flex-col md:flex-row justify-between md:items-start gap-4">
          <div>
            {subject && (
              <div className="flex items-center gap-2 mb-3">
                <BookOpen className="w-4 h-4 text-slate-400" />
                <span className="font-semibold text-slate-700">{subject.name}</span>
                <span className="text-slate-400">·</span>
                <span className="font-mono text-sm text-slate-500">{subject.code}</span>
              </div>
            )}
            <h1 className="text-2xl font-bold text-slate-800 mb-1">{examInfo?.name}</h1>
            {examInfo?.exam_type && (
              <p className="text-sm text-slate-500">{examInfo.exam_type}</p>
            )}
          </div>
          <div className="text-right shrink-0">
            <p className="text-xs text-slate-500 uppercase font-semibold tracking-wide mb-1">Maximum Marks</p>
            <p className="text-3xl font-black text-slate-800">{examTotalMarks || '—'}</p>
          </div>
        </div>

        <hr className="my-6 border-slate-100" />

        {/* Score section */}
        <div className="flex flex-wrap items-center gap-6">
          <div>
            <p className="text-xs text-slate-500 uppercase font-semibold tracking-wide mb-1">Your Score</p>
            {isEvaluated ? (
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-black text-emerald-600">{result.total_marks}</span>
                <span className="text-lg text-slate-400 font-medium">/ {result.maximum_marks || examTotalMarks || '—'}</span>
                {result.percentage != null && (
                  <span className="text-sm font-bold text-emerald-600 bg-emerald-100 px-3 py-1 rounded-full">
                    {result.percentage}%
                  </span>
                )}
              </div>
            ) : (
              <p className="text-lg font-semibold text-amber-600 italic">Pending</p>
            )}
          </div>
          <div>
            <p className="text-xs text-slate-500 uppercase font-semibold tracking-wide mb-2">Status</p>
            <StatusBadge status={result?.status} />
          </div>
        </div>
      </div>

      {/* Documents Section */}
      <div>
        <h2 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
          <FileText className="w-5 h-5 text-blue-600" />
          Exam Documents
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <DocumentCard
            title="Question Paper"
            description="Uploaded by your professor for this assessment."
            icon={FileText}
            iconColor="bg-blue-600"
            available={!!qpDoc}
            availableMsg="Available"
            unavailableMsg="Not uploaded yet by professor"
            onView={() => openDoc(qpDoc)}
          />
          <DocumentCard
            title="Model Answer"
            description="Reference answer uploaded by your professor."
            icon={CheckCircle2}
            iconColor="bg-emerald-600"
            available={!!maDoc}
            availableMsg="Available"
            unavailableMsg="Not available yet"
            onView={() => openDoc(maDoc)}
          />
          <DocumentCard
            title="My Answer Sheet"
            description="Your submitted answer sheet for evaluation."
            icon={Eye}
            iconColor="bg-purple-600"
            available={hasScript}
            availableMsg="Your answer sheet on file"
            unavailableMsg="Not uploaded yet"
            onView={openScript}
          />
        </div>
      </div>

      {/* Evaluation Feedback (if evaluated with question-wise breakdown) */}
      {isEvaluated && result?.questions && result.questions.length > 0 && (
        <div>
          <h2 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            Question-wise Evaluation
          </h2>
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="p-4 bg-slate-50 border-b border-slate-200 flex justify-between items-center">
              <span className="text-sm font-semibold text-slate-600">Question Breakdown</span>
              <span className="text-sm font-bold text-slate-800">
                Total: {result.total_marks} / {result.maximum_marks || examTotalMarks}
              </span>
            </div>
            <div className="divide-y divide-slate-100">
              {result.questions.map((q, idx) => (
                <div key={idx} className="p-5">
                  <div className="flex justify-between items-start mb-2">
                    <span className="font-bold text-slate-800">Question {q.question_number}</span>
                    <div className="text-right">
                      {q.final_marks != null ? (
                        <span className="text-lg font-black text-emerald-600">
                          {q.final_marks} <span className="text-sm text-slate-400 font-medium">/ {q.maximum_marks}</span>
                        </span>
                      ) : (
                        <span className="text-sm text-amber-600 font-medium italic">Pending</span>
                      )}
                    </div>
                  </div>
                  {/* Progress bar */}
                  {q.final_marks != null && q.maximum_marks > 0 && (
                    <div className="w-full bg-slate-100 rounded-full h-2 mb-3 overflow-hidden">
                      <div
                        className="bg-emerald-500 h-2 rounded-full"
                        style={{ width: `${Math.round((q.final_marks / q.maximum_marks) * 100)}%` }}
                      />
                    </div>
                  )}
                  {q.ai_feedback && (
                    <div className="mt-3">
                      <p className="text-xs font-bold text-slate-400 uppercase tracking-wide mb-1">AI Feedback</p>
                      <p className="text-sm text-slate-700 bg-blue-50 border border-blue-100 rounded-lg p-3 whitespace-pre-wrap">
                        {q.ai_feedback}
                      </p>
                    </div>
                  )}
                  {q.professor_remarks && (
                    <div className="mt-2">
                      <p className="text-xs font-bold text-amber-600 uppercase tracking-wide mb-1">Professor Remarks</p>
                      <p className="text-sm text-slate-700 bg-amber-50 border border-amber-100 rounded-lg p-3">
                        {q.professor_remarks}
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Pending evaluation notice */}
      {!isEvaluated && (
        <div className="bg-amber-50 border border-amber-100 rounded-2xl p-6 flex items-start gap-4">
          <Clock className="w-6 h-6 text-amber-500 shrink-0 mt-0.5" />
          <div>
            <h3 className="font-bold text-amber-800 mb-1">Evaluation Not Yet Completed</h3>
            <p className="text-sm text-amber-700">
              Your answer sheet has been received. The AI evaluation and professor review are in progress.
              Your score and detailed feedback will appear here once the evaluation is completed.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default StudentExamDetail;
