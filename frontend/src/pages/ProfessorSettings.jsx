import React, { useState } from 'react';
import { Bell, Shield, Eye, Moon, Monitor } from 'lucide-react';

const ProfessorSettings = () => {
  const [notifications, setNotifications] = useState(true);
  const [darkMode, setDarkMode] = useState(false);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-800">Settings</h1>
        <p className="text-slate-500 mt-1">Configure your dashboard preferences and system settings.</p>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-6 border-b border-slate-100 flex items-center gap-3">
          <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
            <Monitor className="w-5 h-5" />
          </div>
          <h2 className="text-lg font-bold text-slate-800">Preferences</h2>
        </div>
        <div className="p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold text-slate-800 flex items-center">
                <Bell className="w-4 h-4 mr-2 text-slate-400" /> Email Notifications
              </h3>
              <p className="text-sm text-slate-500">Receive alerts when evaluations are complete.</p>
            </div>
            <button 
              onClick={() => setNotifications(!notifications)}
              className={`w-12 h-6 rounded-full transition-colors relative ${notifications ? 'bg-blue-600' : 'bg-slate-300'}`}
            >
              <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all ${notifications ? 'left-7' : 'left-1'}`} />
            </button>
          </div>
          <hr className="border-slate-100" />
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold text-slate-800 flex items-center">
                <Moon className="w-4 h-4 mr-2 text-slate-400" /> Dark Mode
              </h3>
              <p className="text-sm text-slate-500">Toggle dark appearance for the dashboard.</p>
            </div>
            <button 
              onClick={() => setDarkMode(!darkMode)}
              className={`w-12 h-6 rounded-full transition-colors relative ${darkMode ? 'bg-blue-600' : 'bg-slate-300'}`}
            >
              <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all ${darkMode ? 'left-7' : 'left-1'}`} />
            </button>
          </div>
        </div>
      </div>
      
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden mt-6">
        <div className="p-6 border-b border-slate-100 flex items-center gap-3">
          <div className="p-2 bg-purple-50 text-purple-600 rounded-lg">
            <Shield className="w-5 h-5" />
          </div>
          <h2 className="text-lg font-bold text-slate-800">Privacy & Security</h2>
        </div>
        <div className="p-6 space-y-4">
          <p className="text-sm text-slate-600">
            The AI Evaluator System adheres to strictly confidential data handling. Student answer scripts are processed completely offline without being sent to external third-party models (e.g., OpenAI).
          </p>
          <button className="text-sm font-medium text-blue-600 hover:underline flex items-center">
            <Eye className="w-4 h-4 mr-1" /> View Full Privacy Policy
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProfessorSettings;
