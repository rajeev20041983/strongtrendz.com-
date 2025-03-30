import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';

// Home component with image and enquiry form
const Home = () => (
  <div>
    {/* Hero section with full-width background and form */}
    <div style={{
      position: 'relative',
      height: '600px',
      width: '100%',
      overflow: 'hidden'
    }}>
      <img 
        src="/assets/images/home.jpg" 
        alt="Background" 
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          position: 'absolute'
        }}
      />
      
      {/* Left side content */}
      <div style={{
        position: 'absolute',
        left: '10%', 
        top: '50%',
        transform: 'translateY(-50%)', 
        maxWidth: '500px',
        color: 'white',
        textShadow: '2px 2px 4px rgba(0,0,0,0.8)'
      }}>
        <div style={{backgroundColor: 'rgba(0, 0, 0, 0.7)', padding: '10px 20px', display: 'inline-block', marginBottom: '20px'}}>
          <p style={{margin: 0, fontSize: '18px', fontWeight: 'bold'}}>We</p>
        </div>
        <h1 style={{
          fontSize: '48px', 
          marginBottom: '20px', 
          fontWeight: '800',
          fontFamily: "'Raleway', sans-serif",
          letterSpacing: '1px'
        }}>Make the Right Moves at the Right Time</h1>
        <p style={{fontSize: '20px', lineHeight: '1.6'}}></p>
      </div>
      
      {/* Enquiry Form */}
      <div style={{
        position: 'absolute',
        right: '10%',
        top: '50%',
        transform: 'translateY(-50%)',
        width: '350px',
        backgroundColor: 'white',
        boxShadow: '0 5px 15px rgba(0,0,0,0.2)',
        borderRadius: '5px',
        overflow: 'hidden'
      }}>
        <div style={{
          backgroundColor: '#0088cc', 
          color: 'white', 
          padding: '15px 20px',
          textAlign: 'center',
          fontSize: '20px',
          fontWeight: 'bold'
        }}>
          Enquiry Form
        </div>
        <div style={{padding: '20px'}}>
          <form>
            <div style={{marginBottom: '15px'}}>
              <input 
                type="text" 
                placeholder="Name" 
                style={{
                  width: '100%',
                  padding: '10px',
                  border: '1px solid #ddd',
                  borderRadius: '3px',
                  fontSize: '16px'
                }} 
              />
            </div>
            <div style={{marginBottom: '15px'}}>
              <input 
                type="tel" 
                placeholder="Phone Number" 
                style={{
                  width: '100%',
                  padding: '10px',
                  border: '1px solid #ddd',
                  borderRadius: '3px',
                  fontSize: '16px'
                }} 
              />
            </div>
            <div style={{marginBottom: '15px'}}>
              <input 
                type="email" 
                placeholder="Email" 
                style={{
                  width: '100%',
                  padding: '10px',
                  border: '1px solid #ddd',
                  borderRadius: '3px',
                  fontSize: '16px'
                }} 
              />
            </div>
            <div style={{marginBottom: '15px'}}>
              <label style={{display: 'flex', alignItems: 'center', fontSize: '14px', color: '#555'}}>
                <input type="checkbox" style={{marginRight: '10px'}} />
                I Agree to Terms & Conditions
              </label>
            </div>
            <button 
              type="submit" 
              style={{
                width: '100%',
                padding: '12px',
                backgroundColor: '#0088cc',
                color: 'white',
                border: 'none',
                borderRadius: '3px',
                fontSize: '16px',
                fontWeight: 'bold',
                cursor: 'pointer'
              }}
            >
              Submit
            </button>
          </form>
        </div>
      </div>
    </div>
    
    {/* Three links section below hero */}
    <div style={{
      padding: '40px 0',
      backgroundColor: '#f9f9f9',
      borderBottom: '1px solid #eee'
    }}>
      <div style={{
        maxWidth: '1200px',
        margin: '0 auto',
        display: 'flex',
        justifyContent: 'space-between',
        padding: '0 20px'
      }}>
        <div style={{textAlign: 'center', flex: '1', padding: '0 15px'}}>
          <h3 style={{
            color: '#004a8f',
            fontSize: '22px',
            marginBottom: '15px',
            fontFamily: "'Raleway', sans-serif",
            fontWeight: '700'
          }}>Share Market Advice</h3>
          <p style={{fontSize: '15px', lineHeight: '1.6', color: '#555'}}>
            Get expert insights and analysis for making informed investment decisions.
          </p>
        </div>
        <div style={{textAlign: 'center', flex: '1', padding: '0 15px'}}>
          <h3 style={{
            color: '#004a8f',
            fontSize: '22px',
            marginBottom: '15px',
            fontFamily: "'Raleway', sans-serif",
            fontWeight: '700'
          }}>Why Strong Trendz?</h3>
          <p style={{fontSize: '15px', lineHeight: '1.6', color: '#555'}}>
            Our proven track record and expert team make us the ideal partner for your business.
          </p>
        </div>
        <div style={{textAlign: 'center', flex: '1', padding: '0 15px'}}>
          <h3 style={{
            color: '#004a8f',
            fontSize: '22px',
            marginBottom: '15px',
            fontFamily: "'Raleway', sans-serif",
            fontWeight: '700'
          }}>Customer Support</h3>
          <p style={{fontSize: '15px', lineHeight: '1.6', color: '#555'}}>
            Dedicated assistance to help you navigate your business challenges.
          </p>
        </div>
      </div>
    </div>
  </div>
);

// About component
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

// Services component
const Services = () => (
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

function App() {
  return (
    <div style={{
      display: 'flex', 
      flexDirection: 'column', 
      minHeight: '100vh',
      fontFamily: "'Montserrat', sans-serif"
    }}>
      {/* Top blue bar with contact info and social links */}
      <header style={{backgroundColor: '#004a8f', color: 'white', padding: '10px 0'}}>
        <div style={{maxWidth: '1200px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
          <div>
            <a href="mailto:cs@strongtrendz.com" style={{color: 'white', marginRight: '15px', textDecoration: 'none'}}>cs@strongtrendz.com</a>
            <a href="tel:02692-225000" style={{color: 'white', textDecoration: 'none'}}>02692-225000</a>
          </div>
          <div style={{display: 'flex', alignItems: 'center'}}>
            <div style={{marginRight: '20px'}}>
              <strong>Customer Care</strong><br/>
              <a href="tel:02692-225000" style={{color: 'white', textDecoration: 'none', fontWeight: 'bold'}}>02692-225000</a>
            </div>
            <div>
              <a href="https://facebook.com" target="_blank" rel="noopener noreferrer" style={{color: 'white', marginRight: '15px', textDecoration: 'none'}}>Facebook</a>
              <a href="https://twitter.com" target="_blank" rel="noopener noreferrer" style={{color: 'white', marginRight: '15px', textDecoration: 'none'}}>Twitter</a>
              <a href="https://instagram.com" target="_blank" rel="noopener noreferrer" style={{color: 'white', textDecoration: 'none'}}>Instagram</a>
            </div>
          </div>
        </div>
      </header>
      
      {/* Navigation with Strong Trendz Advisory logo and menu */}
      <nav style={{backgroundColor: 'white', padding: '15px 0', borderBottom: '1px solid #eee'}}>
        <div style={{maxWidth: '1200px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
          <Link to="/" style={{
            textDecoration: 'none',
            display: 'flex',
            alignItems: 'center'
          }}>
            <div style={{
              backgroundColor: '#004a8f',
              width: '50px',
              height: '50px',
              borderRadius: '50%',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              marginRight: '10px',
              color: 'white',
              fontSize: '24px',
              fontWeight: 'bold'
            }}>S</div>
            <div>
              <div style={{
                fontSize: '24px', 
                fontWeight: '800', 
                color: '#004a8f', 
                fontFamily: "'Raleway', sans-serif",
                letterSpacing: '1px',
                lineHeight: '1'
              }}>
                STRONG TRENDZ
              </div>
              <div style={{
                fontSize: '16px',
                color: '#666',
                fontWeight: '400'
              }}>
                Investment Advisor
              </div>
            </div>
          </Link>
          <div>
            <Link to="/" style={{color: '#004a8f', marginRight: '20px', textDecoration: 'none', fontWeight: 'bold'}}>HOME</Link>
            <Link to="/about" style={{color: '#004a8f', marginRight: '20px', textDecoration: 'none', fontWeight: 'bold'}}>ABOUT US</Link>
            <Link to="/services" style={{color: '#004a8f', marginRight: '20px', textDecoration: 'none', fontWeight: 'bold'}}>SERVICES</Link>
            <button style={{backgroundColor: '#004a8f', color: 'white', border: 'none', padding: '8px 15px', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold'}}>LOGIN</button>
          </div>
        </div>
      </nav>
      
      {/* Main content area with routes */}
      <main style={{flex: '1'}}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/about" element={<About />} />
          <Route path="/services" element={<Services />} />
        </Routes>
      </main>
      
      {/* Footer */}
      <footer style={{
        backgroundColor: 'black', 
        color: 'white', 
        padding: '20px 0', 
        width: '100%'
      }}>
        <div style={{maxWidth: '1200px', margin: '0 auto', padding: '0 20px', textAlign: 'center'}}>
          <p style={{margin: '0 0 15px 0'}}>© 2023 Strong Trendz. All rights reserved.</p>
          <div>
            <a href="https://facebook.com" target="_blank" rel="noopener noreferrer" style={{color: 'white', margin: '0 15px', textDecoration: 'none'}}>Facebook</a>
            <a href="https://twitter.com" target="_blank" rel="noopener noreferrer" style={{color: 'white', margin: '0 15px', textDecoration: 'none'}}>Twitter</a>
            <a href="https://instagram.com" target="_blank" rel="noopener noreferrer" style={{color: 'white', margin: '0 15px', textDecoration: 'none'}}>Instagram</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;