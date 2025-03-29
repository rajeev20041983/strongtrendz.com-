import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './index.css';
import SimpleHeader from './SimpleHeader';

const HomePage = () => <div style={{padding: '20px'}}>Home Page Content</div>;
const AboutPage = () => <div style={{padding: '20px'}}>About Page Content</div>;
const ServicesPage = () => <div style={{padding: '20px'}}>Services Page Content</div>;

const MinimalApp = () => {
  return (
    <BrowserRouter>
      <div>
        <SimpleHeader />
        <main>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/services" element={<ServicesPage />} />
          </Routes>
        </main>
        <footer style={{backgroundColor: 'black', color: 'white', padding: '10px', textAlign: 'center'}}>
          Footer
        </footer>
      </div>
    </BrowserRouter>
  );
};

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<MinimalApp />);