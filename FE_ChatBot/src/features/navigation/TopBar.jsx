import { useState, useEffect, useRef } from "react";
import { FiChevronDown, FiEdit2, FiTrash2, FiInfo } from "react-icons/fi";

export default function Topbar() {
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
    <div className="h-14 flex items-center justify-between px-4 bg-transparent mt-2 relative z-40">
      {/* Left */}
      <div className="relative" ref={dropdownRef}>
        <div 
          className="flex items-center gap-2 cursor-pointer hover:bg-[var(--bg-hover)] px-3 py-1.5 rounded-lg transition text-[var(--text-main)]"
          onClick={() => setIsOpen(!isOpen)}
        >
          <span className="text-sm font-medium">Chatbot</span>
          <FiChevronDown className="text-gray-400" size={16} />
        </div>

        {/* Dropdown Menu */}
        {isOpen && (
          <div className="absolute top-full left-0 mt-1 w-48 bg-[var(--bg-panel)] rounded-xl shadow-2xl border border-[var(--border-main)] py-1 overflow-hidden z-50">
            <button className="flex items-center gap-3 w-full px-4 py-2.5 text-[13px] text-[var(--text-main)] hover:bg-[var(--bg-hover)] transition-colors text-left">
              <FiEdit2 size={14} className="text-gray-400" /> Đổi tên
            </button>
            <button className="flex items-center gap-3 w-full px-4 py-2.5 text-[13px] text-[var(--text-main)] hover:bg-[var(--bg-hover)] transition-colors text-left">
              <FiInfo size={14} className="text-gray-400" /> Thông tin
            </button>
            <div className="border-t border-[var(--border-main)] my-1"></div>
            <button className="flex items-center gap-3 w-full px-4 py-2.5 text-[13px] text-red-400 hover:bg-[var(--bg-hover)] transition-colors text-left">
              <FiTrash2 size={14} /> Xóa hội thoại
            </button>
          </div>
        )}
      </div>

      {/* Right */}
      <div className="flex items-center gap-4">
        <button className="flex items-center gap-2 border border-[var(--border-main)] bg-transparent hover:bg-[var(--bg-hover)] px-3 py-1.5 rounded-lg transition text-[var(--text-main)]">
          <span className="text-[13px] font-medium">Share</span>
        </button>
      </div>
    </div>
  );
}
