import React, { useState, useEffect } from 'react';
import api from '../api/axios';
import { FileText, CheckCircle2, AlertCircle, PlayCircle, BookOpen } from 'lucide-react';
import { Link } from 'react-router-dom';

const Evaluations = () => {
  const [subjects, setSubjects] = useState([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState('');
  const [assessments, setAssessments] = useState([]);
  const [selectedAssessmentId, setSelectedAssessmentId] = useState('');

  const [loadingData, setLoadingData] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [results, setResults] = useState([]);
  const [evaluations, setEvaluations] = useState([]);

  useEffect(() => {
    fetchSubjects();
  }, []);

  useEffect(() => {
    if (selectedSubjectId) {
      fetchAssessments(selectedSubjectId);
      setSelectedAssessmentId('');
      clearData();
    } else {
      setAssessments([]);
      setSelectedAssessmentId('');
      clearData();
    }
  }, [selectedSubjectId]);

  useEffect(() => {
    if (selectedAssessmentId) {
      fetchAssessmentData(selectedAssessmentId);
    } else {
      clearData();
    }
  }, [selectedAssessmentId]);

  const fetchSubjects = async () => {
    try {
      const res = await api.get('/subjects/');
      setSubjects(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchAssessments = async (subjectId) => {
    try {
      const res = await api.get(`/subjects/${subjectId}/exams`);
      setAssessments(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchAssessmentData = async (examId) => {
    try {
      setLoadingData(true);
      const [docsRes, resultsRes, evalsRes] = await Promise.all([
        api.get(`/exams/${examId}/documents`).catch(() => ({ data: [] })),
        api.get(`/exams/${examId}/results`).catch(() => ({ data: [] })),
        api.get(`/exams/${examId}/evaluations`).catch(() => ({ data: { evaluations: [] } }))
      ]);
      setDocuments(docsRes.data || []);
      setResults(resultsRes.data || []);
      setEvaluations(evalsRes.data?.evaluations || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingData(false);
    }
  };

  const clearData = () => {
    setDocuments([]);
    setResults([]);
    setEvaluations([]);
  };

  const hasDoc = (type) => documents.some(d => d.document_type === type);
  const hasQP = hasDoc('question_paper');
  const hasMA = hasDoc('model_answer');
  const hasMR = hasDoc('marks_rubric');
  const hasScripts = results.length > 0;
  const isMasterDocsReady = hasQP && hasMA && hasMR;
  
  // Evaluation logic
  const evaluatedScriptsCount = results.filter(r => r.status === 'COMPLETED' || evaluations.some(e => e.student_roll_number === r.roll_number)).length;
  const allEvaluated = hasScripts && evaluatedScriptsCount === results.length;
  const partialEvaluated = hasScripts && evaluatedScriptsCount > 0 && evaluatedScriptsCount < results.length;
  
  const renderEmptyState = () => {
    if (!selectedSubjectId || !selectedAssessmentId) {
      return (
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-slate-200 text-center">
          <BookOpen className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-slate-800 mb-1">Select an Assessment</h3>
          <p className="text-slate-500">Please select a subject and assessment above to view evaluation status.</p>
        </div>
      );
    }

    if (loadingData) {
      return (
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-slate-200 text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-500">Loading evaluation data...</p>
        </div>
      );
    }

    if (allEvaluated) {
      return (
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-emerald-200 text-center">
          <CheckCircle2 className="w-16 h-16 text-emerald-500 mx-auto mb-4" />
          <h3 className="text-2xl font-bold text-slate-800 mb-2">Evaluation Completed</h3>
          <p className="text-slate-600 mb-6">All {results.length} student answer sheets have been evaluated.</p>
          <div className="flex justify-center space-x-4">
            <Link to="/professor/results" className="px-6 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-700 font-medium">
              View Results
            </Link>
            <Link to="/professor/reports" className="px-6 py-2 bg-slate-100 text-slate-800 rounded-lg hover:bg-slate-200 font-medium">
              View Reports & Analysis
            </Link>
          </div>
        </div>
      );
    }

    if (partialEvaluated) {
      return (
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-blue-200 text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <h3 className="text-2xl font-bold text-slate-800 mb-2">Evaluation in Progress</h3>
          <p className="text-slate-600 mb-2">AI is currently evaluating student answer sheets.</p>
          <p className="text-sm font-medium text-blue-600 mb-6">{evaluatedScriptsCount} of {results.length} evaluated</p>
          <p className="text-slate-500 text-sm">Please wait while the evaluation is being completed or check individual status in Exam Details.</p>
        </div>
      );
    }

    if (isMasterDocsReady && hasScripts && !partialEvaluated && !allEvaluated) {
      return (
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-blue-200 text-center">
          <PlayCircle className="w-16 h-16 text-blue-500 mx-auto mb-4" />
          <h3 className="text-2xl font-bold text-slate-800 mb-2">Ready for Evaluation</h3>
          <p className="text-slate-600 mb-6">All required documents have been uploaded.</p>
          <Link to={`/professor/exams/${selectedAssessmentId}`} className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium inline-block">
            Start AI Evaluation
          </Link>
        </div>
      );
    }

    return (
      <div className="bg-white p-12 rounded-2xl shadow-sm border border-amber-200 text-center">
        <AlertCircle className="w-16 h-16 text-amber-500 mx-auto mb-4" />
        <h3 className="text-2xl font-bold text-slate-800 mb-2">Evaluation Pending</h3>
        <p className="text-slate-600 mb-6">Waiting for professor to upload the required evaluation documents.</p>
        
        <div className="max-w-xs mx-auto text-left bg-slate-50 p-4 rounded-xl border border-slate-200 mb-6">
          <ul className="space-y-2 text-sm font-medium">
            <li className={`flex items-center ${hasQP ? 'text-emerald-700' : 'text-slate-500'}`}>
              {hasQP ? <CheckCircle2 className="w-4 h-4 mr-2" /> : <span className="w-4 h-4 mr-2 text-center text-slate-400">✗</span>} Question Paper
            </li>
            <li className={`flex items-center ${hasMA ? 'text-emerald-700' : 'text-slate-500'}`}>
              {hasMA ? <CheckCircle2 className="w-4 h-4 mr-2" /> : <span className="w-4 h-4 mr-2 text-center text-slate-400">✗</span>} Model Answer
            </li>
            <li className={`flex items-center ${hasMR ? 'text-emerald-700' : 'text-slate-500'}`}>
              {hasMR ? <CheckCircle2 className="w-4 h-4 mr-2" /> : <span className="w-4 h-4 mr-2 text-center text-slate-400">✗</span>} Marking Rubric
            </li>
            <li className={`flex items-center ${hasScripts ? 'text-emerald-700' : 'text-slate-500'}`}>
              {hasScripts ? <CheckCircle2 className="w-4 h-4 mr-2" /> : <span className="w-4 h-4 mr-2 text-center text-slate-400">✗</span>} Student Answer Sheets
            </li>
          </ul>
        </div>
        
        <Link to={`/professor/exams/${selectedAssessmentId}`} className="text-blue-600 hover:underline font-medium">
          Upload Documents
        </Link>
      </div>
    );
  };

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-800">Evaluation</h1>
        <p className="text-slate-500 mt-1">Monitor and manage answer-sheet evaluation.</p>
      </div>

      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 mb-8 flex flex-col md:flex-row gap-4">
        <div className="flex-1">
          <label className="block text-sm font-medium text-slate-700 mb-1">Subject:</label>
          <select 
            value={selectedSubjectId} 
            onChange={(e) => setSelectedSubjectId(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="">-- Select Subject --</option>
            {subjects.map(s => (
              <option key={s.id} value={s.id}>{s.name} ({s.code}) - {s.class_section || s.department}</option>
            ))}
          </select>
        </div>
        <div className="flex-1">
          <label className="block text-sm font-medium text-slate-700 mb-1">Assessment:</label>
          <select 
            value={selectedAssessmentId} 
            onChange={(e) => setSelectedAssessmentId(e.target.value)}
            disabled={!selectedSubjectId || assessments.length === 0}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white disabled:bg-slate-50"
          >
            <option value="">-- Select Assessment --</option>
            {assessments.map(a => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </div>
      </div>

      {renderEmptyState()}
    </div>
  );
};

export default Evaluations;
