// If in Home.js
const Home = () => (
  <div>
    {/* Hero section - full height */}
    <div style={{
      position: 'relative',
      height: '100vh', // Changed from 500px to 100vh (full viewport height)
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
      
      <div style={{
        position: 'absolute',
        left: '10%', 
        top: '50%',
        transform: 'translateY(-50%)', 
        maxWidth: '600px',
        color: 'white',
        textShadow: '2px 2px 4px rgba(0,0,0,0.8)'
      }}>
        <h1 style={{
          fontSize: '42px', 
          marginBottom: '20px', 
          fontWeight: '800',
          fontFamily: "'Raleway', sans-serif",
          letterSpacing: '1px'
        }}>Your partner for innovative business solutions</h1>
      </div>
    </div>
    
    {/* Remove the entire "Our Services" section */}
  </div>
);

export default Home;