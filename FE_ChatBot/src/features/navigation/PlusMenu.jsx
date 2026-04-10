import { useEffect, useState } from "react";
import { FiPlus, FiPaperclip, FiImage, FiMoreHorizontal } from "react-icons/fi";
import { SiGoogledrive } from "react-icons/si";
import { BsLightbulb } from "react-icons/bs";
import { TbTelescope } from "react-icons/tb";
import { MdShoppingBag } from "react-icons/md";

export default function PlusMenu() {
  const [open, setOpen] = useState(false);

  // Click ra ngoài tự đóng
  useEffect(() => {
    const handleClick = () => setOpen(false);
    window.addEventListener("click", handleClick);
    return () => window.removeEventListener("click", handleClick);
  }, []);

  // Fake content
  const items = [
    { icon: <FiPaperclip />, label: "Thêm ảnh và tệp" },
    { icon: <SiGoogledrive />, label: "Thêm từ Google Drive" },
    { divider: true },
    { icon: <FiImage />, label: "Tạo hình ảnh" },
    { icon: <BsLightbulb />, label: "Đang suy nghĩ" },
    { icon: <TbTelescope />, label: "Nghiên cứu chuyên sâu" },
    { icon: <MdShoppingBag />, label: "Nghiên cứu mua sắm" },
    { icon: <FiMoreHorizontal />, label: "Thêm" },
  ];

  return (
    <div className="relative">
      {/* plus btn */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpen(!open);
        }}
        className="p-2 rounded-full hover:bg-neutral-700 transition"
      >
        <FiPlus size={18} />
      </button>

      {/* dropdown plus */}
      {open && (
        <div className="absolute bottom-full mb-2 left-0 w-64 bg-[#2f2f2f] border border-neutral-700 rounded-2xl shadow-xl p-2 z-50">
          {items.map((item, index) =>
            item.divider ? (
              <div key={index} className="border-t border-neutral-700 my-2" />
            ) : (
              <div
                key={index}
                className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-neutral-700 cursor-pointer transition"
              >
                <span className="text-lg text-neutral-300">{item.icon}</span>

                <span className="text-sm text-neutral-200">{item.label}</span>
              </div>
            ),
          )}
        </div>
      )}
    </div>
  );
}
