import React, { useEffect, useState } from 'react';
import '@/App.css';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import { Toaster } from '@/components/ui/sonner';
import { toast } from 'sonner';

import Navbar from '@/components/Navbar';
import Home from '@/pages/Home';
import EventDetails from '@/pages/EventDetails';
import CreateEvent from '@/pages/CreateEvent';
import MyEvents from '@/pages/MyEvents';
import MyBookings from '@/pages/MyBookings';
import BookingSuccess from '@/pages/BookingSuccess';
import AdminDashboard from '@/pages/AdminDashboard';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const AuthContext = React.createContext();

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showRoleSelection, setShowRoleSelection] = useState(false);

  useEffect(() => {
    // Check for session_id in URL hash (after OAuth)
    const hash = window.location.hash;
    if (hash && hash.includes('session_id=')) {
      const sessionId = hash.split('session_id=')[1].split('&')[0];
      handleSessionId(sessionId);
    } else {
      // Check existing session
      checkAuth();
    }
  }, []);

  const handleSessionId = async (sessionId) => {
    try {
      const response = await axios.post(`${API}/auth/session`, null, {
        headers: { 'X-Session-ID': sessionId },
        withCredentials: true
      });
      
      // Clean URL
      window.location.hash = '';
      
      // Get user data
      await checkAuth();
      
      // Show role selection for new users
      if (response.data.is_new_user) {
        setShowRoleSelection(true);
      }
    } catch (error) {
      console.error('Session creation failed:', error);
      toast.error('Authentication failed');
      setLoading(false);
    }
  };

  const checkAuth = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`, {
        withCredentials: true
      });
      setUser(response.data);
    } catch (error) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = () => {
    const redirectUrl = window.location.origin + '/events';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const logout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, null, { withCredentials: true });
      setUser(null);
      toast.success('Logged out successfully');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const selectRole = async (role) => {
    try {
      await axios.patch(`${API}/auth/select-role`, { role }, { withCredentials: true });
      setShowRoleSelection(false);
      await checkAuth();
      toast.success(`Role set to ${role}`);
    } catch (error) {
      console.error('Role selection failed:', error);
      toast.error('Failed to set role');
    }
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, checkAuth, selectRole }}>
      <div className="App">
        {/* Role Selection Modal */}
        {showRoleSelection && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4">
              <h2 className="text-2xl font-bold mb-4">Choose Your Role</h2>
              <p className="text-gray-600 mb-6">
                Select how you'd like to use our platform. You can change this later.
              </p>
              <div className="space-y-3">
                <button
                  onClick={() => selectRole('attendee')}
                  className="w-full p-4 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition text-left"
                >
                  <div className="font-semibold text-lg">🎫 Attendee</div>
                  <div className="text-sm text-gray-600 mt-1">
                    Browse and book tickets for events
                  </div>
                </button>
                <button
                  onClick={() => selectRole('organizer')}
                  className="w-full p-4 border-2 border-gray-200 rounded-lg hover:border-purple-500 hover:bg-purple-50 transition text-left"
                >
                  <div className="font-semibold text-lg">🎪 Organizer</div>
                  <div className="text-sm text-gray-600 mt-1">
                    Create and manage events, plus book tickets
                  </div>
                </button>
              </div>
            </div>
          </div>
        )}
        <BrowserRouter>
          <Navbar />
          <Routes>
            <Route path="/" element={<Navigate to="/events" />} />
            <Route path="/events" element={<Home />} />
            <Route path="/events/:id" element={<EventDetails />} />
            <Route path="/create-event" element={user ? <CreateEvent /> : <Navigate to="/events" />} />
            <Route path="/my-events" element={user ? <MyEvents /> : <Navigate to="/events" />} />
            <Route path="/my-bookings" element={user ? <MyBookings /> : <Navigate to="/events" />} />
            <Route path="/booking-success" element={user ? <BookingSuccess /> : <Navigate to="/events" />} />
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" richColors />
      </div>
    </AuthContext.Provider>
  );
}

export default App;
