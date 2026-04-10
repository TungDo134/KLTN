/*
 Layout Component
 */

import { Outlet } from "react-router-dom";

import Sidebar from "../features/navigation/Sidebar";
import Topbar from "../features/navigation/TopBar";

import "../index.css";

function AppLayout() {
  return (
    <div className="flex h-screen bg-[#212121] text-white">
      {/* Sidebar */}
      <Sidebar />

      {/* Right side (Topbar + Content) */}
      <div className="flex-1 flex flex-col">
        {/* Topbar */}
        <Topbar />

        {/* Main content */}
        <div className="flex-1 overflow-hidden">
          <Outlet />
        </div>
      </div>
    </div>
  );
}

export default AppLayout;
