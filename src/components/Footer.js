import React from 'react';
import { Link } from 'react-router-dom';

const Footer = () => {
  return (
    <footer className="bg-gray-800 text-white py-12">
      <div className="container mx-auto px-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Column 1 - About */}
          <div>
            <h3 className="text-xl font-bold mb-4">Strong Trendz</h3>
            <p className="mb-4">Your trusted partner for investment solutions with over 30 years of experience.</p>
            <p>© {new Date().getFullYear()} Strong Trendz. All rights reserved.</p>
          </div>
          
          {/* Column 2 - Quick Links */}
          <div>
            <h3 className="text-xl font-bold mb-4">Quick Links</h3>
            <ul className="space-y-2">
              <li><Link to="/" className="hover:text-secondary">Home</Link></li>
              <li><Link to="/about" className="hover:text-secondary">About Us</Link></li>
              <li><Link to="/services" className="hover:text-secondary">Services</Link></li>
              <li><Link to="/contact" className="hover:text-secondary">Contact</Link></li>
            </ul>
          </div>
          
          {/* Column 3 - Services */}
          <div>
            <h3 className="text-xl font-bold mb-4">Services</h3>
            <ul className="space-y-2">
              <li><Link to="/services" className="hover:text-secondary">Equity Trading</Link></li>
              <li><Link to="/services" className="hover:text-secondary">Portfolio Management</Link></li>
              <li><Link to="/services" className="hover:text-secondary">Investment Advisory</Link></li>
              <li><Link to="/services" className="hover:text-secondary">Research Reports</Link></li>
            </ul>
          </div>
          
          {/* Column 4 - Contact */}
          <div>
            <h3 className="text-xl font-bold mb-4">Contact Us</h3>
            <ul className="space-y-2">
              <li className="flex items-center">
                <i className="fas fa-map-marker-alt mr-2"></i>
                <span>Sardar Gunj Road, Anand 388001, Gujarat</span>
              </li>
              <li className="flex items-center">
                <i className="fas fa-phone-alt mr-2"></i>
                <a href="tel:02692-225000">02692-225000</a>
              </li>
              <li className="flex items-center">
                <i className="fas fa-envelope mr-2"></i>
                <a href="mailto:cs@strongtrendz.com">cs@strongtrendz.com</a>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;