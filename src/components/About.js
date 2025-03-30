import React from 'react';

const About = () => (
  <div>
    {/* About Hero Section */}
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
        <h1 style={{fontSize: '36px', marginBottom: '15px', fontWeight: '700'}}>About Strong Trendz</h1>
        <p style={{fontSize: '18px', lineHeight: '1.6'}}>Learn about our mission, vision, and the team behind our success</p>
      </div>
    </div>
    
    {/* Main Content Section */}
    <div style={{padding: '60px 20px', maxWidth: '1200px', margin: '0 auto', fontFamily: "'Montserrat', sans-serif"}}>
      <div style={{marginBottom: '40px'}}>
        <h2 style={{fontSize: '28px', color: '#004a8f', marginBottom: '20px', fontWeight: '600'}}>Our Story</h2>
        <p style={{fontSize: '16px', lineHeight: '1.8', color: '#333'}}>
          Founded in 2010, Strong Trendz has been at the forefront of business innovation and technology integration. 
          What started as a small consulting firm has grown into a comprehensive business solutions provider 
          helping companies across multiple industries achieve their goals through strategic planning and implementation.
        </p>
        <p style={{fontSize: '16px', lineHeight: '1.8', color: '#333', marginTop: '20px'}}>
          Our journey has been defined by our commitment to excellence, our dedication to our clients, 
          and our ability to adapt to the ever-changing business landscape.
        </p>
      </div>
      
      <div style={{display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', marginTop: '50px'}}>
        <div style={{flex: '0 0 48%', marginBottom: '30px'}}>
          <h3 style={{fontSize: '22px', color: '#004a8f', marginBottom: '15px', fontWeight: '600'}}>Our Mission</h3>
          <p style={{fontSize: '16px', lineHeight: '1.8', color: '#333'}}>
            To empower businesses with innovative solutions that drive growth, efficiency, and competitive advantage 
            in an increasingly digital world.
          </p>
        </div>
        <div style={{flex: '0 0 48%', marginBottom: '30px'}}>
          <h3 style={{fontSize: '22px', color: '#004a8f', marginBottom: '15px', fontWeight: '600'}}>Our Vision</h3>
          <p style={{fontSize: '16px', lineHeight: '1.8', color: '#333'}}>
            To be the leading provider of business transformation services, recognized for our expertise, 
            integrity, and the measurable value we create for our clients.
          </p>
        </div>
      </div>
    </div>
  </div>
);

export default About;