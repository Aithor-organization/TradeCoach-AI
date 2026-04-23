"use client";

import { useEffect } from "react";
import { useAuthStore } from "@/stores/authStore";

const CHECK_INTERVAL_MS = 60_000;

export default function AuthExpiryWatcher() {
  useEffect(() => {
    useAuthStore.getState().checkTokenExpiry();
    const id = setInterval(() => {
      useAuthStore.getState().checkTokenExpiry();
    }, CHECK_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  return null;
}
