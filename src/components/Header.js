// components/Header.js
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import LoginModal from './LoginModal';

const Header = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const { currentUser, logout } = useAuth();

  const toggleMenu = () => {
    setIsMenuOpen(!isMenuOpen);
  };

  return (
    <>
      <div className="top-bar bg-primary text-white py-2">
        <div className="container flex justify-between items-center">
          <div className="contact-info flex items-center">
            <a href="mailto:cs@strongtrendz.com" className="mr-4 flex items-center">
              <i className="fas fa-envelope mr-2"></i>
              <span className="hidden sm:inline">cs@strongtrendz.com</span>
            </a>
            <a href="tel:02692-225000" className="flex items-center">
              <i className="fas fa-phone-alt mr-2"></i>
              <span className="hidden sm:inline">02692-225000</span>
            </a>
          </div>
          <div className="social-icons flex">
            <a href="#" className="ml-4" aria-label="Facebook"><i className="fab fa-facebook-f"></i></a>
            <a href="#" className="ml-4" aria-label="Instagram"><i className="fab fa-instagram"></i></a>
            <a href="#" className="ml-4" aria-label="Twitter"><i className="fab fa-twitter"></i></a>
            <a href="#" className="ml-4" aria-label="LinkedIn"><i className="fab fa-linkedin-in"></i></a>
          </div>
        </div>
      </div>
      
      <header className="main-header py-4 shadow-md relative z-20 bg-white">
        <div className="container">
          <div className="flex justify-between items-center">
            <div className="logo">
              <Link to="/">
                <img src="/logo.png" alt="Strong Trendz Logo" className="h-12" />
              </Link>
            </div>
            
            <div className="md:hidden">
              <button onClick={toggleMenu} className="text-primary text-2xl">
                <i className="fas fa-bars"></i>
              </button>
            </div>
            
            <nav className={`main-nav md:flex ${isMenuOpen ? 'mobile-menu-active' : 'mobile-menu-hidden'}`}>
              <ul className="nav-menu md:flex">
                <li className="md:ml-6"><Link to="/" className="block py-2 text-primary font-medium hover:text-secondary">Home</Link></li>
                <li className="md:ml-6"><Link to="/about" className="block py-2 text-primary font-medium hover:text-secondary">About Us</Link></li>
                <li className="md:ml-6"><Link to="/services" className="block py-2 text-primary font-medium hover:text-secondary">Services</Link></li>
                {currentUser ? (
                  <>
                    <li className="md:ml-6"><Link to="/dashboard" className="block py-2 text-primary font-medium hover:text-secondary">Dashboard</Link></li>
                    <li className="md:ml-6"><button onClick={logout} className="block py-2 text-primary font-medium hover:text-secondary">Logout</button></li>
                  </>
                ) : (
                  <li className="md:ml-6">
                    <button 
                      onClick={() => setShowLoginModal(true)} 
                      className="login-btn bg-primary text-white px-4 py-2 rounded flex items-center"
                    >
                      <i className="fas fa-lock mr-2"></i> LOGIN
                    </button>
                  </li>
                )}
              </ul>
            </nav>
          </div>
        </div>
      </header>
      
      {showLoginModal && (
        <LoginModal onClose={() => setShowLoginModal(false)} />
      )}
    </>
  );
};

export default Header;