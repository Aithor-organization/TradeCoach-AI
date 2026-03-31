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

function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    if (!payload.exp) return false;
    return payload.exp * 1000 < Date.now();
  } catch {
    return true;
  }
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
      onRehydrateStorage: () => (state, error) => {
        if (error || !state) {
          // hydration 실패해도 앱은 작동해야 함
          useAuthStore.setState({ _hydrated: true });
          return;
        }
        const token = localStorage.getItem("tc_token");
        if (token && isTokenExpired(token)) {
          localStorage.removeItem("tc_token");
          useAuthStore.setState({
            isAuthenticated: false, token: null, userId: null,
            name: null, email: null, _hydrated: true,
          });
        } else if (token && !state.isAuthenticated) {
          useAuthStore.setState({ isAuthenticated: true, token, _hydrated: true });
        } else {
          useAuthStore.setState({ _hydrated: true });
        }
      },
    }
  )
);
