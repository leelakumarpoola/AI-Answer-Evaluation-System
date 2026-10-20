import React from 'react';
import { useAuth } from '../context/AuthContext';
import { User, Mail, Shield, Key } from 'lucide-react';

const ProfessorProfile = () => {
  const { user } = useAuth();
  
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-800">My Profile</h1>
        <p className="text-slate-500 mt-1">Manage your account details and credentials.</p>
      </div>
      
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-8 border-b border-slate-100 flex items-center gap-6">
          <div className="w-24 h-24 bg-slate-200 rounded-full flex items-center justify-center text-3xl font-bold text-slate-600">
            {user?.name?.[0] || 'P'}
          </div>
          <div>
            <h2 className="text-2xl font-bold text-slate-800">{user?.name || 'Professor'}</h2>
            <div className="flex items-center text-slate-500 mt-1">
              <Shield className="w-4 h-4 mr-1 text-blue-500" />
              <span className="capitalize">{user?.role}</span>
            </div>
          </div>
        </div>
        
        <div className="p-8 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-bold text-slate-500 uppercase tracking-wider mb-2">Email Address</label>
              <div className="flex items-center p-3 bg-slate-50 rounded-xl border border-slate-100">
                <Mail className="w-5 h-5 text-slate-400 mr-3" />
                <span className="font-medium text-slate-800">{user?.email}</span>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-bold text-slate-500 uppercase tracking-wider mb-2">Account Status</label>
              <div className="flex items-center p-3 bg-emerald-50 rounded-xl border border-emerald-100">
                <Shield className="w-5 h-5 text-emerald-500 mr-3" />
                <span className="font-medium text-emerald-700">Active</span>
              </div>
            </div>
          </div>
          
          <hr className="border-slate-100" />
          
          <div>
            <h3 className="font-bold text-slate-800 mb-4">Security</h3>
            <button className="flex items-center px-4 py-2 bg-white border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors">
              <Key className="w-4 h-4 mr-2" /> Change Password
            </button>
            <p className="text-xs text-slate-500 mt-2">Password management is handled by your university IT administrator.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfessorProfile;
