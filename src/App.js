import React from 'react';
// No other imports for now

function App() {
  return (
    <div>
      <div style={{backgroundColor: 'blue', color: 'white', padding: '20px'}}>
        This should be a blue header
      </div>
      
      <div style={{padding: '20px'}}>
        Main content area
      </div>
      
      <div style={{backgroundColor: 'black', color: 'white', padding: '10px', textAlign: 'center'}}>
        Footer area
      </div>
    </div>
  );
}

export default App;