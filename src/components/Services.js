// components/Services.js
import React from 'react';

const Services = () => {
  return (
    <div>
      <div className="py-16 bg-gray-100" style={{backgroundImage: 'url(/stock-chart-bg.jpg)', backgroundSize: 'cover', backgroundPosition: 'center'}}>
        <div className="container">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold text-white mb-4">Our Services</h2>
            <p className="text-xl text-white max-w-3xl mx-auto">
              We specialize in equity trading and portfolio management services to help you achieve your financial goals.
            </p>
          </div>
        </div>
      </div>
      
      <section className="py-16">
        <div className="container">
          <div className="bg-white shadow-lg rounded-lg overflow-hidden mb-12">
            <div className="flex flex-col md:flex-row">
              <div className="md:w-5/12 bg-primary">
                <div className="h-full flex items-center justify-center p-10">
                  <i className="fas fa-chart-line text-9xl text-white"></i>
                </div>
              </div>
              
              <div className="md:w-7/12 p-8">
                <h3 className="text-3xl font-bold text-primary mb-4">Equity Trading</h3>
                
                <p className="mb-4 text-lg">
                  Our equity trading services provide you with access to both cash and derivative segments of NSE and BSE. 
                  We offer a seamless trading experience through our advanced web and mobile platforms.
                </p>
                
                <h4 className="text-xl font-bold text-gray-800 mt-6 mb-3">Key Features:</h4>
                
                <ul className="list-disc pl-6 mb-6 text-lg">
                  <li className="mb-2">Real-time market data and quotes</li>
                  <li className="mb-2">Advanced charting tools and technical analysis</li>
                  <li className="mb-2">Instant order execution</li>
                  <li className="mb-2">Detailed research reports and market insights</li>
                  <li className="mb-2">Personalized trading strategies</li>
                </ul>
                
                <a href="#" className="inline-block mt-4 bg-primary text-white py-3 px-6 rounded font-medium hover:bg-primary-dark transition">
                  Learn More About Equity Trading
                </a>
              </div>
            </div>
          </div>
          
          <div className="bg-white shadow-lg rounded-lg overflow-hidden">
            <div className="flex flex-col md:flex-row">
              <div className="md:w-7/12 p-8 order-2 md:order-1">
                <h3 className="text-3xl font-bold text-primary mb-4">Portfolio Management</h3>
                
                <p className="mb-4 text-lg">
                  Our Portfolio Management Services (PMS) offer professional management of your investment portfolio, 
                  tailored to your risk appetite and financial goals.
                </p>
                
                <h4 className="text-xl font-bold text-gray-800 mt-6 mb-3">Our Approach:</h4>
                
                <ul className="list-disc pl-6 mb-6 text-lg">
                  <li className="mb-2">Comprehensive risk assessment and goal planning</li>
                  <li className="mb-2">Diversified investment strategies</li>
                  <li className="mb-2">Regular portfolio rebalancing</li>
                  <li className="mb-2">Periodic performance reviews</li>
                  <li className="mb-2">Transparent fee structure</li>
                </ul>
                
                <a href="#" className="inline-block mt-4 bg-primary text-white py-3 px-6 rounded font-medium hover:bg-primary-dark transition">
                  Explore Portfolio Management
                </a>
              </div>
              
              <div className="md:w-5/12 bg-secondary order-1 md:order-2">
                <div className="h-full flex items-center justify-center p-10">
                  <i className="fas fa-briefcase text-9xl text-white"></i>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Services;