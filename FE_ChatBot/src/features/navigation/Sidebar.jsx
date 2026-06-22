import { useEffect, useState } from "react";
import {
  IoAddOutline,
  IoSearchOutline,
  IoChatbubblesOutline,
  IoCloseOutline,
} from "react-icons/io5";
import {
  FiBriefcase,
  FiFolder,
  FiDownload,
  FiSidebar,
  FiSettings,
  FiLogOut,
  FiLogIn,
} from "react-icons/fi";
import {
  HiOutlineTemplate,
  HiSelector,
  HiOutlineSparkles,
} from "react-icons/hi";
import LoginModal from "./LoginModal";
import { getStoredAuthUser, logout } from "../../services/authApi";

function Sidebar({ mobileOpen, desktopOpen, onMobileClose, onDesktopToggle }) {
  const [openUserMenu, setOpenUserMenu] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [currentUser, setCurrentUser] = useState(() => getStoredAuthUser());

  const isLoggedIn = Boolean(currentUser);
  const displayName = currentUser?.full_name || currentUser?.email || "User";
  const displayEmail = currentUser?.email || "";
  const initials = displayName
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();

  const handleLogout = async () => {
    await logout();
    setCurrentUser(null);
    setOpenUserMenu(false);
  };

  // Click outside => close
  useEffect(() => {
    const handleClick = () => setOpenUserMenu(false);
    window.addEventListener("click", handleClick);
    return () => window.removeEventListener("click", handleClick);
  }, []);

  const chats = [
    "Lịch trình Đà Lạt 3 ngày",
    "Du lịch Hà Nội",
    "Khách sạn Phú Quốc",
  ];

  return (
    <div
      className={`
        w-65 bg-(--bg-sidebar) flex flex-col h-full text-(--text-main) shrink-0
        fixed md:static inset-y-0 left-0 z-50
        transition-all duration-300 ease-in-out
        ${mobileOpen ? "translate-x-0" : "-translate-x-full"}
        ${desktopOpen ? "md:ml-0" : "md:-ml-65"}
        md:translate-x-0
      `}
    >
      {/* Header */}
      <div className="px-4 py-3 flex items-center justify-between">
        <h1 className="font-serif text-[19px] tracking-wide font-medium whitespace-nowrap">
          Mellow AI
        </h1>
        <div className="flex items-center gap-1">
          {/* Close button - mobile only */}
          <button
            onClick={onMobileClose}
            className="p-1.5 hover:bg-(--bg-hover) rounded-md text-gray-400 transition-colors md:hidden"
          >
            <IoCloseOutline size={20} />
          </button>
          <button
            onClick={onDesktopToggle}
            className="p-1.5 hover:bg-(--bg-hover) rounded-md text-gray-400 transition-colors hidden md:block"
          >
            <FiSidebar size={16} />
          </button>
        </div>
      </div>

      {/* Primary Actions */}
      <div className="px-3 pt-2 pb-1 space-y-0.5">
        <button className="w-full flex items-center gap-3 px-2.5 py-2 rounded-lg hover:bg-(--bg-hover) text-[13px] transition-colors">
          <IoAddOutline size={16} className="text-gray-400" />
          <span>New chat</span>
        </button>
        <button className="w-full flex items-center gap-3 px-2.5 py-2 rounded-lg hover:bg-(--bg-hover) text-[13px] transition-colors">
          <IoSearchOutline size={16} className="text-gray-400" />
          <span>Search</span>
        </button>
        <button className="w-full flex items-center gap-3 px-2.5 py-2 rounded-lg hover:bg-(--bg-hover) text-[13px] transition-colors">
          <FiBriefcase size={16} className="text-gray-400" />
          <span>Customize</span>
        </button>
      </div>

      <div className="px-5 my-2 border-t border-(--border-main) opacity-60"></div>

      {/* Secondary Actions */}
      <div className="px-3 py-1 space-y-0.5">
        <button className="w-full flex items-center gap-3 px-2.5 py-2 rounded-lg hover:bg-(--bg-hover) text-[13px] transition-colors">
          <IoChatbubblesOutline size={16} className="text-gray-400" />
          <span>Chats</span>
        </button>
        <button className="w-full flex items-center gap-3 px-2.5 py-2 rounded-lg hover:bg-(--bg-hover) text-[13px] transition-colors">
          <FiFolder size={16} className="text-gray-400" />
          <span>Projects</span>
        </button>
        <button className="w-full flex items-center gap-3 px-2.5 py-2 rounded-lg hover:bg-(--bg-hover) text-[13px] transition-colors">
          <HiOutlineTemplate size={16} className="text-gray-400" />
          <span>Artifacts</span>
        </button>
      </div>

      {/* Recents */}
      <div className="flex-1 overflow-y-auto px-3 mt-4 mb-2">
        <p className="px-2.5 mb-2 text-[11px] font-medium text-gray-500">
          Recents
        </p>
        <div className="space-y-0.5">
          {chats.map((chat, index) => {
            const isActive = index === 0; // Tạm thời gán dòng đầu tiên luôn được chọn (placeholder)
            return (
              <button
                key={index}
                className={`w-full text-left truncate px-2.5 py-2 rounded-lg transition-colors text-[13px] ${
                  isActive
                    ? "bg-(--bg-hover) text-(--text-main) font-medium"
                    : "text-(--text-muted) hover:bg-(--bg-hover)"
                }`}
              >
                {chat}
              </button>
            );
          })}
        </div>
      </div>

      {/* User Profile / Login */}
      <div className="p-3 relative">
        {isLoggedIn ? (
          <>
            {/* User menu popup */}
            {openUserMenu && (
              <div className="absolute bottom-16 left-3 right-3 bg-(--bg-panel) rounded-xl shadow-2xl border border-(--border-main) py-1 overflow-hidden z-50">
                <div className="px-4 py-3 border-b border-(--border-main) bg-(--bg-panel)">
                  <p className="font-medium text-[13px]">{displayName}</p>
                  <p className="text-[12px] text-gray-400">{displayEmail}</p>
                </div>
                <button className="flex items-center gap-3 w-full px-4 py-2.5 text-[13px] hover:bg-(--bg-hover) transition-colors text-left">
                  <HiOutlineSparkles size={15} /> Nâng cấp gói
                </button>
                <button className="flex items-center gap-3 w-full px-4 py-2.5 text-[13px] hover:bg-(--bg-hover) transition-colors text-left">
                  <FiSettings size={15} /> Cài đặt
                </button>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-3 w-full px-4 py-2.5 text-[13px] hover:bg-(--bg-hover) text-red-400 transition-colors text-left"
                >
                  <FiLogOut size={15} /> Đăng xuất
                </button>
              </div>
            )}

            {/* User Button */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                setOpenUserMenu(!openUserMenu);
              }}
              className="w-full flex items-center justify-between px-2 py-2 rounded-lg hover:bg-(--bg-hover) transition-colors"
            >
              <div className="flex items-center gap-2">
                {currentUser?.avatar_url ? (
                  <img
                    src={currentUser.avatar_url}
                    alt={displayName}
                    className="w-7.5 h-7.5 rounded-full object-cover"
                  />
                ) : (
                  <div className="w-7.5 h-7.5 rounded-full bg-[#E3D4C4] text-[#4A433A] flex items-center justify-center text-xs font-semibold">
                    {initials || "U"}
                  </div>
                )}
                <div className="text-left flex flex-col justify-center ml-1">
                  <span className="text-[13px] font-medium leading-tight">
                    {displayName}
                  </span>
                  <span className="text-[11px] text-gray-400 leading-tight mt-0.5">
                    Free plan
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-1 text-gray-400">
                <div
                  className="p-1 hover:bg-(--bg-hover) rounded transition-colors"
                  onClick={(e) => e.stopPropagation()}
                >
                  <FiDownload size={14} />
                </div>
                <HiSelector size={16} />
              </div>
            </button>
          </>
        ) : (
          /* Login Button */
          <button
            onClick={() => setShowLoginModal(true)}
            className="w-full flex items-center gap-3 px-2.5 py-2.5 rounded-lg hover:bg-(--bg-hover) text-[13px] transition-colors text-(--text-muted) hover:text-(--text-main)"
          >
            <FiLogIn size={16} />
            <span>Đăng nhập</span>
          </button>
        )}
      </div>

      {/* Login Modal */}
      {showLoginModal && (
        <LoginModal
          onClose={() => setShowLoginModal(false)}
          onLogin={setCurrentUser}
        />
      )}
    </div>
  );
}

export default Sidebar;
