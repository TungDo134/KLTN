import { FiChevronDown, FiShare, FiMoreHorizontal } from "react-icons/fi";

export default function Topbar() {
  return (
    <div className="h-14 flex items-center justify-between px-6 border-b border-neutral-800 bg-[#212121]">
      {/* Left */}
      <div className="flex items-center gap-2 cursor-pointer hover:bg-neutral-800 px-3 py-1.5 rounded-lg transition">
        <span className="text-lg font-medium">T&K Travel Assitant</span>
        {/* <FiChevronDown className="text-gray-400" size={16} /> */}
      </div>

      {/* Right */}
      <div className="flex items-center gap-4">
        <button className="flex items-center gap-2 bg-neutral-800 hover:bg-neutral-700 px-3 py-1.5 rounded-lg transition">
          <FiShare size={16} />
          <span className="text-sm">Chia sẻ</span>
        </button>

        <FiMoreHorizontal
          size={18}
          className="cursor-pointer text-gray-400 hover:text-white transition"
        />
      </div>
    </div>
  );
}
