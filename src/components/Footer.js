import React from 'react';
import { Link } from 'react-router-dom';

const Footer = () => {
  return (
    <footer className="bg-gray-800 text-white py-8">
      <div className="container mx-auto px-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Company Info */}
          <div>
            <h3 className="text-xl font-bold mb-4">Strong Trendz</h3>
            <p className="mb-4">Your trusted partner for investment solutions since 1992.</p>
            <p>© {new Date().getFullYear()} Strong Trendz. All rights reserved.</p>
          </div>
          
          {/* Quick Links */}
          <div>
            <h3 className="text-xl font-bold mb-4">Quick Links</h3>
            <ul className="space-y-2">
              <li><Link to="/" className="hover:text-blue-300">Home</Link></li>
              <li><Link to="/about" className="hover:text-blue-300">About Us</Link></li>
              <li><Link to="/services" className="hover:text-blue-300">Services</Link></li>
              <li><Link to="/contact" className="hover:text-blue-300">Contact</Link></li>
            </ul>
          </div>
          
          {/* Contact */}
          <div>
            <h3 className="text-xl font-bold mb-4">Contact Us</h3>
            <p className="mb-2">Sardar Gunj Road, Anand 388001</p>
            <p className="mb-2">Gujarat, India</p>
            <p className="mb-2">
              <a href="tel:02692-225000" className="hover:text-blue-300">02692-225000</a>
            </p>
            <p>
              <a href="mailto:cs@strongtrendz.com" className="hover:text-blue-300">cs@strongtrendz.com</a>
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;