import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import api from '../api/axios';
import PasswordRulesGuide, { isPasswordValid } from '../components/PasswordRulesGuide';

const RegisterStudent = () => {
  const [formData, setFormData] = useState({
    roll_number: '',
    email: '', // Required by backend schema to verify identity
    password: '',
    confirmPassword: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');

    if (!isPasswordValid(formData.password)) {
      setError('Please fulfill all password requirements below: at least 8 characters, with uppercase, lowercase, a number, and a special character.');
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      await api.post('/auth/student/register', {
        roll_number: formData.roll_number,
        email: formData.email,
        password: formData.password
      });
      alert('Student account created successfully.');
      navigate('/login');
    } catch (err) {
      if (err.response && err.response.status === 404) {
        setError('Registration number and email combination not found. Please contact your professor/administrator.');
      } else if (err.response && err.response.status === 400 && err.response.data?.detail?.includes('already has authentication')) {
        setError('An account already exists for this registration number. Please login.');
      } else if (err.response && err.response.data && err.response.data.detail) {
        const detail = err.response.data.detail;
        if (Array.isArray(detail)) {
          setError(detail.map(d => d.msg || JSON.stringify(d)).join(', '));
        } else {
          setError(detail);
        }
      } else if (err.message && err.message.includes('Network Error')) {
        setError('Unable to connect to the backend server. Please verify the server is running on port 8000.');
      } else {
        setError('Registration failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-slate-800 mb-1 text-center">Create Student Account</h1>
        <p className="text-sm text-slate-500 mb-6 text-center">AI-Powered Answer Script Evaluation</p>

        {error && (
          <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-md border border-red-100">
            {error}
          </div>
        )}

        <form onSubmit={handleRegister} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Registration Number</label>
            <input 
              type="text" 
              name="roll_number"
              required
              value={formData.roll_number}
              onChange={handleChange}
              placeholder="e.g. 23BCE0001"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Registered Email (Verification)</label>
            <input 
              type="email" 
              name="email"
              required
              value={formData.email}
              onChange={handleChange}
              placeholder="Enter your official email"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
            <div className="relative">
              <input 
                type={showPassword ? "text" : "password"} 
                name="password"
                required
                value={formData.password}
                onChange={handleChange}
                placeholder="Enter your password (min 8 characters)"
                className="w-full pl-3 pr-10 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 focus:outline-none"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Confirm Password</label>
            <div className="relative">
              <input 
                type={showConfirmPassword ? "text" : "password"} 
                name="confirmPassword"
                required
                value={formData.confirmPassword}
                onChange={handleChange}
                placeholder="Confirm your password"
                className="w-full pl-3 pr-10 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 focus:outline-none"
                aria-label={showConfirmPassword ? "Hide password" : "Show password"}
              >
                {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>

          {/* Real-time Password Rules & Strength Meter */}
          {formData.password && (
            <PasswordRulesGuide 
              password={formData.password} 
              confirmPassword={formData.confirmPassword} 
            />
          )}

          <button 
            type="submit" 
            disabled={loading}
            className="w-full bg-slate-800 text-white font-medium py-2 px-4 rounded-lg hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-500 disabled:opacity-50 mt-2"
          >
            {loading ? 'Creating...' : 'CREATE ACCOUNT'}
          </button>
        </form>

        <div className="mt-6 text-sm text-slate-500 text-center">
          Already have an account? <Link to="/login" className="text-slate-800 font-medium hover:underline">Login</Link>
        </div>
      </div>
    </div>
  );
};

export default RegisterStudent;
