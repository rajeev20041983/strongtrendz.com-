// components/AboutUs.js
import React from 'react';

const AboutUs = () => {
  return (
    <section className="py-16">
      <div className="container">
        <div className="flex flex-col md:flex-row items-center">
          <div className="md:w-5/12 mb-10 md:mb-0 md:pr-10">
            <img src="/about-us.jpg" alt="About Strong Trendz" className="rounded-lg shadow-lg w-full" />
          </div>
          
          <div className="md:w-7/12">
            <h2 className="text-4xl font-bold text-primary mb-6">Who We Are</h2>
            
            <p className="mb-4 text-lg">
              Strong Trendz is a full-service stock broking company with over 30+ years of experience in the financial markets. 
              We offer comprehensive investment solutions tailored to your specific financial goals and needs.
            </p>
            
            <p className="mb-4 text-lg">
              Our core focus is on providing exceptional services in equity trading and portfolio management. We believe in building 
              long-term relationships with our clients through transparency, reliability, and personalized service.
            </p>
            
            <p className="mb-4 text-lg">
              Each client is paired with a dedicated Relationship Manager who guides them through their wealth creation journey. 
              We combine traditional values with cutting-edge technology to deliver a seamless investment experience.
            </p>
            
            <h3 className="text-2xl font-bold text-primary mt-8 mb-4">Our Mission</h3>
            
            <p className="mb-4 text-lg">
              To empower investors with the knowledge, tools, and support they need to achieve their financial goals through 
              smart investment strategies and personalized guidance.
            </p>
            
            <h3 className="text-2xl font-bold text-primary mt-8 mb-4">Our Values</h3>
            
            <ul className="list-disc pl-6 mb-6 text-lg">
              <li className="mb-2">Integrity and transparency in all client interactions</li>
              <li className="mb-2">Commitment to excellence in service delivery</li>
              <li className="mb-2">Innovation in financial solutions</li>
              <li className="mb-2">Client-first approach in everything we do</li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
};

export default AboutUs;
