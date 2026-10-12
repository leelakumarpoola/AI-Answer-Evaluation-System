import React, { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, 
  FileText, 
  FilePlus, 
  Upload, 
  CheckCircle, 
  BarChart, 
  Users, 
  User, 
  Settings, 
  LogOut,
  Menu,
  Bell
} from 'lucide-react';
import { logout, getCurrentUser } from '../services/authService';

const DashboardLayout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const navigate = useNavigate();
  const user = getCurrentUser();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navItems = [
    { name: 'Dashboard', path: '/professor/dashboard', icon: <LayoutDashboard size={20} /> },
    { name: 'Examinations', path: '/professor/examinations', icon: <FileText size={20} /> },
    { name: 'Create Examination', path: '/professor/create-examination', icon: <FilePlus size={20} /> },
    { name: 'Upload Answer Scripts', path: '/professor/upload', icon: <Upload size={20} /> },
    { name: 'Evaluation', path: '/professor/evaluation', icon: <CheckCircle size={20} /> },
    { name: 'Results', path: '/professor/results', icon: <BarChart size={20} /> },
    { name: 'Student Performance', path: '/professor/students', icon: <Users size={20} /> },
  ];

  const bottomNavItems = [
    { name: 'Profile', path: '/professor/profile', icon: <User size={20} /> },
    { name: 'Settings', path: '/professor/settings', icon: <Settings size={20} /> },
  ];

  return (
    <div className="dashboard-layout">
      {/* Overlay for mobile sidebar */}
      {sidebarOpen && (
        <div 
          style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 40 }}
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          AI Evaluator
        </div>
        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <NavLink 
              key={item.name}
              to={item.path} 
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setSidebarOpen(false)}
            >
              {item.icon}
              <span>{item.name}</span>
            </NavLink>
          ))}
          
          <div style={{ margin: '1rem 0', borderTop: '1px solid var(--sidebar-hover)' }}></div>
          
          {bottomNavItems.map((item) => (
            <NavLink 
              key={item.name}
              to={item.path} 
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setSidebarOpen(false)}
            >
              {item.icon}
              <span>{item.name}</span>
            </NavLink>
          ))}
          
          <button className="nav-item" onClick={handleLogout} style={{ background: 'transparent', border: 'none', width: '100%', textAlign: 'left', cursor: 'pointer' }}>
            <LogOut size={20} />
            <span>Logout</span>
          </button>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {/* Header */}
        <header className="top-header">
          <div className="flex items-center gap-4">
            <button className="menu-toggle" onClick={() => setSidebarOpen(true)}>
              <Menu size={24} />
            </button>
            <h1 className="text-lg font-semibold hidden md:block" style={{ margin: 0 }}>Professor Dashboard</h1>
          </div>
          
          <div className="flex items-center gap-4">
            <button style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
              <Bell size={20} />
            </button>
            <div className="flex items-center gap-2">
              <div style={{ width: 32, height: 32, borderRadius: '50%', backgroundColor: 'var(--primary)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }}>
                {user?.name?.charAt(0) || 'P'}
              </div>
              <span className="text-sm font-medium hidden md:block">{user?.name || 'Professor'}</span>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <div className="content-area">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default DashboardLayout;
