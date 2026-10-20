import React, { useState, useEffect, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api/axios';
import { 
  ChevronLeft, CheckCircle2, AlertCircle, Save, FileText, 
  ExternalLink, User, BookOpen, Award, Check, RefreshCw, AlertTriangle,
  Image as ImageIcon, GitFork, CheckCircle, XCircle, ZoomIn, X
} from 'lucide-react';

const ProfessorReview = () => {
  const { examId, studentId } = useParams();
  const [evaluations, setEvaluations] = useState([]);
  const [reviewPackages, setReviewPackages] = useState({});
  const [student, setStudent] = useState(null);
  const [exam, setExam] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Form states per evaluation
  const [marks, setMarks] = useState({});
  const [remarks, setRemarks] = useState({});
  const [saving, setSaving] = useState({});
  const [savingAll, setSavingAll] = useState(false);
  const [openingPdf, setOpeningPdf] = useState(false);
  const [diagramImages, setDiagramImages] = useState({});
  const [previewModalImg, setPreviewModalImg] = useState(null);

  // Global notification states
  const [globalError, setGlobalError] = useState(null);
  const [globalSuccess, setGlobalSuccess] = useState(null);

  useEffect(() => {
    fetchData();
  }, [examId, studentId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch student details
      const studentRes = await api.get(`/students/${studentId}`).catch(() => null);
      if (studentRes?.data) {
        setStudent(studentRes.data);
      }

      // Fetch exam details
      const examRes = await api.get(`/exams/${examId}`).catch(() => null);
      if (examRes?.data) {
        setExam(examRes.data);
      }

      // Fetch all evaluations for this exam
      const evalsRes = await api.get(`/exams/${examId}/evaluations`);
      const rollNo = studentRes?.data?.roll_number;

      const studentEvals = rollNo 
        ? evalsRes.data.evaluations.filter(e => e.student_roll_number === rollNo)
        : evalsRes.data.evaluations;

      setEvaluations(studentEvals);

      // Fetch Full Review Package for each evaluation
      const packages = {};
      const initialMarks = {};
      const initialRemarks = {};

      for (let ev of studentEvals) {
        try {
          const pkgRes = await api.get(`/evaluations/${ev.evaluation_id}/review`);
          packages[ev.evaluation_id] = pkgRes.data;

          // Preserve any existing user input in form state, otherwise initialize from review
          initialMarks[ev.evaluation_id] = pkgRes.data.professor_review.final_marks !== null 
            ? pkgRes.data.professor_review.final_marks 
            : pkgRes.data.ai_evaluation.ai_suggested_marks;

          initialRemarks[ev.evaluation_id] = pkgRes.data.professor_review.professor_remarks || '';

          // If a diagram was detected and evaluated, fetch its cropped image
          const dEval = pkgRes.data?.diagram_evaluation || pkgRes.data?.ai_evaluation?.diagram_evaluation;
          if (dEval?.diagram_detected) {
            try {
              const imgRes = await api.get(`/evaluations/${ev.evaluation_id}/diagram-image`, {
                responseType: 'blob'
              });
              const imgUrl = URL.createObjectURL(imgRes.data);
              setDiagramImages(prev => ({ ...prev, [ev.evaluation_id]: imgUrl }));
            } catch (imgErr) {
              console.log(`No direct crop file available for evaluation ${ev.evaluation_id}`);
            }
          }
        } catch (pkgErr) {
          console.error(`Error loading review package for eval ${ev.evaluation_id}:`, pkgErr);
        }
      }

      setReviewPackages(packages);
      setMarks(prev => ({ ...initialMarks, ...prev }));
      setRemarks(prev => ({ ...initialRemarks, ...prev }));
    } catch (err) {
      console.error('Failed to load review data:', err);
      setError(err.response?.data?.detail || 'Failed to load review data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const showError = (msg) => {
    setGlobalError(msg);
    setTimeout(() => setGlobalError(null), 6000);
  };

  const showSuccess = (msg) => {
    setGlobalSuccess(msg);
    setTimeout(() => setGlobalSuccess(null), 5000);
  };

  // ─────────────────────────────────────────────────────────────
  // Open Complete Original Student Answer Sheet PDF in Browser Tab
  // ─────────────────────────────────────────────────────────────
  const handleOpenOriginalPdf = async () => {
    try {
      setOpeningPdf(true);
      // Fetch actual raw PDF bytes with Bearer token authentication
      const response = await api.get(`/exams/${examId}/students/${studentId}/answer-script/pdf`, {
        responseType: 'blob'
      });

      const fileBlob = new Blob([response.data], { type: 'application/pdf' });
      const fileURL = URL.createObjectURL(fileBlob);

      // Open complete original PDF in native browser viewer in a new tab
      const pdfWindow = window.open(fileURL, '_blank');
      if (!pdfWindow) {
        showError('Popup blocked by browser. Please enable popups to view the original answer sheet PDF.');
      }
    } catch (err) {
      console.error('Failed to open original answer sheet PDF:', err);
      let errorMsg = 'Failed to open original answer sheet PDF. The file may be missing or inaccessible.';
      if (err.response?.data instanceof Blob) {
        try {
          const text = await err.response.data.text();
          const parsed = JSON.parse(text);
          if (parsed.detail) errorMsg = parsed.detail;
        } catch (_) {}
      } else if (err.response?.data?.detail) {
        errorMsg = err.response.data.detail;
      }
      showError(errorMsg);
    } finally {
      setOpeningPdf(false);
    }
  };

  // ─────────────────────────────────────────────────────────────
  // Save Draft (Updates final marks without locking)
  // ─────────────────────────────────────────────────────────────
  const handleSave = async (evalId) => {
    const rawVal = marks[evalId];
    if (rawVal === '' || isNaN(parseFloat(rawVal))) {
      showError('Please enter a valid numeric mark before saving.');
      return;
    }

    setSaving(prev => ({ ...prev, [evalId]: true }));
    try {
      await api.patch(`/evaluations/${evalId}/review`, {
        final_marks: parseFloat(rawVal),
        professor_remarks: remarks[evalId] || ''
      });
      showSuccess('Marks saved successfully as draft.');
      // Update local review status without clearing in-flight states
      setReviewPackages(prev => {
        if (!prev[evalId]) return prev;
        return {
          ...prev,
          [evalId]: {
            ...prev[evalId],
            professor_review: {
              ...prev[evalId].professor_review,
              final_marks: parseFloat(rawVal),
              professor_remarks: remarks[evalId] || '',
              review_status: 'under_review'
            }
          }
        };
      });
    } catch (err) {
      showError(err.response?.data?.detail || 'Failed to update review marks.');
    } finally {
      setSaving(prev => ({ ...prev, [evalId]: false }));
    }
  };

  // ─────────────────────────────────────────────────────────────
  // Approve Final Marks (Confirms and locks evaluation)
  // ─────────────────────────────────────────────────────────────
  const handleApprove = async (evalId) => {
    const pkg = reviewPackages[evalId];
    const rawVal = marks[evalId];
    if (rawVal === '' || isNaN(parseFloat(rawVal))) {
      showError('Please enter valid final marks before approving.');
      return;
    }

    const qNum = pkg?.question_info?.question_number || '';
    const confirmed = window.confirm(
      `Confirm final marks for Question ${qNum}?\n\nAwarded Marks: ${rawVal} / ${pkg?.question_info?.max_marks || ''}\n\nOnce approved, this question evaluation will be finalized and locked.`
    );
    if (!confirmed) return;

    setSaving(prev => ({ ...prev, [evalId]: true }));
    try {
      // 1. Save latest marks and remarks first
      await api.patch(`/evaluations/${evalId}/review`, {
        final_marks: parseFloat(rawVal),
        professor_remarks: remarks[evalId] || ''
      });
      // 2. Approve and lock
      await api.post(`/evaluations/${evalId}/approve`);
      showSuccess(`Question ${qNum} evaluation approved and locked.`);

      // Update state locally
      setReviewPackages(prev => {
        if (!prev[evalId]) return prev;
        return {
          ...prev,
          [evalId]: {
            ...prev[evalId],
            professor_review: {
              ...prev[evalId].professor_review,
              final_marks: parseFloat(rawVal),
              professor_remarks: remarks[evalId] || '',
              review_status: 'approved'
            }
          }
        };
      });
    } catch (err) {
      showError(err.response?.data?.detail || 'Failed to approve evaluation.');
    } finally {
      setSaving(prev => ({ ...prev, [evalId]: false }));
    }
  };

  // ─────────────────────────────────────────────────────────────
  // Save All Final Marks
  // ─────────────────────────────────────────────────────────────
  const handleSaveAll = async () => {
    setSavingAll(true);
    let successCount = 0;
    try {
      for (let ev of evaluations) {
        const evalId = ev.evaluation_id;
        const val = parseFloat(marks[evalId]);
        if (isNaN(val)) continue;

        await api.patch(`/evaluations/${evalId}/review`, {
          final_marks: val,
          professor_remarks: remarks[evalId] || ''
        });
        successCount++;
      }
      showSuccess(`Successfully saved marks for ${successCount} question(s).`);
      fetchData();
    } catch (err) {
      showError(err.response?.data?.detail || 'Failed to save all marks.');
    } finally {
      setSavingAll(false);
    }
  };

  // ─────────────────────────────────────────────────────────────
  // Dynamic Total Calculations
  // ─────────────────────────────────────────────────────────────
  const totals = useMemo(() => {
    let aiTotal = 0;
    let finalTotal = 0;
    let maxTotal = 0;
    let allApproved = true;

    for (let ev of evaluations) {
      const pkg = reviewPackages[ev.evaluation_id];
      if (pkg) {
        maxTotal += Number(pkg.question_info.max_marks || 0);
        aiTotal += Number(pkg.ai_evaluation.ai_suggested_marks || 0);
        const currentMark = marks[ev.evaluation_id];
        const val = parseFloat(currentMark);
        finalTotal += !isNaN(val) ? val : Number(pkg.ai_evaluation.ai_suggested_marks || 0);

        if (pkg.professor_review.review_status !== 'approved') {
          allApproved = false;
        }
      }
    }

    return {
      aiTotal: Number(aiTotal.toFixed(2)),
      finalTotal: Number(finalTotal.toFixed(2)),
      maxTotal: Number(maxTotal.toFixed(2)),
      allApproved: evaluations.length > 0 && allApproved
    };
  }, [evaluations, reviewPackages, marks]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-slate-500">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mb-3" />
        <span className="font-medium text-slate-700">Loading student evaluation review...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6 text-red-700 bg-red-50 rounded-2xl border border-red-200">
        <h3 className="font-bold text-lg mb-2 flex items-center">
          <AlertCircle className="w-5 h-5 mr-2" /> Error Loading Review
        </h3>
        <p className="text-sm">{error}</p>
        <Link 
          to={`/professor/exams/${examId}`} 
          className="inline-flex items-center mt-4 px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-semibold hover:bg-red-700"
        >
          <ChevronLeft className="w-4 h-4 mr-1" /> Return to Exam Details
        </Link>
      </div>
    );
  }

  // Answer script file info from first available review package
  const firstPkg = Object.values(reviewPackages)[0];
  const scriptFileName = firstPkg?.answer_script_file_name || 'Scanned_Answer_Script.pdf';

  return (
    <div className="max-w-6xl mx-auto pb-16">
      {/* Back Link */}
      <Link 
        to={`/professor/exams/${examId}`} 
        className="inline-flex items-center text-sm font-medium text-slate-500 hover:text-slate-800 mb-6 transition-colors"
      >
        <ChevronLeft className="w-4 h-4 mr-1" />
        Back to Exam Details
      </Link>

      {/* Global Alerts */}
      {globalError && (
        <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-xl border border-red-200 flex items-center shadow-sm animate-fadeIn">
          <AlertCircle className="w-5 h-5 mr-3 shrink-0 text-red-600" /> 
          <span className="font-medium text-sm">{globalError}</span>
        </div>
      )}

      {globalSuccess && (
        <div className="mb-6 p-4 bg-emerald-50 text-emerald-800 rounded-xl border border-emerald-200 flex items-center shadow-sm animate-fadeIn">
          <CheckCircle2 className="w-5 h-5 mr-3 shrink-0 text-emerald-600" /> 
          <span className="font-medium text-sm">{globalSuccess}</span>
        </div>
      )}

      {/* Top Banner: Student Info, Total Marks & View PDF Button */}
      <div className="bg-white p-7 rounded-2xl shadow-sm border border-slate-200 mb-8">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6">
          {/* Student & Exam Info */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-3 py-1 bg-blue-50 text-blue-700 font-bold rounded-lg text-xs uppercase tracking-wider border border-blue-100">
                {student?.roll_number || 'Student'}
              </span>
              <span className="text-slate-400">•</span>
              <span className="text-sm font-medium text-slate-600 flex items-center">
                <BookOpen className="w-3.5 h-3.5 mr-1 text-slate-400" />
                {exam?.name || 'Assessment Review'}
              </span>
            </div>
            <h1 className="text-2xl lg:text-3xl font-bold text-slate-800">
              {student?.name || 'Student Evaluation Review'}
            </h1>
            <p className="text-sm text-slate-500 mt-1 flex items-center gap-3">
              <span>{student?.department}</span>
              {student?.year && <span>• Year {student?.year}</span>}
              {student?.section && <span>• Section {student?.section}</span>}
            </p>
          </div>

          {/* Action Button & Marks Scorecard */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4 w-full lg:w-auto">
            {/* Total Marks Widget */}
            <div className="flex items-center justify-between sm:justify-start gap-4 p-3.5 bg-slate-50 rounded-xl border border-slate-200">
              <div className="text-center px-3 border-r border-slate-200">
                <span className="block text-xs font-semibold text-slate-500 uppercase tracking-wider">AI Total</span>
                <span className="text-lg font-bold text-blue-600">{totals.aiTotal}</span>
              </div>
              <div className="text-center px-3">
                <span className="block text-xs font-semibold text-slate-500 uppercase tracking-wider">Final Total</span>
                <span className="text-xl font-extrabold text-slate-800">
                  {totals.finalTotal}
                  <span className="text-xs font-medium text-slate-400 ml-1">/ {totals.maxTotal}</span>
                </span>
              </div>
            </div>

            {/* Primary Button: View Original Answer Sheet (PDF) */}
            <button
              onClick={handleOpenOriginalPdf}
              disabled={openingPdf}
              id="view-original-answer-sheet-pdf-btn"
              className="inline-flex items-center justify-center px-5 py-3.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow-md hover:shadow-lg transition-all focus:ring-4 focus:ring-indigo-100 disabled:opacity-50 text-sm shrink-0"
              title="Open the complete original scanned answer-sheet PDF in the browser's native PDF viewer"
            >
              <FileText className="w-5 h-5 mr-2 shrink-0" />
              <span>{openingPdf ? 'Opening Original PDF...' : 'View Original Answer Sheet (PDF)'}</span>
              <ExternalLink className="w-4 h-4 ml-2 text-indigo-200 shrink-0" />
            </button>
          </div>
        </div>

        {/* Informative Guidance Banner */}
        <div className="mt-6 pt-5 border-t border-slate-100 flex flex-col sm:flex-row items-start sm:items-center justify-between text-xs text-slate-500 gap-2">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-700">Uploaded Document:</span>
            <span className="font-mono bg-slate-100 px-2 py-0.5 rounded text-slate-600">{scriptFileName}</span>
            <span className="text-emerald-600 font-semibold flex items-center">
              <Check className="w-3.5 h-3.5 mr-0.5" /> Scanned Original PDF
            </span>
          </div>
          <div className="text-slate-400">
            Tip: You can inspect handwritten answers in the PDF tab and return anytime without losing edits.
          </div>
        </div>
      </div>

      {/* Evaluations Content */}
      {evaluations.length === 0 ? (
        <div className="bg-white p-12 rounded-2xl shadow-sm text-center border border-slate-200 text-slate-500">
          <AlertCircle className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-lg font-bold text-slate-700 mb-1">No Evaluations Available</h3>
          <p className="text-sm">No evaluation records found for this student. Please ensure the AI evaluation has been executed.</p>
        </div>
      ) : (
        <div className="space-y-8">
          {evaluations.map((ev, index) => {
            const pkg = reviewPackages[ev.evaluation_id];
            if (!pkg) {
              return (
                <div key={ev.evaluation_id} className="p-6 bg-white rounded-2xl border border-slate-200 animate-pulse text-slate-400">
                  Loading Question {ev.question_number || index + 1} details...
                </div>
              );
            }

            const isApproved = pkg.professor_review.review_status === 'approved';
            const currentMarkVal = marks[ev.evaluation_id] ?? '';
            const maxMarks = pkg.question_info.max_marks;
            const aiSuggested = pkg.ai_evaluation.ai_suggested_marks;
            const hasMarkChanged = currentMarkVal !== '' && parseFloat(currentMarkVal) !== aiSuggested;

            return (
              <div 
                key={ev.evaluation_id} 
                className={`bg-white rounded-2xl shadow-sm border transition-all ${
                  isApproved ? 'border-emerald-200 ring-1 ring-emerald-100' : 'border-slate-200'
                } overflow-hidden`}
              >
                {/* Question Header with Status and View PDF shortcut */}
                <div className="p-6 border-b border-slate-100 flex flex-wrap justify-between items-center bg-slate-50/80 gap-3">
                  <div className="flex items-center gap-3">
                    <span className="w-8 h-8 rounded-lg bg-blue-600 text-white font-bold flex items-center justify-center text-sm">
                      Q{pkg.question_info.question_number}
                    </span>
                    <h2 className="text-lg font-bold text-slate-800">
                      Question {pkg.question_info.question_number} Evaluation
                    </h2>
                  </div>

                  <div className="flex items-center gap-3">
                    {/* View Original Answer Sheet PDF Button near Question */}
                    <button
                      onClick={handleOpenOriginalPdf}
                      disabled={openingPdf}
                      className="inline-flex items-center text-xs font-semibold px-3 py-1.5 rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 transition-colors"
                      title="Inspect student's handwritten answer in original PDF"
                    >
                      <FileText className="w-3.5 h-3.5 mr-1.5 text-indigo-600" />
                      View Original Answer Sheet (PDF)
                      <ExternalLink className="w-3 h-3 ml-1 text-indigo-400" />
                    </button>

                    {/* Status Badge */}
                    <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                      isApproved 
                        ? 'bg-emerald-100 text-emerald-800 border border-emerald-200' 
                        : 'bg-amber-100 text-amber-800 border border-amber-200'
                    }`}>
                      {isApproved ? 'Approved & Locked' : (pkg.professor_review.review_status?.replace('_', ' ') || 'AI Evaluated')}
                    </span>
                  </div>
                </div>

                <div className="p-6 grid grid-cols-1 lg:grid-cols-12 gap-8">
                  {/* Left Column (7 cols): Question Context, OCR Text, Model Answer & Rubric */}
                  <div className="lg:col-span-7 space-y-5">
                    {/* Question Text */}
                    <div>
                      <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                        Question Text
                      </h3>
                      <div className="text-slate-800 bg-slate-50 p-4 rounded-xl border border-slate-200 text-sm leading-relaxed">
                        {pkg.question_info.question_text}
                      </div>
                    </div>

                    {/* Student Extracted Answer with notice */}
                    <div>
                      <div className="flex justify-between items-center mb-2">
                        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                          Extracted Student Answer (OCR Preview)
                        </h3>
                        <span className="text-xs text-indigo-600 font-semibold cursor-pointer hover:underline flex items-center" onClick={handleOpenOriginalPdf}>
                          <FileText className="w-3 h-3 mr-1" /> View Original Handwriting in PDF
                        </span>
                      </div>
                      <div className="text-slate-800 bg-blue-50/50 p-4 rounded-xl border border-blue-100 text-sm leading-relaxed whitespace-pre-wrap max-h-56 overflow-y-auto">
                        {pkg.student_answer_info.answer_text || pkg.student_answer_info.extracted_text || 'No text extracted.'}
                      </div>
                    </div>

                    {/* Model Answer */}
                    <div>
                      <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                        Model Answer / Key Points
                      </h3>
                      <div className="text-slate-700 bg-slate-50 p-4 rounded-xl border border-slate-200 text-sm leading-relaxed whitespace-pre-wrap max-h-48 overflow-y-auto">
                        {pkg.model_answer_info?.answer_text || pkg.model_answer_info?.extracted_text || 'Standard reference answer.'}
                      </div>
                    </div>

                    {/* Intelligent Diagram Recognition & Semantic Evaluation Card */}
                    {(() => {
                      const diag = pkg.diagram_evaluation || pkg.ai_evaluation?.diagram_evaluation;
                      if (!diag || !diag.diagram_detected) return null;

                      const cropSrc = diagramImages[ev.evaluation_id] || diag.diagram_crop_url;

                      return (
                        <div className="bg-gradient-to-br from-indigo-50/50 via-white to-blue-50/30 rounded-xl border border-indigo-200 p-5 shadow-sm space-y-4">
                          {/* Card Header */}
                          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-indigo-100 pb-3">
                            <div className="flex items-center gap-2">
                              <span className="p-1.5 bg-indigo-100 text-indigo-700 rounded-lg">
                                <GitFork className="w-4 h-4" />
                              </span>
                              <div>
                                <h4 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                                  Diagram Recognition & Semantic Evaluation
                                </h4>
                                <span className="text-xs text-slate-500">
                                  Type: <strong className="font-semibold uppercase text-indigo-700">{diag.diagram_type || 'General Diagram'}</strong>
                                  {diag.page_number && ` • Page ${diag.page_number}`}
                                </span>
                              </div>
                            </div>

                            <div className="flex items-center gap-2">
                              <span className="px-2.5 py-1 bg-indigo-100 text-indigo-800 rounded-lg text-xs font-bold">
                                {diag.marks_awarded ?? 0} marks awarded
                              </span>
                            </div>
                          </div>

                          {/* Diagram Crop Image Preview */}
                          {cropSrc && (
                            <div className="relative group bg-white p-2 rounded-xl border border-slate-200 shadow-sm max-w-md">
                              <div 
                                className="relative overflow-hidden rounded-lg bg-slate-50 flex items-center justify-center max-h-64 cursor-pointer"
                                onClick={() => setPreviewModalImg(cropSrc)}
                              >
                                <img 
                                  src={cropSrc} 
                                  alt="Student Cropped Diagram" 
                                  className="object-contain w-full max-h-64 transition-transform duration-200 group-hover:scale-105"
                                />
                                <div className="absolute inset-0 bg-black/30 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity text-white text-xs font-semibold gap-1.5">
                                  <ZoomIn className="w-4 h-4" /> Click to Enlarge Diagram
                                </div>
                              </div>
                              <div className="text-[11px] text-slate-400 mt-1 flex justify-between px-1">
                                <span>Detected Region {diag.bounding_box ? `[${diag.bounding_box.join(', ')}]` : ''}</span>
                                <span className="text-indigo-600 font-medium">Click image to inspect full-res</span>
                              </div>
                            </div>
                          )}

                          {/* Semantic Components & Labels */}
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                            {/* Matching Components */}
                            <div className="bg-white p-3 rounded-lg border border-emerald-100">
                              <span className="font-bold text-emerald-800 flex items-center gap-1 mb-1.5">
                                <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                                Recognized Components ({diag.matching_components?.length || 0})
                              </span>
                              {diag.matching_components && diag.matching_components.length > 0 ? (
                                <div className="flex flex-wrap gap-1.5">
                                  {diag.matching_components.map((comp, idx) => (
                                    <span key={idx} className="px-2 py-0.5 bg-emerald-50 text-emerald-700 font-medium rounded border border-emerald-200">
                                      {comp}
                                    </span>
                                  ))}
                                </div>
                              ) : (
                                <span className="text-slate-400 italic">No standard components identified.</span>
                              )}
                            </div>

                            {/* Missing Components */}
                            <div className="bg-white p-3 rounded-lg border border-amber-100">
                              <span className="font-bold text-amber-800 flex items-center gap-1 mb-1.5">
                                <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                                Missing / Unidentified ({diag.missing_components?.length || 0})
                              </span>
                              {diag.missing_components && diag.missing_components.length > 0 ? (
                                <div className="flex flex-wrap gap-1.5">
                                  {diag.missing_components.map((comp, idx) => (
                                    <span key={idx} className="px-2 py-0.5 bg-amber-50 text-amber-700 font-medium rounded border border-amber-200">
                                      {comp}
                                    </span>
                                  ))}
                                </div>
                              ) : (
                                <span className="text-emerald-600 font-medium">All essential components present.</span>
                              )}
                            </div>
                          </div>

                          {/* Labels & Structural Status Badges */}
                          <div className="flex flex-wrap gap-2 text-xs">
                            <div className="bg-white px-2.5 py-1.5 rounded-lg border border-slate-200 flex items-center gap-1.5 text-slate-700">
                              <span className="font-semibold text-slate-500">Flow/Arrow Score:</span>
                              <span className="font-bold text-indigo-600">{Math.round((diag.arrow_direction_score || 0) * 100)}%</span>
                            </div>
                            <div className="bg-white px-2.5 py-1.5 rounded-lg border border-slate-200 flex items-center gap-1.5 text-slate-700">
                              <span className="font-semibold text-slate-500">Connectivity Score:</span>
                              <span className="font-bold text-indigo-600">{Math.round((diag.connectivity_score || 0) * 100)}%</span>
                            </div>
                            <div className="bg-white px-2.5 py-1.5 rounded-lg border border-slate-200 flex items-center gap-1.5 text-slate-700">
                              <span className="font-semibold text-slate-500">Labels Score:</span>
                              <span className="font-bold text-indigo-600">{Math.round((diag.labels_score || 0) * 100)}%</span>
                            </div>
                          </div>

                          {/* Contradiction Alert if text-diagram conflict */}
                          {diag.has_contradiction && (
                            <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-start gap-2">
                              <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                              <div>
                                <strong className="font-bold">Text-Diagram Inconsistency: </strong>
                                <span>{diag.text_diagram_consistency_note || 'Diagram connectivity conflicts with written response explanation.'}</span>
                              </div>
                            </div>
                          )}

                          {/* Review Flag Alert if drawing ambiguous or unreadable */}
                          {diag.needs_review && (
                            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 flex items-start gap-2">
                              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                              <div>
                                <strong className="font-bold">Human Verification Advised: </strong>
                                <span>Drawing strokes, labels, or connections appear ambiguous or partially unreadable. Baseline partial attempt credit was awarded.</span>
                              </div>
                            </div>
                          )}

                          {/* Evaluation Explanation */}
                          {diag.explanation && (
                            <div className="text-xs text-slate-600 bg-white/80 p-3 rounded-lg border border-slate-200/80 leading-relaxed">
                              <strong className="font-semibold text-slate-700">Visual Reasoning: </strong>
                              {diag.explanation}
                            </div>
                          )}
                        </div>
                      );
                    })()}

                    {/* Criterion Rubric Breakdown if available */}
                    {pkg.ai_evaluation?.criterion_evaluations?.length > 0 && (
                      <div>
                        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                          Rubric Criteria Breakdown
                        </h3>
                        <div className="space-y-2">
                          {pkg.ai_evaluation.criterion_evaluations.map((crit, cIdx) => (
                            <div key={cIdx} className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
                              <div className="flex justify-between font-semibold text-slate-700">
                                <span>{crit.criterion}</span>
                                <span className="text-blue-600 font-bold">{crit.suggested_marks} marks</span>
                              </div>
                              {crit.reason && (
                                <p className="text-slate-500 mt-1 italic">{crit.reason}</p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* AI Feedback */}
                    <div>
                      <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                        AI Detailed Feedback
                      </h3>
                      <div className="text-slate-700 bg-emerald-50/70 p-4 rounded-xl border border-emerald-100 text-sm leading-relaxed">
                        {pkg.ai_evaluation.ai_feedback || 'Conceptual coverage verified.'}
                      </div>
                    </div>
                  </div>

                  {/* Right Column (5 cols): Marks, Overrides & Finalization */}
                  <div className="lg:col-span-5">
                    <div className="bg-slate-50 p-6 rounded-2xl border border-slate-200 sticky top-6">
                      <h3 className="font-bold text-slate-800 text-base mb-4 flex items-center">
                        <Award className="w-4 h-4 mr-2 text-indigo-600" />
                        Marks & Evaluation Decision
                      </h3>

                      {/* Marks Comparison Card */}
                      <div className="grid grid-cols-2 gap-3 mb-5">
                        <div className="bg-white p-3.5 rounded-xl border border-slate-200">
                          <span className="block text-xs font-medium text-slate-500">Max Marks</span>
                          <span className="text-xl font-bold text-slate-800">{maxMarks}</span>
                        </div>
                        <div className="bg-white p-3.5 rounded-xl border border-slate-200">
                          <span className="block text-xs font-medium text-slate-500">AI Suggested</span>
                          <span className="text-xl font-bold text-blue-600">{aiSuggested}</span>
                        </div>
                      </div>

                      {/* Final Marks Input */}
                      <div className="mb-4">
                        <div className="flex justify-between items-center mb-2">
                          <label className="text-sm font-bold text-slate-800">
                            Final Awarded Marks
                          </label>
                          {hasMarkChanged && (
                            <span className="text-xs font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                              Modified from AI ({aiSuggested})
                            </span>
                          )}
                        </div>
                        <div className="relative">
                          <input 
                            type="number"
                            step="0.5"
                            min="0"
                            max={maxMarks}
                            value={currentMarkVal}
                            onChange={(e) => setMarks(prev => ({ ...prev, [ev.evaluation_id]: e.target.value }))}
                            disabled={isApproved || saving[ev.evaluation_id]}
                            className="w-full px-4 py-3 bg-white border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-100 disabled:text-slate-500 font-extrabold text-xl text-slate-800"
                            placeholder="e.g. 8.5"
                          />
                          <span className="absolute right-4 top-3.5 text-sm font-bold text-slate-400">
                            / {maxMarks}
                          </span>
                        </div>
                      </div>

                      {/* Professor Remarks */}
                      <div className="mb-6">
                        <label className="block text-sm font-bold text-slate-700 mb-2">
                          Professor Remarks / Feedback
                        </label>
                        <textarea 
                          rows={3}
                          value={remarks[ev.evaluation_id] ?? ''}
                          onChange={(e) => setRemarks(prev => ({ ...prev, [ev.evaluation_id]: e.target.value }))}
                          disabled={isApproved || saving[ev.evaluation_id]}
                          placeholder="Optional notes explaining any mark adjustment..."
                          className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-100 disabled:text-slate-500 text-sm text-slate-800"
                        />
                      </div>

                      {/* Actions */}
                      <div className="space-y-3 pt-2">
                        {!isApproved ? (
                          <>
                            <div className="flex gap-3">
                              <button 
                                onClick={() => handleSave(ev.evaluation_id)}
                                disabled={saving[ev.evaluation_id]}
                                className="flex-1 bg-white text-slate-700 border border-slate-300 font-semibold py-2.5 px-3 rounded-xl hover:bg-slate-100 transition-colors disabled:opacity-50 flex justify-center items-center text-sm shadow-sm"
                              >
                                <Save className="w-4 h-4 mr-1.5" /> 
                                {saving[ev.evaluation_id] ? 'Saving...' : 'Save Draft'}
                              </button>

                              <button 
                                onClick={() => handleApprove(ev.evaluation_id)}
                                disabled={saving[ev.evaluation_id]}
                                className="flex-1 bg-emerald-600 text-white font-bold py-2.5 px-3 rounded-xl hover:bg-emerald-700 transition-colors shadow-sm flex justify-center items-center text-sm disabled:opacity-50"
                              >
                                <CheckCircle2 className="w-4 h-4 mr-1.5" /> 
                                Save Final Marks
                              </button>
                            </div>

                            <button
                              onClick={handleOpenOriginalPdf}
                              disabled={openingPdf}
                              className="w-full bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 font-semibold py-2 rounded-xl transition-colors flex justify-center items-center text-xs"
                            >
                              <FileText className="w-3.5 h-3.5 mr-1.5" />
                              Inspect Handwriting in Original PDF
                            </button>
                          </>
                        ) : (
                          <div className="p-3 bg-emerald-50 text-emerald-800 rounded-xl border border-emerald-200 text-center text-xs font-semibold flex items-center justify-center">
                            <CheckCircle2 className="w-4 h-4 mr-1.5 text-emerald-600" />
                            Final marks approved and confirmed.
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}

          {/* Bottom Consolidated Action Bar */}
          <div className="p-6 bg-white rounded-2xl shadow-sm border border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4 mt-8">
            <div className="flex items-center gap-4">
              <Award className="w-8 h-8 text-indigo-600" />
              <div>
                <h4 className="font-bold text-slate-800 text-base">Evaluation Summary</h4>
                <p className="text-xs text-slate-500">
                  Total Final Marks: <strong className="text-slate-800 text-sm">{totals.finalTotal} / {totals.maxTotal}</strong>
                  {' '}(AI Original: {totals.aiTotal})
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 w-full sm:w-auto">
              {/* PDF button in bottom bar */}
              <button
                onClick={handleOpenOriginalPdf}
                disabled={openingPdf}
                className="flex-1 sm:flex-initial inline-flex items-center justify-center px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs transition-colors"
                title="View original answer sheet PDF"
              >
                <FileText className="w-4 h-4 mr-1.5 text-indigo-600" />
                View Original PDF
              </button>

              {/* Save All Drafts */}
              <button
                onClick={handleSaveAll}
                disabled={savingAll || totals.allApproved}
                className="flex-1 sm:flex-initial inline-flex items-center justify-center px-4 py-2.5 bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 font-bold rounded-xl text-xs transition-colors shadow-sm disabled:opacity-50"
              >
                <Save className="w-4 h-4 mr-1.5" />
                {savingAll ? 'Saving All...' : 'Save All Drafts'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Diagram Full View Modal */}
      {previewModalImg && (
        <div 
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4 backdrop-blur-sm"
          onClick={() => setPreviewModalImg(null)}
        >
          <div 
            className="relative bg-white rounded-2xl max-w-3xl max-h-[90vh] overflow-hidden shadow-2xl p-5 flex flex-col"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex justify-between items-center pb-3 border-b border-slate-100">
              <h3 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                <ImageIcon className="w-4 h-4 text-indigo-600" />
                Detected Diagram Region Crop
              </h3>
              <button 
                onClick={() => setPreviewModalImg(null)}
                className="p-1 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="overflow-auto py-4 flex items-center justify-center bg-slate-50 rounded-xl my-2">
              <img 
                src={previewModalImg} 
                alt="Enlarged Diagram View" 
                className="max-h-[70vh] object-contain"
              />
            </div>
            <div className="pt-2 text-right">
              <button
                onClick={() => setPreviewModalImg(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProfessorReview;
