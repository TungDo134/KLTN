/*
 Layout Component
 */

import { useState } from "react";
import { Outlet } from "react-router-dom";

import Sidebar from "../features/navigation/Sidebar";
import Topbar from "../features/navigation/TopBar";

import "../index.css";

function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [desktopOpen, setDesktopOpen] = useState(true);
  const [conversationRefreshKey, setConversationRefreshKey] = useState(0);

  const handleConversationChanged = () => {
    setConversationRefreshKey((key) => key + 1);
  };

  return (
    <div className="flex h-screen bg-[var(--bg-main)] text-[var(--text-main)] overflow-hidden">
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <Sidebar 
        mobileOpen={mobileOpen} 
        desktopOpen={desktopOpen}
        refreshKey={conversationRefreshKey}
        onMobileClose={() => setMobileOpen(false)} 
        onDesktopToggle={() => setDesktopOpen(!desktopOpen)}
      />

      {/* Right side (Topbar + Content) */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Topbar */}
        <Topbar 
          onMobileMenuToggle={() => setMobileOpen(true)}
          onDesktopMenuToggle={() => setDesktopOpen(!desktopOpen)}
          desktopSidebarOpen={desktopOpen}
        />

        {/* Main content */}
        <div className="flex-1 overflow-hidden">
          <Outlet context={{ onConversationChanged: handleConversationChanged }} />
        </div>
      </div>
    </div>
  );
}

export default AppLayout;
