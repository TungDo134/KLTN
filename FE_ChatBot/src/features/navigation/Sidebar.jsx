import { useEffect, useState } from "react";
import { IoCreateOutline, IoSearchOutline } from "react-icons/io5";
import { FiSettings, FiLogOut } from "react-icons/fi";
import { HiOutlineSparkles } from "react-icons/hi";

function Sidebar() {
  const [openUserMenu, setOpenUserMenu] = useState(false);

  // Click ra ngoài tự đóng
  useEffect(() => {
    const handleClick = () => setOpenUserMenu(false);
    window.addEventListener("click", handleClick);
    return () => window.removeEventListener("click", handleClick);
  }, []);

  // Fake content
  const chats = [
    "Lịch trình Đà Lạt 3 ngày",
    "Du lịch Hà Nội",
    "Khách sạn Phú Quốc",
  ];

  return (
    <div className="w-64 bg-black p-4 flex flex-col justify-between relative">
      {/* Content */}
      <div>
        <button className="bg-black hover:bg-[#ffffff1a] transition p-2 mb-4 rounded-xl text-sm flex items-center gap-x-2 w-full">
          <IoCreateOutline size="20px" /> Đoạn hội thoại mới
        </button>

        <div className="flex items-center gap-x-2 p-2 mb-2">
          <IoSearchOutline size="20px" />
          <input
            placeholder="Tìm kiếm đoạn hội thoại..."
            className="rounded text-sm outline-none bg-transparent w-full"
          />
        </div>

        <div className="space-y-2 overflow-y-auto max-h-[60vh]">
          <p className="p-2 rounded text-gray-400 cursor-pointer text-[13px]">
            Các đoạn chat của bạn {">"}
          </p>

          <div className="p-2 rounded-xl hover:bg-[#ffffff1a] cursor-pointer text-sm bg-[#242424]">
            Tham quan Hồ Chí Minh
          </div>

          {chats.map((chat, index) => (
            <div
              key={index}
              className="p-2 rounded-xl hover:bg-[#ffffff1a] cursor-pointer text-sm"
            >
              {chat}
            </div>
          ))}
        </div>
      </div>

      {/* User */}
      <div className="relative">
        {/* User menu */}
        {openUserMenu && (
          <div className="absolute bottom-14 left-0 w-full bg-[#2a2a2a] rounded-xl shadow-lg border border-[#3a3a3a] py-2">
            <div className="px-4 py-2 border-b border-[#3a3a3a]">
              <p className="font-medium text-sm">Tùng Đỗ</p>
              <p className="text-xs text-gray-400">@sont4036</p>
            </div>

            <button className="flex items-center gap-2 w-full px-4 py-2 text-sm hover:bg-[#3a3a3a]">
              <HiOutlineSparkles /> Nâng cấp gói
            </button>

            <button className="flex items-center gap-2 w-full px-4 py-2 text-sm hover:bg-[#3a3a3a]">
              <FiSettings /> Cài đặt
            </button>

            <button className="flex items-center gap-2 w-full px-4 py-2 text-sm hover:bg-[#3a3a3a]">
              <FiLogOut /> Đăng xuất
            </button>
          </div>
        )}

        {/* User btn */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            setOpenUserMenu(!openUserMenu);
          }}
          className="flex items-center gap-3 w-full p-2 rounded-xl hover:bg-[#ffffff1a]"
        >
          <div className="w-8 h-8 rounded-full bg-pink-400 flex items-center justify-center text-sm">
            T
          </div>

          <div className="text-left">
            <p className="text-sm">Tùng Đỗ</p>
            <p className="text-xs text-gray-400">Free</p>
          </div>
        </button>
      </div>
    </div>
  );
}

export default Sidebar;
