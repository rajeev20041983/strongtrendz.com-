// components/Dashboard.js
import React from 'react';
import { useAuth } from '../auth/AuthContext';

const Dashboard = () => {
  const { currentUser, userRole } = useAuth();

  // Determine content based on user role
  const renderContent = () => {
    if (userRole === 'admin') {
      return <AdminDashboard user={currentUser} />;
    } else {
      return <CustomerDashboard user={currentUser} />;
    }
  };

  return (
    <div className="py-8">
      <div className="container">
        {renderContent()}
      </div>
    </div>
  );
};

const AdminDashboard = ({ user }) => {
  return (
    <div>
      <h2 className="text-3xl font-bold text-primary mb-6">Admin Dashboard</h2>
      
      <div className="bg-white shadow-lg rounded-lg p-6 mb-8">
        <div className="border-b pb-4 mb-4">
          <h3 className="text-xl font-semibold">Welcome, Admin {user.email}</h3>
          <p className="text-gray-600">Here's an overview of your system</p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="text-3xl font-bold text-blue-600 mb-2">1,250</div>
            <div className="text-gray-700">Total Users</div>
          </div>
          
          <div className="bg-green-50 p-4 rounded-lg">
            <div className="text-3xl font-bold text-green-600 mb-2">₹4.2Cr</div>
            <div className="text-gray-700">Total Trading Volume</div>
          </div>
          
          <div className="bg-purple-50 p-4 rounded-lg">
            <div className="text-3xl font-bold text-purple-600 mb-2">87</div>
            <div className="text-gray-700">New Registrations</div>
          </div>
        </div>
        
        <div className="mb-6">
          <h4 className="text-lg font-semibold mb-4">Recent Activities</h4>
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2">User</th>
                <th className="text-left py-2">Activity</th>
                <th className="text-left py-2">Date & Time</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b">
                <td className="py-3">john.doe@example.com</td>
                <td className="py-3">Account Created</td>
                <td className="py-3">Today, 10:30 AM</td>
              </tr>
              <tr className="border-b">
                <td className="py-3">jane.smith@example.com</td>
                <td className="py-3">Updated Profile</td>
                <td className="py-3">Today, 09:15 AM</td>
              </tr>
              <tr className="border-b">
                <td className="py-3">mike.brown@example.com</td>
                <td className="py-3">Password Reset</td>
                <td className="py-3">Yesterday, 05:45 PM</td>
              </tr>
            </tbody>
          </table>
        </div>
        
        <div className="text-right">
          <a href="#" className="bg-primary text-white px-4 py-2 rounded">View All Activities</a>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white shadow-lg rounded-lg p-6">
          <h3 className="text-xl font-semibold mb-4">User Management</h3>
          <ul className="space-y-2">
            <li><a href="#" className="text-primary hover:underline">View All Users</a></li>
            <li><a href="#" className="text-primary hover:underline">Add New User</a></li>
            <li><a href="#" className="text-primary hover:underline">User Permissions</a></li>
            <li><a href="#" className="text-primary hover:underline">Account Approvals</a></li>
          </ul>
        </div>
        
        <div className="bg-white shadow-lg rounded-lg p-6">
          <h3 className="text-xl font-semibold mb-4">System Settings</h3>
          <ul className="space-y-2">
            <li><a href="#" className="text-primary hover:underline">General Settings</a></li>
            <li><a href="#" className="text-primary hover:underline">Email Templates</a></li>
            <li><a href="#" className="text-primary hover:underline">Security Settings</a></li>
            <li><a href="#" className="text-primary hover:underline">Backup & Restore</a></li>
          </ul>
        </div>
      </div>
    </div>
  );
};

const CustomerDashboard = ({ user }) => {
  return (
    <div>
      <h2 className="text-3xl font-bold text-primary mb-6">My Dashboard</h2>
      
      <div className="bg-white shadow-lg rounded-lg overflow-hidden mb-8">
        <div className="bg-primary text-white p-6">
          <h3 className="text-2xl font-semibold">Welcome Back!</h3>
          <p>Here's an overview of your portfolio and recent activities</p>
        </div>
        
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">Portfolio Value</div>
              <div className="text-2xl font-bold text-primary">₹7,56,245</div>
              <div className="text-sm text-green-600 mt-1">+2.4% Today</div>
            </div>
            
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">Available Funds</div>
              <div className="text-2xl font-bold text-primary">₹1,25,000</div>
              <div className="text-sm text-blue-600 mt-1">Ready to Invest</div>
            </div>
            
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">Today's P&L</div>
              <div className="text-2xl font-bold text-green-600">₹18,245</div>
              <div className="text-sm text-gray-600 mt-1">+2.4%</div>
            </div>
            
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">Total Investments</div>
              <div className="text-2xl font-bold text-primary">₹6,31,245</div>
              <div className="text-sm text-purple-600 mt-1">12 Active Positions</div>
            </div>
          </div>
          
          <div className="mb-8">
            <h4 className="text-xl font-semibold mb-4">Top Holdings</h4>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2">Stock</th>
                    <th className="text-left py-2">Qty</th>
                    <th className="text-left py-2">Avg. Price</th>
                    <th className="text-left py-2">LTP</th>
                    <th className="text-left py-2">P&L</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b">
                    <td className="py-3">Reliance Industries</td>
                    <td className="py-3">22</td>
                    <td className="py-3">₹2,354.20</td>
                    <td className="py-3">₹2,465.75</td>
                    <td className="py-3 text-green-600">+₹2,454.10 (+4.7%)</td>
                  </tr>
                  <tr className="border-b">
                    <td className="py-3">HDFC Bank</td>
                    <td className="py-3">30</td>
                    <td className="py-3">₹1,487.65</td>
                    <td className="py-3">₹1,524.35</td>
                    <td className="py-3 text-green-600">+₹1,101.00 (+2.5%)</td>
                  </tr>
                  <tr className="border-b">
                    <td className="py-3">Tata Motors</td>
                    <td className="py-3">120</td>
                    <td className="py-3">₹485.20</td>
                    <td className="py-3">₹501.75</td>
                    <td className="py-3 text-green-600">+₹1,986.00 (+3.4%)</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="text-right mt-4">
              <a href="#" className="text-primary hover:underline">View All Holdings</a>
            </div>
          </div>
          
          <div className="mb-8">
            <h4 className="text-xl font-semibold mb-4">Recent Transactions</h4>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2">Date</th>
                    <th className="text-left py-2">Type</th>
                    <th className="text-left py-2">Stock</th>
                    <th className="text-left py-2">Qty</th>
                    <th className="text-left py-2">Price</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b">
                    <td className="py-3">Today, 11:45 AM</td>
                    <td className="py-3"><span className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">BUY</span></td>
                    <td className="py-3">Infosys</td>
                    <td className="py-3">15</td>
                    <td className="py-3">₹1,742.50</td>
                  </tr>
                  <tr className="border-b">
                    <td className="py-3">Yesterday, 3:30 PM</td>
                    <td className="py-3"><span className="bg-red-100 text-red-800 px-2 py-1 rounded text-xs">SELL</span></td>
                    <td className="py-3">Bharti Airtel</td>
                    <td className="py-3">25</td>
                    <td className="py-3">₹875.25</td>
                  </tr>
                  <tr className="border-b">
                    <td className="py-3">25 Mar, 10:15 AM</td>
                    <td className="py-3"><span className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">BUY</span></td>
                    <td className="py-3">Tata Motors</td>
                    <td className="py-3">50</td>
                    <td className="py-3">₹485.20</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="text-right mt-4">
              <a href="#" className="text-primary hover:underline">View All Transactions</a>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <a href="#" className="block bg-primary text-white p-4 rounded-lg text-center hover:bg-primary-dark transition">
              <i className="fas fa-chart-line text-2xl mb-2"></i>
              <div>Place New Order</div>
            </a>
            
            <a href="#" className="block bg-secondary text-white p-4 rounded-lg text-center hover:bg-secondary-dark transition">
              <i className="fas fa-file-alt text-2xl mb-2"></i>
              <div>Account Statement</div>
            </a>
            
            <a href="#" className="block bg-gray-700 text-white p-4 rounded-lg text-center hover:bg-gray-800 transition">
              <i className="fas fa-headset text-2xl mb-2"></i>
              <div>Contact Support</div>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;