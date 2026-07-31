import { useState, useEffect, useRef } from "react";
import {
  FiChevronDown,
  FiEdit2,
  FiTrash2,
  FiInfo,
  FiMenu,
  FiSidebar,
} from "react-icons/fi";

export default function Topbar({
  onMobileMenuToggle,
  onDesktopMenuToggle,
  desktopSidebarOpen,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  return (
    <div className="h-14 flex items-center justify-between px-3 sm:px-4 bg-transparent mt-2 relative z-40">
      {/* Left */}
      <div className="flex items-center gap-2">
        {/* Hamburger menu - mobile only */}
        <button
          onClick={onMobileMenuToggle}
          className="p-2 hover:bg-(--color-surface-hover) rounded-lg transition-colors text-(--color-text-secondary) md:hidden"
        >
          <FiMenu size={20} />
        </button>

        {/* Sidebar toggle - desktop only (shows when sidebar is closed) */}
        {!desktopSidebarOpen && (
          <button
            onClick={onDesktopMenuToggle}
            className="p-2 hover:bg-(--color-surface-hover) rounded-lg transition-colors text-(--color-text-secondary) hidden md:block"
          >
            <FiSidebar size={20} />
          </button>
        )}
      </div>

      {/* Right */}
      <div className="flex items-center gap-4"></div>
    </div>
  );
}
