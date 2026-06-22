import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { IoCloseOutline } from "react-icons/io5";
import { FcGoogle } from "react-icons/fc";

import { loginWithGoogle } from "../../services/authApi";

function LoginModal({ onClose, onLogin }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, []);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const handleGoogleLogin = async () => {
    setLoading(true);
    setError("");

    try {
      const user = await loginWithGoogle();
      onLogin?.(user);
      onClose();
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Khong the dang nhap voi Google.",
      );
    } finally {
      setLoading(false);
    }
  };

  return createPortal(
    <div
      className="fixed inset-0 z-[999] flex items-center justify-center"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

      <div
        className="relative bg-white rounded-2xl w-[420px] max-w-[90vw] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        style={{ animation: "loginModalIn 0.2s ease-out" }}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 rounded-full hover:bg-gray-100 transition-colors text-gray-500 hover:text-gray-800"
        >
          <IoCloseOutline size={22} />
        </button>

        <div className="px-8 pt-10 pb-8">
          <h2 className="text-[24px] font-bold text-gray-900 leading-tight">
            Dang nhap hoac dang ky
          </h2>

          <div className="mt-7">
            <button
              onClick={handleGoogleLogin}
              disabled={loading}
              className="w-full flex items-center gap-3 px-5 py-3 border border-gray-200 rounded-full text-[14px] font-medium text-gray-800 hover:bg-gray-50 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <FcGoogle size={20} />
              <span>{loading ? "Dang dang nhap..." : "Tiep tuc voi Google"}</span>
            </button>

            {error && (
              <p className="mt-3 text-[13px] leading-5 text-red-500">
                {error}
              </p>
            )}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes loginModalIn {
          from {
            opacity: 0;
            transform: scale(0.95) translateY(10px);
          }
          to {
            opacity: 1;
            transform: scale(1) translateY(0);
          }
        }
      `}</style>
    </div>,
    document.body,
  );
}

export default LoginModal;
