import React, { createContext, useState, useEffect, useContext } from 'react';
import api from '../api/axios';
import { useNavigate } from 'react-router-dom';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('access_token'));
  const [role, setRole] = useState(localStorage.getItem('role'));
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchUser = async () => {
      if (token) {
        try {
          const response = await api.get('/auth/me');
          setUser(response.data);
          setRole(response.data.role);
          localStorage.setItem('role', response.data.role);
        } catch (error) {
          console.error("Session expired or invalid token:", error);
          logout();
        }
      }
      setLoading(false);
    };
    fetchUser();
  }, [token]);

  // Optionally listen to 401 globally
  useEffect(() => {
    const interceptor = api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response && error.response.status === 401) {
          logout();
        }
        return Promise.reject(error);
      }
    );
    return () => api.interceptors.response.eject(interceptor);
  }, []);

  const login = async (roleType, credentials) => {
    const endpoint = roleType === 'professor' ? '/auth/professor/login' : '/auth/student/login';
    const response = await api.post(endpoint, credentials);
    const { access_token, role: responseRole } = response.data;
    
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('role', responseRole);
    setToken(access_token);
    setRole(responseRole);
    
    // Fetch user immediately
    const meResponse = await api.get('/auth/me', {
      headers: { Authorization: `Bearer ${access_token}` }
    });
    setUser(meResponse.data);
    
    return meResponse.data;
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('role');
    setToken(null);
    setUser(null);
    setRole(null);
    navigate('/login');
  };

  return (
    <AuthContext.Provider value={{ user, token, role, isAuthenticated: !!user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
