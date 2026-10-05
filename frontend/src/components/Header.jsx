import React, { useState } from 'react';
import { Landmark, ShieldCheck, UserCheck, ShieldAlert, LogOut, Bell, Menu, X, Shield, Lock, FileText, HelpCircle } from 'lucide-react';

export default function Header({
  currentUser,
  activeTab,
  onTabChange,
  onLogout,
  unreadCount = 0
}) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const isAdmin = currentUser?.role === 'admin';

  function handleTabClick(tab) {
    onTabChange(tab);
    setMobileMenuOpen(false);
  }

  return (
    <header className="bg-slate-900 border-b border-slate-800 text-white sticky top-0 z-30 shadow-sm">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand / Title */}
        <button
          type="button"
          onClick={() => handleTabClick(isAdmin ? 'admin' : 'home')}
          className="flex items-center space-x-3 text-left focus:outline-none focus:ring-2 focus:ring-blue-400 rounded-lg p-1"
        >
          <div className="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-sm ring-1 ring-blue-400/30">
            <Landmark className="w-5 h-5" aria-hidden="true" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold tracking-tight text-white leading-none">
                CivicFlow
              </span>

            </div>
            <p className="text-[11px] text-slate-400 font-normal mt-0.5 hidden sm:block">
              Municipal Issue Intake, AI Drafting & Adjudication
            </p>
          </div>
        </button>

        {/* Desktop Navigation */}
        <div className="hidden md:flex items-center space-x-3">
          <nav aria-label="Main Navigation" className="flex items-center bg-slate-800 p-1 rounded-lg border border-slate-700 text-xs">
            {isAdmin ? (
              <>
                <button
                  type="button"
                  onClick={() => handleTabClick('admin')}
                  className={`px-3 py-1.5 rounded-md font-medium transition focus:outline-none focus:ring-2 focus:ring-blue-400 ${activeTab === 'admin'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-300 hover:text-white'
                    }`}
                >
                  Admin Adjudication
                </button>
                <button
                  type="button"
                  onClick={() => handleTabClick('home')}
                  className={`px-3 py-1.5 rounded-md font-medium transition focus:outline-none focus:ring-2 focus:ring-blue-400 ${activeTab === 'home'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-300 hover:text-white'
                    }`}
                >
                  Public View
                </button>
              </>
            ) : currentUser ? (
              <>
                <button
                  type="button"
                  onClick={() => handleTabClick('home')}
                  className={`px-3 py-1.5 rounded-md font-medium transition focus:outline-none focus:ring-2 focus:ring-blue-400 ${activeTab === 'home'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-300 hover:text-white'
                    }`}
                >
                  Home
                </button>
                <button
                  type="button"
                  onClick={() => handleTabClick('how-it-works')}
                  className={`px-3 py-1.5 rounded-md font-medium transition focus:outline-none focus:ring-2 focus:ring-blue-400 ${activeTab === 'how-it-works'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-300 hover:text-white'
                    }`}
                >
                  How It Works
                </button>
                <button
                  type="button"
                  onClick={() => handleTabClick('report')}
                  className={`px-3 py-1.5 rounded-md font-medium transition focus:outline-none focus:ring-2 focus:ring-blue-400 ${activeTab === 'report'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-300 hover:text-white'
                    }`}
                >
                  Report Issue
                </button>
                <button
                  type="button"
                  onClick={() => handleTabClick('my-complaints')}
                  className={`px-3 py-1.5 rounded-md font-medium transition focus:outline-none focus:ring-2 focus:ring-blue-400 ${activeTab === 'my-complaints'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-300 hover:text-white'
                    }`}
                >
                  My Complaints
                </button>
                <button
                  type="button"
                  onClick={() => handleTabClick('notifications')}
                  className={`px-3 py-1.5 rounded-md font-medium transition flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-blue-400 ${activeTab === 'notifications'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-300 hover:text-white'
                    }`}
                >
                  <Bell className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>Notifications</span>
                  {unreadCount > 0 && (
                    <span className="px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-blue-500 text-white leading-tight">
                      {unreadCount}
                    </span>
                  )}
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => handleTabClick('home')}
                  className={`px-3 py-1.5 rounded-md font-medium transition focus:outline-none focus:ring-2 focus:ring-blue-400 ${activeTab === 'home'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-300 hover:text-white'
                    }`}
                >
                  Home
                </button>
                <button
                  type="button"
                  onClick={() => handleTabClick('how-it-works')}
                  className={`px-3 py-1.5 rounded-md font-medium transition focus:outline-none focus:ring-2 focus:ring-blue-400 ${activeTab === 'how-it-works'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-300 hover:text-white'
                    }`}
                >
                  How It Works
                </button>
                <button
                  type="button"
                  onClick={() => handleTabClick('report')}
                  className={`px-3 py-1.5 rounded-md font-medium transition focus:outline-none focus:ring-2 focus:ring-blue-400 ${activeTab === 'report'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-300 hover:text-white'
                    }`}
                >
                  Report an Issue
                </button>
                <button
                  type="button"
                  onClick={() => handleTabClick('admin')}
                  className={`px-3 py-1.5 rounded-md font-medium transition inline-flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-blue-400 ${activeTab === 'admin'
                    ? 'bg-slate-900 text-blue-300 border border-slate-600 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                    }`}
                >
                  <Lock className="w-3 h-3 text-slate-400" aria-hidden="true" />
                  <span>Admin Portal</span>
                </button>
              </>
            )}
          </nav>

          {/* User Session Info */}
          {currentUser && (
            <div className="flex items-center space-x-2 pl-2 border-l border-slate-800">
              <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-[11px] font-medium border ${isAdmin
                ? 'bg-purple-950/70 text-purple-200 border-purple-800'
                : 'bg-blue-950/70 text-blue-200 border-blue-800'
                }`}>
                {isAdmin ? (
                  <ShieldAlert className="w-3.5 h-3.5 mr-1 text-purple-400" aria-hidden="true" />
                ) : (
                  <UserCheck className="w-3.5 h-3.5 mr-1 text-blue-400" aria-hidden="true" />
                )}
                <span>{isAdmin ? 'Admin' : 'Citizen'}: {currentUser.name ? currentUser.name.split(' ')[0] : 'User'}</span>
              </span>
              {onLogout && (
                <button
                  type="button"
                  onClick={onLogout}
                  title="Sign out of CivicFlow"
                  aria-label="Sign out of CivicFlow"
                  className="text-xs text-slate-400 hover:text-white p-1.5 hover:bg-slate-800 rounded-md transition focus:outline-none focus:ring-2 focus:ring-blue-400"
                >
                  <LogOut className="w-4 h-4" aria-hidden="true" />
                </button>
              )}
            </div>
          )}
        </div>

        {/* Mobile menu button */}
        <div className="flex items-center md:hidden gap-2">
          {currentUser && !isAdmin && unreadCount > 0 && (
            <button
              type="button"
              onClick={() => handleTabClick('notifications')}
              className="relative p-1.5 text-slate-300 hover:text-white"
              aria-label={`You have ${unreadCount} unread notifications`}
            >
              <Bell className="w-5 h-5" />
              <span className="absolute top-0.5 right-0.5 w-2 h-2 rounded-full bg-blue-500 ring-2 ring-slate-900" />
            </button>
          )}

          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-expanded={mobileMenuOpen}
            aria-label="Toggle navigation menu"
            className="p-2 rounded-md text-slate-300 hover:text-white hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile dropdown menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-800 bg-slate-900 px-4 pt-3 pb-4 space-y-2">
          {currentUser ? (
            <>
              <div className="flex items-center justify-between pb-3 border-b border-slate-800 text-xs">
                <span className="text-slate-300 font-medium flex items-center gap-1.5">
                  {isAdmin ? <ShieldAlert className="w-4 h-4 text-purple-400" /> : <UserCheck className="w-4 h-4 text-blue-400" />}
                  {currentUser.name} ({currentUser.role})
                </span>
                {onLogout && (
                  <button
                    type="button"
                    onClick={onLogout}
                    className="text-xs text-rose-400 hover:text-rose-300 flex items-center gap-1"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    <span>Sign out</span>
                  </button>
                )}
              </div>

              {isAdmin ? (
                <>
                  <button
                    type="button"
                    onClick={() => handleTabClick('admin')}
                    className={`w-full text-left px-3 py-2 rounded-lg text-xs font-semibold ${activeTab === 'admin' ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                      }`}
                  >
                    Admin Adjudication Dashboard
                  </button>
                  <button
                    type="button"
                    onClick={() => handleTabClick('home')}
                    className={`w-full text-left px-3 py-2 rounded-lg text-xs font-semibold ${activeTab === 'home' ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                      }`}
                  >
                    Public View
                  </button>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => handleTabClick('home')}
                    className={`w-full text-left px-3 py-2 rounded-lg text-xs font-semibold ${activeTab === 'home' ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                      }`}
                  >
                    Home
                  </button>
                  <button
                    type="button"
                    onClick={() => handleTabClick('how-it-works')}
                    className={`w-full text-left px-3 py-2 rounded-lg text-xs font-semibold ${activeTab === 'how-it-works' ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                      }`}
                  >
                    How It Works
                  </button>
                  <button
                    type="button"
                    onClick={() => handleTabClick('report')}
                    className={`w-full text-left px-3 py-2 rounded-lg text-xs font-semibold ${activeTab === 'report' ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                      }`}
                  >
                    Report Issue
                  </button>
                  <button
                    type="button"
                    onClick={() => handleTabClick('my-complaints')}
                    className={`w-full text-left px-3 py-2 rounded-lg text-xs font-semibold ${activeTab === 'my-complaints' ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                      }`}
                  >
                    My Complaints
                  </button>
                  <button
                    type="button"
                    onClick={() => handleTabClick('notifications')}
                    className={`w-full text-left px-3 py-2 rounded-lg text-xs font-semibold flex items-center justify-between ${activeTab === 'notifications' ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                      }`}
                  >
                    <span>Notifications</span>
                    {unreadCount > 0 && (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-500 text-white">
                        {unreadCount}
                      </span>
                    )}
                  </button>
                </>
              )}
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={() => handleTabClick('home')}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs font-semibold ${activeTab === 'home' ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                  }`}
              >
                Home
              </button>
              <button
                type="button"
                onClick={() => handleTabClick('how-it-works')}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs font-semibold ${activeTab === 'how-it-works' ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                  }`}
              >
                How It Works
              </button>
              <button
                type="button"
                onClick={() => handleTabClick('report')}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs font-semibold ${activeTab === 'report' ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                  }`}
              >
                Report an Issue
              </button>
              <button
                type="button"
                onClick={() => handleTabClick('admin')}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 ${activeTab === 'admin' ? 'bg-slate-800 text-blue-300' : 'text-slate-400 hover:bg-slate-800'
                  }`}
              >
                <Lock className="w-3.5 h-3.5" />
                <span>Admin Portal</span>
              </button>
            </>
          )}
        </div>
      )}
    </header>
  );
}
