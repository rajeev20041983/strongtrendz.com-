import React from 'react';
import { Routes, Route } from 'react-router-dom';
import TestHeader from './components/TestHeader'; 
// Import pages once you create them
// import Home from './pages/Home';
// import About from './pages/About';

function App() {
  return (
    <div className="App">
      <header className="bg-primary text-white p-4">
        <h1 className="text-2xl font-bold">Strong Trendz</h1>
      </header>
      
      <main className="container mx-auto p-4">
        <Routes>
          <Route path="/" element={<div>Home Page Coming Soon</div>} />
          <Route path="/about" element={<div>About Page Coming Soon</div>} />
          {/* Add more routes as you build pages */}
        </Routes>
      </main>
      
      <footer className="bg-gray-800 text-white p-4 mt-8">
        <p className="text-center">© 2025 Strong Trendz. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default App;