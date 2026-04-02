import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  isAuthenticated: boolean;
  userId: string | null;
  name: string | null;
  email: string | null;
  token: string | null;
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
        // 이전 배포에서 localStorage에 저장된 _hydrated 오염 데이터 정리
        if (typeof window !== "undefined") {
          try {
            const raw = localStorage.getItem("tc-auth");
            if (raw && raw.includes("_hydrated")) {
              const parsed = JSON.parse(raw);
              if (parsed?.state?._hydrated !== undefined) {
                delete parsed.state._hydrated;
                localStorage.setItem("tc-auth", JSON.stringify(parsed));
              }
            }
          } catch { /* 파싱 실패 무시 */ }
        }

        // localStorage 토큰과 store 동기화
        if (typeof window === "undefined") {
          useAuthHydration.setState({ hydrated: true });
          return;
        }
        const token = localStorage.getItem("tc_token");
        if (token && state && !state.isAuthenticated) {
          // 토큰 만료 체크
          try {
            const payload = JSON.parse(atob(token.split(".")[1]));
            if (payload.exp && payload.exp * 1000 < Date.now()) {
              localStorage.removeItem("tc_token");
              useAuthHydration.setState({ hydrated: true });
              return;
            }
          } catch {
            localStorage.removeItem("tc_token");
            useAuthHydration.setState({ hydrated: true });
            return;
          }
          useAuthStore.setState({ isAuthenticated: true, token });
        }
        useAuthHydration.setState({ hydrated: true });
      },
    }
  )
);

// hydration 상태를 persist와 분리 — localStorage 오염 방지
export const useAuthHydration = create<{ hydrated: boolean }>()(() => ({
  hydrated: false,
}));
