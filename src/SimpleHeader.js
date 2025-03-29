import React from 'react';
import { Link } from 'react-router-dom';

const SimpleHeader = () => {
  return (
    <>
      <div style={{backgroundColor: '#004a8f', color: 'white', padding: '10px'}}>
        <div style={{width: '90%', maxWidth: '1200px', margin: '0 auto', display: 'flex', justifyContent: 'space-between'}}>
          <div>
            <a href="mailto:cs@strongtrendz.com" style={{color: 'white', marginRight: '15px'}}>
              cs@strongtrendz.com
            </a>
            <a href="tel:02692-225000" style={{color: 'white'}}>
              02692-225000
            </a>
          </div>
          <div>
            <span style={{marginLeft: '10px'}}>Facebook</span>
            <span style={{marginLeft: '10px'}}>Twitter</span>
            <span style={{marginLeft: '10px'}}>Instagram</span>
          </div>
        </div>
      </div>
      
      <header style={{padding: '15px 0', boxShadow: '0 2px 5px rgba(0,0,0,0.1)', backgroundColor: 'white'}}>
        <div style={{width: '90%', maxWidth: '1200px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
          <div>
            <Link to="/" style={{fontSize: '24px', fontWeight: 'bold', color: '#004a8f'}}>Strong Trendz</Link>
          </div>
          
          <nav>
            <Link to="/" style={{marginLeft: '20px', color: '#004a8f'}}>Home</Link>
            <Link to="/about" style={{marginLeft: '20px', color: '#004a8f'}}>About Us</Link>
            <Link to="/services" style={{marginLeft: '20px', color: '#004a8f'}}>Services</Link>
            <button 
              style={{marginLeft: '20px', backgroundColor: '#004a8f', color: 'white', padding: '8px 16px', border: 'none', borderRadius: '4px'}}
            >
              LOGIN
            </button>
          </nav>
        </div>
      </header>
    </>
  );
};

export default SimpleHeader;