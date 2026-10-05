import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Home from './pages/Home';
import HowItWorks from './pages/HowItWorks';
import CitizenDashboard from './components/CitizenDashboard';
import ComplaintIntakeForm from './components/ComplaintIntakeForm';
import AdminAdjudicationDashboard from './components/AdminAdjudicationDashboard';
import AdminLogin from './components/AdminLogin';
import CitizenNotifications from './components/CitizenNotifications';
import { fetchCurrentUser, clearStoredToken } from './services/auth';
import { fetchUnreadCount } from './services/notifications';
import { ShieldAlert } from 'lucide-react';

export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [activeTab, setActiveTab] = useState('home'); // 'home', 'how-it-works', 'report', 'my-complaints', 'notifications', 'admin'
  const [unreadCount, setUnreadCount] = useState(0);
  const [selectedComplaintId, setSelectedComplaintId] = useState(null);

  async function refreshUnreadCount(user) {
    if (!user || user.role === 'admin') {
      setUnreadCount(0);
      return;
    }
    try {
      const count = await fetchUnreadCount();
      setUnreadCount(count);
    } catch {
      // Ignored
    }
  }

  useEffect(() => {
    async function initUser() {
      try {
        const user = await fetchCurrentUser();
        setCurrentUser(user);
        if (user?.role === 'admin') {
          setActiveTab('admin');
        } else if (user) {
          refreshUnreadCount(user);
        }
      } catch {
        // Ignored
      }
    }
    initUser();
  }, []);

  function handleUserChange(user) {
    setCurrentUser(user);
    if (user?.role === 'admin') {
      setActiveTab('admin');
    } else {
      refreshUnreadCount(user);
    }
  }

  function handleLogout() {
    clearStoredToken();
    setCurrentUser(null);
    setUnreadCount(0);
    setSelectedComplaintId(null);
    setActiveTab('home');
  }

  function handleTabChange(tab) {
    if (tab === 'report') {
      setSelectedComplaintId(null);
    }
    setActiveTab(tab);
    if (currentUser) {
      refreshUnreadCount(currentUser);
    }
  }

  function handleSelectComplaint(complaintId) {
    setSelectedComplaintId(complaintId);
    setActiveTab('report');
  }

  function handleNotificationRead() {
    if (currentUser) {
      refreshUnreadCount(currentUser);
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <Header
        currentUser={currentUser}
        activeTab={activeTab}
        onTabChange={handleTabChange}
        onLogout={handleLogout}
        unreadCount={unreadCount}
      />

      <main className="flex-1 w-full">
        {activeTab === 'admin' ? (
          currentUser?.role === 'admin' ? (
            <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
              <AdminAdjudicationDashboard currentUser={currentUser} />
            </div>
          ) : !currentUser ? (
            <AdminLogin
              onAdminLoginSuccess={handleUserChange}
              onCancel={() => setActiveTab('home')}
            />
          ) : (
            <div className="max-w-2xl mx-auto px-4 py-16 text-center">
              <div className="w-12 h-12 rounded-full bg-rose-50 border border-rose-200 flex items-center justify-center mx-auto mb-3 text-rose-600">
                <ShieldAlert className="w-6 h-6" aria-hidden="true" />
              </div>
              <h3 className="text-base font-semibold text-slate-900">
                403 Forbidden: Administrative Privileges Required
              </h3>
              <p className="text-xs text-slate-600 mt-1 max-w-md mx-auto">
                You do not have permission to access the municipal adjudication dashboard. Only authorized administrators may review and adjudicate submitted complaints.
              </p>
              <button
                type="button"
                onClick={() => setActiveTab('home')}
                className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold transition shadow-sm"
              >
                Return to Citizen Portal
              </button>
            </div>
          )
        ) : activeTab === 'notifications' ? (
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <CitizenNotifications
              onSelectComplaint={handleSelectComplaint}
              onNotificationRead={handleNotificationRead}
            />
          </div>
        ) : activeTab === 'how-it-works' ? (
          <HowItWorks
            onNavigateReport={() => {
              setSelectedComplaintId(null);
              setActiveTab('report');
            }}
          />
        ) : activeTab === 'my-complaints' ? (
          <CitizenDashboard
            currentUser={currentUser}
            onNavigateReport={() => {
              setSelectedComplaintId(null);
              setActiveTab('report');
            }}
            onSelectComplaint={handleSelectComplaint}
          />
        ) : activeTab === 'report' ? (
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <ComplaintIntakeForm
              onUserChange={handleUserChange}
              selectedComplaintId={selectedComplaintId}
              onNavigateAdmin={() => setActiveTab('admin')}
            />
          </div>
        ) : (
          <Home
            currentUser={currentUser}
            onNavigateReport={() => {
              setSelectedComplaintId(null);
              setActiveTab('report');
            }}
            onNavigateHowItWorks={() => setActiveTab('how-it-works')}
            onNavigateAdmin={() => setActiveTab('admin')}
          />
        )}
      </main>
    </div>
  );
}
