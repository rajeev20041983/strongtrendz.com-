// auth/AuthContext.js
import React, { useContext, useState, useEffect, createContext } from 'react';

const AuthContext = createContext();

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [userRole, setUserRole] = useState(null);

  // On mount, check if user is logged in (e.g., from localStorage)
  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    const savedRole = localStorage.getItem('userRole');
    
    if (savedUser) {
      setCurrentUser(JSON.parse(savedUser));
      setUserRole(savedRole);
    }
    
    setLoading(false);
  }, []);

  // Simulated login function - in production would connect to AWS API Gateway
  async function login(email, password, role) {
    // This would be replaced with actual API call to your AWS Lambda function
    // For demo purposes, we'll just simulate a successful login
    
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const user = { id: '123', email: email };
    setCurrentUser(user);
    setUserRole(role);
    
    // Save to localStorage for persistence
    localStorage.setItem('user', JSON.stringify(user));
    localStorage.setItem('userRole', role);
    
    return user;
  }

  function logout() {
    setCurrentUser(null);
    setUserRole(null);
    localStorage.removeItem('user');
    localStorage.removeItem('userRole');
  }

  const value = {
    currentUser,
    userRole,
    login,
    logout
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
}