import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

const Register = () => {
  const [role, setRole] = useState('professor');
  const [formData, setFormData] = useState({
    fullName: '',
    username: '',
    password: '',
    confirmPassword: '',
    department: '',
    employeeId: '',
    registrationNumber: '',
    year: ''
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  const validatePassword = (password) => {
    const minLength = password.length >= 8;
    const hasUpper = /[A-Z]/.test(password);
    const hasLower = /[a-z]/.test(password);
    const hasNumber = /[0-9]/.test(password);
    const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password);
    return minLength && hasUpper && hasLower && hasNumber && hasSpecial;
  };

  const handleRegister = (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    // Basic Validation
    if (!formData.fullName || !formData.username || !formData.password || !formData.confirmPassword || !formData.department) {
      setError('Please fill in all required fields');
      return;
    }
    
    if (role === 'professor' && !formData.employeeId) {
      setError('Employee/Professor ID is required');
      return;
    }

    if (role === 'student' && (!formData.registrationNumber || !formData.year)) {
      setError('Registration Number and Year are required');
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (!validatePassword(formData.password)) {
      setError('Password does not meet the minimum requirements');
      return;
    }

    if (formData.username === 'professor01') {
      setError('Username is already taken. Try another one.');
      return;
    }

    // Mock Registration Success
    setSuccess('Registration successful! Redirecting to login...');
    setTimeout(() => {
      navigate('/login');
    }, 2000);
  };

  return (
    <div className="card auth-card" style={{ maxWidth: '500px', width: '100%', margin: '2rem 0' }}>
      <div className="text-center mb-6">
        <h2 className="text-xl font-semibold mb-2">Create an Account</h2>
        <p className="text-muted text-sm">Join the AI Powered Answer Script Evaluation platform.</p>
      </div>

      <div className="flex gap-2 mb-6 p-1" style={{ background: 'var(--bg-color)', borderRadius: 'var(--radius)' }}>
        <button 
          className={`flex-1 py-2 text-sm font-medium rounded ${role === 'professor' ? 'btn-primary' : ''}`}
          style={{ background: role === 'professor' ? 'white' : 'transparent', color: role === 'professor' ? 'var(--text-main)' : 'var(--text-muted)', boxShadow: role === 'professor' ? 'var(--shadow-sm)' : 'none', border: 'none', cursor: 'pointer' }}
          onClick={() => setRole('professor')}
        >
          Professor
        </button>
        <button 
          className={`flex-1 py-2 text-sm font-medium rounded ${role === 'student' ? 'btn-primary' : ''}`}
          style={{ background: role === 'student' ? 'white' : 'transparent', color: role === 'student' ? 'var(--text-main)' : 'var(--text-muted)', boxShadow: role === 'student' ? 'var(--shadow-sm)' : 'none', border: 'none', cursor: 'pointer' }}
          onClick={() => setRole('student')}
        >
          Student
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 text-sm rounded" style={{ background: '#fee2e2', color: '#b91c1c' }}>
          {error}
        </div>
      )}
      
      {success && (
        <div className="mb-4 p-3 text-sm rounded" style={{ background: '#d1fae5', color: '#065f46' }}>
          {success}
        </div>
      )}

      <form onSubmit={handleRegister}>
        <div className="input-group">
          <label className="input-label">Full Name *</label>
          <input type="text" name="fullName" className="input-field" value={formData.fullName} onChange={handleInputChange} />
        </div>

        <div className="input-group">
          <label className="input-label">Username *</label>
          <input type="text" name="username" className="input-field" value={formData.username} onChange={handleInputChange} />
        </div>

        {role === 'professor' ? (
          <div className="flex gap-4">
            <div className="input-group flex-1">
              <label className="input-label">Department *</label>
              <input type="text" name="department" className="input-field" value={formData.department} onChange={handleInputChange} />
            </div>
            <div className="input-group flex-1">
              <label className="input-label">Employee ID *</label>
              <input type="text" name="employeeId" className="input-field" value={formData.employeeId} onChange={handleInputChange} />
            </div>
          </div>
        ) : (
          <>
            <div className="input-group">
              <label className="input-label">Registration Number *</label>
              <input type="text" name="registrationNumber" className="input-field" value={formData.registrationNumber} onChange={handleInputChange} />
            </div>
            <div className="flex gap-4">
              <div className="input-group flex-1">
                <label className="input-label">Department *</label>
                <input type="text" name="department" className="input-field" value={formData.department} onChange={handleInputChange} />
              </div>
              <div className="input-group flex-1">
                <label className="input-label">Year *</label>
                <select name="year" className="input-field" value={formData.year} onChange={handleInputChange}>
                  <option value="">Select Year</option>
                  <option value="1">1st Year</option>
                  <option value="2">2nd Year</option>
                  <option value="3">3rd Year</option>
                  <option value="4">4th Year</option>
                </select>
              </div>
            </div>
          </>
        )}

        <div className="flex gap-4">
          <div className="input-group flex-1">
            <label className="input-label">Password *</label>
            <input type="password" name="password" className="input-field" value={formData.password} onChange={handleInputChange} />
          </div>
          <div className="input-group flex-1">
            <label className="input-label">Confirm Password *</label>
            <input type="password" name="confirmPassword" className="input-field" value={formData.confirmPassword} onChange={handleInputChange} />
          </div>
        </div>

        <div className="mb-6 mt-2">
          <p className="text-sm font-medium mb-1">Password Requirements:</p>
          <ul className="text-xs text-muted" style={{ paddingLeft: '1.25rem' }}>
            <li>Minimum 8 characters</li>
            <li>At least one uppercase letter</li>
            <li>At least one lowercase letter</li>
            <li>At least one number</li>
            <li>At least one special character</li>
          </ul>
        </div>

        <button type="submit" className="btn btn-primary w-full justify-center mb-4">
          Register
        </button>

        <div className="text-center text-sm text-muted">
          Already have an account? <Link to="/login" className="font-medium text-primary">Login here</Link>
        </div>
      </form>
    </div>
  );
};

export default Register;
