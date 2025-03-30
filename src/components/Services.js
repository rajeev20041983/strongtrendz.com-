import React from 'react';

const Services  = () => (
  <div>
    {/* Services Hero Section */}
    <div style={{
      position: 'relative',
      height: '350px',
      width: '100%',
      overflow: 'hidden',
      backgroundColor: '#004a8f'
    }}>
      <div style={{
        position: 'absolute',
        left: '10%', 
        top: '50%',
        transform: 'translateY(-50%)', 
        maxWidth: '800px',
        color: 'white',
        fontFamily: "'Montserrat', sans-serif"
      }}>
        <h1 style={{fontSize: '36px', marginBottom: '15px', fontWeight: '700'}}>Our Services</h1>
        <p style={{fontSize: '18px', lineHeight: '1.6'}}>Comprehensive solutions tailored to your business needs</p>
      </div>
    </div>
    
    {/* Services Cards Section */}
    <div style={{padding: '60px 20px', maxWidth: '1200px', margin: '0 auto', fontFamily: "'Montserrat', sans-serif"}}>
      <div style={{marginBottom: '40px', textAlign: 'center'}}>
        <h2 style={{fontSize: '28px', color: '#004a8f', marginBottom: '20px', fontWeight: '600'}}>What We Offer</h2>
        <p style={{fontSize: '16px', lineHeight: '1.8', color: '#333', maxWidth: '800px', margin: '0 auto'}}>
          Strong Trendz provides a range of services designed to help your business thrive in today's competitive landscape.
        </p>
      </div>
      
      <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', marginTop: '30px'}}>
        {/* Service Cards */}
        {[1, 2, 3].map((item, index) => (
          <div key={index} style={{
            flex: '0 0 30%', 
            marginBottom: '40px', 
            boxShadow: '0 4px 8px rgba(0,0,0,0.1)', 
            borderRadius: '8px',
            overflow: 'hidden',
            transition: 'transform 0.3s ease',
            cursor: 'pointer'
          }}>
            <div style={{height: '200px', backgroundColor: '#e0e0e0', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
              <div style={{fontSize: '48px', color: '#004a8f'}}>
                {index === 0 ? '📊' : index === 1 ? '💻' : '📱'}
              </div>
            </div>
            <div style={{padding: '25px'}}>
              <h3 style={{fontSize: '20px', color: '#004a8f', marginBottom: '15px', fontWeight: '600'}}>
                {index === 0 ? 'Business Consulting' : index === 1 ? 'Digital Transformation' : 'Software Solutions'}
              </h3>
              <p style={{fontSize: '15px', lineHeight: '1.7', color: '#333'}}>
                {index === 0 
                  ? 'Strategic guidance and actionable insights to optimize your business operations and drive growth.' 
                  : index === 1 
                    ? 'Comprehensive digital solutions to modernize your business and improve operational efficiency.' 
                    : 'Custom software development and integration to address your specific business challenges.'}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  </div>
);

export default Services ;