// components/Footer.js
import React from 'react';
import { Link } from 'react-router-dom';

const Footer = () => {
  return (
    <footer className="bg-primary text-white">
      <div className="container py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div>
            <img src="/logo-white.png" alt="Strong Trendz Logo" className="h-12 mb-4" />
            <div className="mb-4">
              <span className="font-medium block mb-2">HEAD OFFICE</span>
              <address className="not-italic">
                Opp. People's Bank Park,<br />
                Sardar Gunj Road, Anand 388001.<br />
                Gujarat
              </address>
            </div>
            <div className="flex space-x-4 mt-6">
              <a href="#" className="w-8 h-8 bg-white bg-opacity-10 rounded-full flex items-center justify-center hover:bg-secondary transition">
                <i className="fab fa-facebook-f"></i>
              </a>
              <a href="#" className="w-8 h-8 bg-white bg-opacity-10 rounded-full flex items-center justify-center hover:bg-secondary transition">
                <i className="fab fa-twitter"></i>
              </a>
              <a href="#" className="w-8 h-8 bg-white bg-opacity-10 rounded-full flex items-center justify-center hover:bg-secondary transition">
                <i className="fab fa-instagram"></i>
              </a>
              <a href="#" className="w-8 h-8 bg-white bg-opacity-10 rounded-full flex items-center justify-center hover:bg-secondary transition">
                <i className="fab fa-linkedin-in"></i>
              </a>
            </div>
          </div>
          
          <div>
            <h3 className="text-lg font-bold mb-4">Quick Links</h3>
            <ul className="space-y-2">
              <li><Link to="/" className="hover:text-secondary transition">Home</Link></li>
              <li><Link to="/about" className="hover:text-secondary transition">About Us</Link></li>
              <li><Link to="/services" className="hover:text-secondary transition">Services</Link></li>
              <li><Link to="/login" className="hover:text-secondary transition">Customer Login</Link></li>
            </ul>
          </div>
          
          <div>
            <h3 className="text-lg font-bold mb-4">Our Services</h3>
            <ul className="space-y-2">
              <li><a href="#" className="hover:text-secondary transition">Equity Trading</a></li>
              <li><a href="#" className="hover:text-secondary transition">Portfolio Management</a></li>
              <li><a href="#" className="hover:text-secondary transition">Research Reports</a></li>
              <li><a href="#" className="hover:text-secondary transition">Market Analysis</a></li>
            </ul>
          </div>
          
          <div>
            <h3 className="text-lg font-bold mb-4">Contact Us</h3>
            <ul className="space-y-2">
              <li className="flex items-center">
                <i className="fas fa-phone-alt mr-3"></i>
                <a href="tel:02692-225000">02692-225000</a>
              </li>
              <li className="flex items-center">
                <i className="fas fa-envelope mr-3"></i>
                <a href="mailto:cs@strongtrendz.com">cs@strongtrendz.com</a>
              </li>
            </ul>
          </div>
        </div>
      </div>
      
      <div className="border-t border-white border-opacity-10">
        <div className="container py-6 text-center text-sm">
          <p>&copy; {new Date().getFullYear()} Strong Trendz. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;