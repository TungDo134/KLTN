import { signInWithPopup, signOut } from "firebase/auth";

import axiosClient from "../api/axiosClient";
import { auth, googleProvider } from "../config/firebase";

const ACCESS_TOKEN_KEY = "access_token";
const AUTH_USER_KEY = "auth_user";

export async function loginWithGoogle() {
  const result = await signInWithPopup(auth, googleProvider);
  const idToken = await result.user.getIdToken();

  const response = await axiosClient.post("/auth/firebase-login", null, {
    headers: {
      Authorization: `Bearer ${idToken}`,
    },
  });

  localStorage.setItem(ACCESS_TOKEN_KEY, idToken);
  localStorage.setItem(AUTH_USER_KEY, JSON.stringify(response.data));

  return response.data;
}

export async function logout() {
  await signOut(auth);
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
}

export function getStoredAuthUser() {
  const rawUser = localStorage.getItem(AUTH_USER_KEY);
  if (!rawUser) return null;

  try {
    return JSON.parse(rawUser);
  } catch {
    localStorage.removeItem(AUTH_USER_KEY);
    return null;
  }
}
