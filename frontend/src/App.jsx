import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import RegisterProfessor from './pages/RegisterProfessor';
import RegisterStudent from './pages/RegisterStudent';
import ProfessorLayout from './components/ProfessorLayout';
import ProfessorDashboard from './pages/ProfessorDashboard';
import Subjects from './pages/Subjects';
import Exams from './pages/Exams';
import ExamDetails from './pages/ExamDetails';
import Students from './pages/Students';
import StudentDashboard from './pages/StudentDashboard';
import ProfessorReview from './pages/ProfessorReview';
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
          </Route>
        </Route>

        {/* Protected Student Routes */}
        <Route element={<ProtectedRoute allowedRole="student" />}>
          <Route path="/student/dashboard" element={<StudentDashboard />} />
        </Route>

        {/* Catch-all redirect */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </div>
  );
}

export default App;
