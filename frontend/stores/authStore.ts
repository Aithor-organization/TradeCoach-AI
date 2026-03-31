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
      onRehydrateStorage: () => (state) => {
        if (state) {
          // hydration 완료 시 localStorage 토큰과 동기화
          const token = localStorage.getItem("tc_token");
          if (token && !state.isAuthenticated) {
            // localStorage에 토큰이 있지만 store에 없는 경우 복구
            useAuthStore.setState({ isAuthenticated: true, token, _hydrated: true });
          } else {
            useAuthStore.setState({ _hydrated: true });
          }
        }
      },
    }
  )
);
