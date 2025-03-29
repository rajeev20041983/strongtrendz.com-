// components/Home.js
import React from 'react';
import { Link } from 'react-router-dom';

const Home = () => {
  return (
    <div>
      {/* Hero Section */}
      <div className="relative h-screen flex items-center justify-center text-white">
        <div className="absolute inset-0 z-0">
          <img src="/stock-trading-bg.jpg" alt="Trading Background" className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-black opacity-60"></div>
        </div>
        
        <div className="container relative z-10 text-center px-4">
          <h1 className="text-5xl md:text-6xl font-bold mb-6">Expert Investment Solutions</h1>
          <p className="text-xl md:text-2xl mb-8 max-w-3xl mx-auto">
            Strong Trendz offers comprehensive investment solutions tailored to your financial goals with over 30+ years in the field.
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <Link to="/services" className="bg-primary hover:bg-primary-dark text-white font-bold py-3 px-8 rounded-lg transition transform hover:scale-105">
              Explore Our Services
            </Link>
            <Link to="/about" className="bg-transparent hover:bg-white/10 text-white border-2 border-white font-bold py-3 px-8 rounded-lg transition transform hover:scale-105">
              Learn About Us
            </Link>
          </div>
        </div>
      </div>
      
      {/* Services Highlights */}
      <section className="py-16 bg-gray-100">
        <div className="container">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold text-primary mb-4">Our Key Services</h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              We specialize in equity trading and portfolio management to help you build and grow your wealth
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 gap-8">
            <div className="bg-white rounded-lg shadow-lg overflow-hidden transform transition hover:scale-105 hover:shadow-xl">
              <div className="h-48 bg-primary flex items-center justify-center">
                <i className="fas fa-chart-line text-6xl text-white"></i>
              </div>
              <div className="p-6">
                <h3 className="text-2xl font-bold text-primary mb-3">Equity Trading</h3>
                <p className="text-gray-600 mb-4">
                  Our advanced trading platforms give you access to real-time market data, powerful analysis tools, and seamless order execution.
                </p>
                <Link to="/services" className="text-primary font-medium hover:underline">Learn More →</Link>
              </div>
            </div>
            
            <div className="bg-white rounded-lg shadow-lg overflow-hidden transform transition hover:scale-105 hover:shadow-xl">
              <div className="h-48 bg-secondary flex items-center justify-center">
                <i className="fas fa-briefcase text-6xl text-white"></i>
              </div>
              <div className="p-6">
                <h3 className="text-2xl font-bold text-primary mb-3">Portfolio Management</h3>
                <p className="text-gray-600 mb-4">
                  Our expert portfolio managers create personalized investment strategies aligned with your financial goals and risk tolerance.
                </p>
                <Link to="/services" className="text-primary font-medium hover:underline">Learn More →</Link>
              </div>
            </div>
          </div>
        </div>
      </section>
      
      {/* Stats Section */}
      <section className="py-16 bg-white">
        <div className="container">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
            <div className="p-6 bg-gray-50 rounded-lg">
              <div className="text-primary text-3xl font-bold mb-2">30+</div>
              <div className="text-gray-600">Years of Experience</div>
            </div>
            
            <div className="p-6 bg-gray-50 rounded-lg">
              <div className="text-primary text-3xl font-bold mb-2">15,000+ Cr.</div>
              <div className="text-gray-600">Assets Under Management</div>
            </div>
            
            <div className="p-6 bg-gray-50 rounded-lg">
              <div className="text-primary text-3xl font-bold mb-2">170+</div>
              <div className="text-gray-600">Team Strength</div>
            </div>
            
            <div className="p-6 bg-gray-50 rounded-lg">
              <div className="text-primary text-3xl font-bold mb-2">160,000+</div>
              <div className="text-gray-600">Happy Clients</div>
            </div>
          </div>
        </div>
      </section>
      
      {/* CTA Section */}
      <section className="py-16 bg-primary text-white">
        <div className="container text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-6">Ready to Start Your Investment Journey?</h2>
          <p className="text-xl mb-8 max-w-3xl mx-auto">
            Join thousands of satisfied investors who trust Strong Trendz for their financial needs.
          </p>
          <Link to="/login" className="bg-white text-primary hover:bg-gray-100 font-bold py-3 px-8 rounded-lg transition">
            Open an Account
          </Link>
        </div>
      </section>
    </div>
  );
};

export default Home;