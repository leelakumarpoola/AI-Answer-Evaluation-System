import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import RegisterProfessor from './pages/RegisterProfessor';
import RegisterStudent from './pages/RegisterStudent';
import ProfessorLayout from './components/ProfessorLayout';
import StudentLayout from './components/StudentLayout';
import ProfessorDashboard from './pages/ProfessorDashboard';
import Subjects from './pages/Subjects';
import Exams from './pages/Exams';
import ExamDetails from './pages/ExamDetails';
import Students from './pages/Students';
import StudentDashboard from './pages/StudentDashboard';
import StudentExams from './pages/StudentExams';
import StudentExamDetail from './pages/StudentExamDetail';
import StudentResults from './pages/StudentResults';
import ProfessorReview from './pages/ProfessorReview';
import ProfessorProfile from './pages/ProfessorProfile';
import ProfessorSettings from './pages/ProfessorSettings';
import Evaluations from './pages/Evaluations';
import Results from './pages/Results';
import Reports from './pages/Reports';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <div className="flex flex-col min-h-screen">
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register-professor" element={<RegisterProfessor />} />
        <Route path="/register-student" element={<RegisterStudent />} />
        
        {/* Protected Professor Routes */}
        <Route element={<ProtectedRoute allowedRole="professor" />}>
          <Route element={<ProfessorLayout />}>
            <Route path="/professor/dashboard" element={<ProfessorDashboard />} />
            <Route path="/professor/subjects" element={<Subjects />} />
            <Route path="/professor/subjects/:subjectId/exams" element={<Exams />} />
            <Route path="/professor/exams/:examId" element={<ExamDetails />} />
            <Route path="/professor/exams/:examId/review/:studentId" element={<ProfessorReview />} />
            <Route path="/professor/students" element={<Students />} />
            <Route path="/professor/profile" element={<ProfessorProfile />} />
            <Route path="/professor/settings" element={<ProfessorSettings />} />
            <Route path="/professor/evaluations" element={<Evaluations />} />
            <Route path="/professor/results" element={<Results />} />
            <Route path="/professor/reports" element={<Reports />} />
          </Route>
        </Route>

        {/* Protected Student Routes */}
        <Route element={<ProtectedRoute allowedRole="student" />}>
          <Route element={<StudentLayout />}>
            <Route path="/student/dashboard" element={<StudentDashboard />} />
            <Route path="/student/exams" element={<StudentExams />} />
            <Route path="/student/exam/:examId" element={<StudentExamDetail />} />
            <Route path="/student/results" element={<StudentResults />} />
          </Route>
        </Route>

        {/* Catch-all redirect */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </div>
  );
}

export default App;

