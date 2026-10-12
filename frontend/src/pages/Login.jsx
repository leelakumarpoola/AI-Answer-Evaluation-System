import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Login = () => {
  const [activeTab, setActiveTab] = useState('professor');
  const [email, setEmail] = useState('');
  const [identifier, setIdentifier] = useState(''); // Registration Number for students
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (activeTab === 'professor') {
        await login('professor', { email, password });
        navigate('/professor/dashboard');
      } else {
        await login('student', { identifier, password });
        navigate('/student/dashboard');
      }
    } catch (err) {
      if (err.response && err.response.status === 401) {
        setError(activeTab === 'professor' ? 'Invalid VIT email or password.' : 'Invalid registration number or password.');
      } else {
        setError('Unable to connect to the server. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 w-full max-w-md text-center">
        <h1 className="text-2xl font-bold text-slate-800 mb-1">AI Answer Evaluation System</h1>
        <p className="text-sm text-slate-500 mb-6">AI-Powered Answer Script Evaluation</p>

        <div className="flex rounded-md overflow-hidden border border-slate-200 mb-6">
          <button 
            type="button"
            onClick={() => { setActiveTab('professor'); setError(''); }}
            className={`flex-1 py-2 text-sm font-medium transition-colors ${activeTab === 'professor' ? 'bg-slate-800 text-white' : 'bg-slate-50 text-slate-600 hover:bg-slate-100'}`}
          >
            Professor
          </button>
          <button 
            type="button"
            onClick={() => { setActiveTab('student'); setError(''); }}
            className={`flex-1 py-2 text-sm font-medium transition-colors ${activeTab === 'student' ? 'bg-slate-800 text-white' : 'bg-slate-50 text-slate-600 hover:bg-slate-100'}`}
          >
            Student
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-md border border-red-100 text-left">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4 text-left">
          {activeTab === 'professor' ? (
            <>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">VIT Email</label>
                <input 
                  type="email" 
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your VIT email"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-shadow"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
                <input 
                  type="password" 
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-shadow"
                />
              </div>
            </>
          ) : (
            <>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Registration Number</label>
                <input 
                  type="text" 
                  required
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder="e.g. 23BCE0001"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-shadow"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
                <input 
                  type="password" 
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-shadow"
                />
              </div>
            </>
          )}

          <button 
            type="submit" 
            disabled={loading}
            className="w-full bg-slate-800 text-white font-medium py-2 px-4 rounded-lg hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-500 disabled:opacity-50 transition-colors mt-2"
          >
            {loading ? 'Signing in...' : 'LOGIN'}
          </button>
        </form>

        <div className="mt-6 text-sm text-slate-500">
          Don't have an account? <br />
          {activeTab === 'professor' ? (
            <Link to="/register-professor" className="text-slate-800 font-medium hover:underline">
              Create Professor Account
            </Link>
          ) : (
            <Link to="/register-student" className="text-slate-800 font-medium hover:underline">
              Create Student Account
            </Link>
          )}
        </div>
      </div>
    </div>
  );
};

export default Login;
