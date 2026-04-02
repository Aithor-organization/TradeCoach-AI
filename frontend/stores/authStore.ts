import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  isAuthenticated: boolean;
  userId: string | null;
  name: string | null;
  email: string | null;
  token: string | null;
  _hydrated: boolean;
  login: (token: string, userId: string, name: string, email: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      userId: null,
      name: null,
      email: null,
      token: null,
      _hydrated: false,
      login: (token, userId, name, email) => {
        localStorage.setItem("tc_token", token);
        set({ isAuthenticated: true, token, userId, name, email });
      },
      logout: () => {
        localStorage.removeItem("tc_token");
        set({ isAuthenticated: false, token: null, userId: null, name: null, email: null });
      },
    }),
    {
      name: "tc-auth",
      // _hydrated는 런타임 전용 — localStorage에 저장하면 안 됨
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
        userId: state.userId,
        name: state.name,
        email: state.email,
        token: state.token,
      }),
      onRehydrateStorage: () => (state) => {
        // localStorage 토큰과 store 동기화
        if (typeof window === "undefined") return;
        const token = localStorage.getItem("tc_token");
        if (token && state && !state.isAuthenticated) {
          // 토큰 만료 체크
          try {
            const payload = JSON.parse(atob(token.split(".")[1]));
            if (payload.exp && payload.exp * 1000 < Date.now()) {
              localStorage.removeItem("tc_token");
              useAuthStore.setState({ _hydrated: true });
              return;
            }
          } catch {
            localStorage.removeItem("tc_token");
            useAuthStore.setState({ _hydrated: true });
            return;
          }
          useAuthStore.setState({ isAuthenticated: true, token, _hydrated: true });
        } else {
          useAuthStore.setState({ _hydrated: true });
        }
      },
    }
  )
);
