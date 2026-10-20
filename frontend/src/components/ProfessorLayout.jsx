import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LogOut, LayoutDashboard, BookOpen, FileText, Users, User, CheckCircle2, BarChart3, Settings } from 'lucide-react';

const ProfessorLayout = () => {
  const { user, logout } = useAuth();
  const location = useLocation();

  const navItems = [
    { name: 'Dashboard', path: '/professor/dashboard', icon: LayoutDashboard },
    { name: 'Subjects', path: '/professor/subjects', icon: BookOpen },
    { name: 'Assessments', path: '/professor/subjects', activePattern: '/professor/exams', icon: FileText },
    { name: 'Evaluation', path: '/professor/evaluations', icon: CheckCircle2 },
    { name: 'Results', path: '/professor/results', icon: FileText },
    { name: 'Reports & Analysis', path: '/professor/reports', icon: BarChart3 },
    { name: 'Students', path: '/professor/students', icon: Users },
    { name: 'Profile', path: '/professor/profile', icon: User },
    { name: 'Settings', path: '/professor/settings', icon: Settings },
  ];

  const isActive = (item) => {
    if (location.pathname === item.path) return true;
    if (item.activePattern && location.pathname.startsWith(item.activePattern)) return true;
    if (item.name === 'Subjects' && location.pathname.includes('/subjects/')) return true;
    return false;
  };

  return (
    <div className="flex min-h-screen bg-[#F8FAFC]">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col hidden md:flex">
        <div className="p-6 border-b border-slate-100">
          <h1 className="text-xl font-bold text-slate-800">AI Evaluator</h1>
          <p className="text-xs text-slate-500 mt-1">Professor Portal</p>
        </div>

        <div className="flex-1 py-6 px-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const active = isActive(item);
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                to={item.path}
                className={`flex items-center px-4 py-3 text-sm font-medium rounded-xl transition-colors ${
                  active 
                    ? 'bg-slate-800 text-white shadow-sm' 
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                <Icon className={`w-5 h-5 mr-3 ${active ? 'text-white' : 'text-slate-400'}`} />
                {item.name}
              </Link>
            );
          })}
        </div>

        <div className="p-4 border-t border-slate-100">
          <div className="flex items-center px-4 py-3 mb-2 bg-slate-50 rounded-xl border border-slate-100">
            <User className="w-8 h-8 p-1.5 bg-slate-200 rounded-full text-slate-600 mr-3" />
            <div className="overflow-hidden">
              <p className="text-sm font-semibold text-slate-800 truncate">{user?.name || 'Professor'}</p>
              <p className="text-xs text-slate-500 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="flex w-full items-center px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-xl transition-colors"
          >
            <LogOut className="w-5 h-5 mr-3 text-red-500" />
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        <header className="bg-white border-b border-slate-200 px-8 py-4 flex items-center justify-between md:hidden">
          <h1 className="text-lg font-bold text-slate-800">AI Evaluator</h1>
          <button onClick={logout} className="text-sm font-medium text-red-600">Logout</button>
        </header>
        <div className="flex-1 overflow-auto p-4 md:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default ProfessorLayout;
