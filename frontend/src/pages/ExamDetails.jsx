import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api/axios';
import { 
  ChevronLeft, FileText, Calendar, Clock, BookOpen, AlertCircle, 
  UploadCloud, CheckCircle2, PlayCircle, Users, Eye, Edit3
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const ExamDetails = () => {
  const { examId } = useParams();
  const [exam, setExam] = useState(null);
  const [subject, setSubject] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [students, setStudents] = useState([]);
  const [scriptResults, setScriptResults] = useState([]);
  const [evaluations, setEvaluations] = useState([]);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [uploadingDoc, setUploadingDoc] = useState(null);
  const [uploadStatus, setUploadStatus] = useState({});
  const [processingMaster, setProcessingMaster] = useState(false);

  const [scriptUploadingFor, setScriptUploadingFor] = useState(null);
  const [evaluatingScript, setEvaluatingScript] = useState(null);

  const { user } = useAuth();

  useEffect(() => {
    fetchExamData();
  }, [examId]);

  const fetchExamData = async () => {
    try {
      setLoading(true);
      const examRes = await api.get(`/exams/${examId}`);
      setExam(examRes.data);
      
      const [subjectRes, docsRes, studentsRes, resultsRes, evalsRes] = await Promise.all([
        api.get(`/subjects/${examRes.data.subject_id}`),
        api.get(`/exams/${examId}/documents`),
        api.get(`/students/`),
        api.get(`/exams/${examId}/results`).catch(() => ({ data: [] })),
        api.get(`/exams/${examId}/evaluations`).catch(() => ({ data: { evaluations: [] } }))
      ]);
      
      setSubject(subjectRes.data);
      setDocuments(docsRes.data);
      setStudents(studentsRes.data);
      setScriptResults(resultsRes.data || []);
      setEvaluations(evalsRes.data?.evaluations || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load exam details.');
    } finally {
      setLoading(false);
    }
  };

  const handleDocumentUpload = async (docType, e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploadingDoc(docType);
    setUploadStatus({ ...uploadStatus, [docType]: null });

    const formData = new FormData();
    formData.append('document_type', docType);
    formData.append('file', file);

    try {
      await api.post(`/exams/${examId}/documents/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setUploadStatus({ ...uploadStatus, [docType]: { type: 'success', message: 'Uploaded successfully' } });
      const docsRes = await api.get(`/exams/${examId}/documents`);
      setDocuments(docsRes.data);
    } catch (err) {
      setUploadStatus({ 
        ...uploadStatus, 
        [docType]: { type: 'error', message: err.response?.data?.detail || 'Upload failed' } 
      });
    } finally {
      setUploadingDoc(null);
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

  const processMasterDocuments = async () => {
    setProcessingMaster(true);
    try {
      const qp = documents.find(d => d.document_type === 'question_paper');
      const ma = documents.find(d => d.document_type === 'model_answer');
      const mr = documents.find(d => d.document_type === 'marks_rubric');

      if (!qp || !ma || !mr) {
        showError('Please upload Question Paper, Model Answer, and Marks Rubric first.');
        return;
      }

      for (let doc of [qp, ma, mr]) {
        await api.post(`/exams/${examId}/documents/${doc.id}/process`);
        await api.post(`/exams/${examId}/documents/${doc.id}/ocr`);
        await api.post(`/exams/${examId}/documents/${doc.id}/extract`);
      }
      showSuccess('Master documents processed successfully.');
    } catch (err) {
      showError(err.response?.data?.detail || 'Failed to process master documents. Server may be unavailable.');
    } finally {
      setProcessingMaster(false);
    }
  };

  const handleScriptUpload = async (studentId, e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) { // 10MB limit
      showError('File size exceeds the allowed limit (10MB).');
      return;
    }

    setScriptUploadingFor(studentId);
    const formData = new FormData();
    formData.append('file', file);

    try {
      await api.post(`/exams/${examId}/students/${studentId}/answer-script`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      showSuccess('Student answer script uploaded successfully.');
      fetchExamData();
    } catch (err) {
      showError(err.response?.data?.detail || 'Failed to upload answer script. Ensure the file is a valid PDF.');
    } finally {
      setScriptUploadingFor(null);
    }
  };

  const startEvaluation = async (answerScriptId) => {
    setEvaluatingScript(answerScriptId);
    try {
      await api.post(`/answer-scripts/${answerScriptId}/process`);
      await api.post(`/answer-scripts/${answerScriptId}/ocr`);
      await api.post(`/answer-scripts/${answerScriptId}/extract-answers`);
      await api.post(`/answer-scripts/${answerScriptId}/semantic-similarity`);
      await api.post(`/answer-scripts/${answerScriptId}/rubric-evaluation`);
      await api.post(`/answer-scripts/${answerScriptId}/feedback`);
      
      showSuccess('AI Evaluation completed successfully.');
      fetchExamData();
    } catch (err) {
      showError(err.response?.data?.detail || 'Evaluation pipeline failed. Please try again.');
    } finally {
      setEvaluatingScript(null);
    }
  };

  const hasDoc = (type) => documents.some(d => d.document_type === type);
  const masterDocsReady = hasDoc('question_paper') && hasDoc('model_answer') && hasDoc('marks_rubric');

  if (loading) return <div className="text-center py-12 text-slate-500">Loading evaluation workflow...</div>;
  if (error) return (
    <div className="max-w-5xl mx-auto p-4 bg-red-50 text-red-700 rounded-xl border border-red-100">{error}</div>
  );

  return (
    <div className="max-w-6xl mx-auto pb-12">
      <Link to={`/professor/subjects/${exam.subject_id}/exams`} className="inline-flex items-center text-sm font-medium text-slate-500 hover:text-slate-800 mb-6 transition-colors">
        <ChevronLeft className="w-4 h-4 mr-1" />
        Back to Exams
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

      <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-200 mb-8">
        <div className="flex justify-between items-start border-b border-slate-100 pb-6 mb-6">
          <div>
            <h1 className="text-3xl font-bold text-slate-800 mb-2">{exam.name}</h1>
            <div className="flex items-center text-slate-600">
              <BookOpen className="w-4 h-4 mr-2" />
              <span className="font-medium">{subject?.name}</span>
            </div>
          </div>
          <div className="text-right">
            <span className="inline-block px-4 py-1.5 bg-blue-50 text-blue-700 text-sm font-bold rounded-full border border-blue-100 mb-2">
              {exam.exam_type}
            </span>
            <p className="text-sm font-medium text-slate-500">
              Max Marks: <span className="text-slate-800 font-bold text-lg">{exam.total_marks}</span>
            </p>
          </div>
        </div>
      </div>

      <div className="mb-8">
        <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center">
          <FileText className="w-5 h-5 mr-2 text-blue-600" />
          Master Documents
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-4">
          {['question_paper', 'model_answer', 'marks_rubric'].map(docType => {
            const uploaded = hasDoc(docType);
            const isUploading = uploadingDoc === docType;
            const labels = {
              question_paper: 'Question Paper',
              model_answer: 'Model Answer',
              marks_rubric: 'Marks Rubric'
            };

            return (
              <div key={docType} className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col">
                <div className="flex justify-between items-center mb-4">
                  <span className="font-bold text-slate-800">{labels[docType]}</span>
                  {uploaded ? (
                    <span className="flex items-center text-xs text-emerald-700 font-bold bg-emerald-50 px-2 py-1 rounded-md">
                      <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Uploaded
                    </span>
                  ) : (
                    <span className="text-xs text-amber-600 font-bold bg-amber-50 px-2 py-1 rounded-md">Missing</span>
                  )}
                </div>
                
                <div className="mt-auto pt-4 border-t border-slate-100">
                  <label className="cursor-pointer w-full flex justify-center items-center px-4 py-2 border border-slate-300 shadow-sm text-sm font-medium rounded-lg text-slate-700 bg-white hover:bg-slate-50 transition-colors">
                    <UploadCloud className="w-4 h-4 mr-2 text-slate-500" />
                    {isUploading ? 'Uploading...' : (uploaded ? 'Replace PDF' : 'Upload PDF')}
                    <input type="file" accept="application/pdf" className="hidden" onChange={(e) => handleDocumentUpload(docType, e)} disabled={isUploading} />
                  </label>
                </div>
              </div>
            );
          })}
        </div>
        
        {masterDocsReady && (
          <div className="bg-blue-50 border border-blue-100 p-4 rounded-xl flex items-center justify-between">
            <div className="flex items-center text-blue-800 text-sm font-medium">
              <CheckCircle2 className="w-5 h-5 mr-2 text-blue-600" />
              All master documents uploaded. Ready for processing.
            </div>
            <button 
              onClick={processMasterDocuments}
              disabled={processingMaster}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-bold hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center"
            >
              {processingMaster ? 'Processing...' : 'Process Documents'}
            </button>
          </div>
        )}
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden mb-8">
        <div className="p-6 border-b border-slate-100">
          <h2 className="text-xl font-bold text-slate-800 flex items-center">
            <Users className="w-5 h-5 mr-2 text-purple-600" />
            Student Answer Sheets & Evaluation
          </h2>
          {!masterDocsReady && (
            <div className="mt-4 flex items-start p-4 bg-amber-50 text-amber-800 rounded-xl text-sm font-medium border border-amber-100">
              <AlertCircle className="w-5 h-5 mr-2 shrink-0 text-amber-600" />
              Evaluation cannot be started. Please ensure Question Paper, Model Answer, and Marks Rubric are uploaded.
            </div>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Student</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Answer Sheet</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {students.map((student) => {
                const scriptRes = scriptResults.find(r => r.roll_number === student.roll_number);
                const hasScript = !!scriptRes;
                const isUploading = scriptUploadingFor === student.id;
                
                // Determine AI evaluation status
                // A script is AI evaluated if it has entries in the evaluations array
                const studentEvals = evaluations.filter(e => e.student_roll_number === student.roll_number);
                const isEvaluated = studentEvals.length > 0;
                const isEvaluating = evaluatingScript === (scriptRes?.answer_script_id);
                
                return (
                  <tr key={student.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="font-bold text-slate-800">{student.roll_number}</div>
                      <div className="text-sm text-slate-500">{student.name}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {hasScript ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
                          ✓ Uploaded
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
                          ⚠ Missing
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {isEvaluating ? (
                        <span className="text-sm font-bold text-blue-600 flex items-center">
                          <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mr-2"></div>
                          Processing AI...
                        </span>
                      ) : isEvaluated ? (
                        <span className="text-sm font-bold text-emerald-600">
                          {scriptRes?.status === 'COMPLETED' ? 'Review Approved' : 'AI Evaluated'}
                        </span>
                      ) : hasScript ? (
                        <span className="text-sm font-bold text-amber-600">Pending Evaluation</span>
                      ) : (
                        <span className="text-sm text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      {!hasScript ? (
                        <label className="cursor-pointer inline-flex items-center px-3 py-1.5 border border-slate-300 rounded-md text-slate-700 bg-white hover:bg-slate-50">
                          <UploadCloud className="w-4 h-4 mr-1.5 text-slate-500" />
                          {isUploading ? 'Uploading...' : 'Upload Script'}
                          <input type="file" accept="application/pdf" className="hidden" onChange={(e) => handleScriptUpload(student.id, e)} disabled={isUploading} />
                        </label>
                      ) : !isEvaluated ? (
                        <button 
                          onClick={() => startEvaluation(scriptRes.answer_script_id)}
                          disabled={!masterDocsReady || isEvaluating}
                          className="inline-flex items-center px-4 py-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                        >
                          <PlayCircle className="w-4 h-4 mr-1.5" /> Start AI Evaluation
                        </button>
                      ) : (
                        <Link 
                          to={`/professor/exams/${examId}/review/${student.id}`}
                          className="inline-flex items-center px-4 py-1.5 bg-slate-800 text-white rounded-md hover:bg-slate-700"
                        >
                          <Eye className="w-4 h-4 mr-1.5" /> View Results
                        </Link>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ExamDetails;
