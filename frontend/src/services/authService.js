// Mock Authentication Service

export const login = async (username, password, role) => {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      if (role === 'professor' && username === 'professor01' && password === 'Professor@123') {
        const user = {
          id: 1,
          name: 'Dr. Smith',
          username: 'professor01',
          role: 'professor'
        };
        localStorage.setItem('user', JSON.stringify(user));
        resolve({ success: true, user });
      } else {
        reject({ success: false, message: 'Invalid username or password' });
      }
    }, 1000);
  });
};

export const logout = () => {
  localStorage.removeItem('user');
};

export const getCurrentUser = () => {
  const user = localStorage.getItem('user');
  return user ? JSON.parse(user) : null;
};

export const isAuthenticated = () => {
  return !!localStorage.getItem('user');
};
