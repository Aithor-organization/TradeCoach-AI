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
  checkTokenExpiry: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
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
      checkTokenExpiry: () => {
        if (typeof window === "undefined") return;
        const state = get();
        const token = state.token ?? localStorage.getItem("tc_token");
        if (!token) {
          if (state.isAuthenticated) get().logout();
          return;
        }
        try {
          const payload = JSON.parse(atob(token.split(".")[1]));
          if (!payload.exp || payload.exp * 1000 < Date.now()) {
            console.warn("[authStore] 토큰 만료 감지, 자동 로그아웃");
            get().logout();
          }
        } catch {
          console.warn("[authStore] 토큰 파싱 실패, 자동 로그아웃");
          get().logout();
        }
      },
    }),
    {
      name: "tc-auth",
      onRehydrateStorage: () => (state) => {
        console.log("[authStore] onRehydrateStorage 호출, state:", !!state);

        // 이전 배포의 _hydrated 오염 데이터 정리
        if (typeof window !== "undefined") {
          try {
            const raw = localStorage.getItem("tc-auth");
            if (raw && raw.includes("_hydrated")) {
              const parsed = JSON.parse(raw);
              if (parsed?.state?._hydrated !== undefined) {
                delete parsed.state._hydrated;
                localStorage.setItem("tc-auth", JSON.stringify(parsed));
                console.log("[authStore] _hydrated 오염 데이터 정리 완료");
              }
            }
          } catch { /* 파싱 실패 무시 */ }
        }

        // localStorage 토큰과 store 동기화
        if (typeof window === "undefined") return;
        const token = localStorage.getItem("tc_token");
        console.log("[authStore] tc_token 존재:", !!token, "state.isAuthenticated:", state?.isAuthenticated);

        if (token && state && !state.isAuthenticated) {
          try {
            const payload = JSON.parse(atob(token.split(".")[1]));
            if (payload.exp && payload.exp * 1000 < Date.now()) {
              console.log("[authStore] 토큰 만료, 제거");
              localStorage.removeItem("tc_token");
              return;
            }
          } catch {
            console.log("[authStore] 토큰 파싱 실패, 제거");
            localStorage.removeItem("tc_token");
            return;
          }
          console.log("[authStore] 토큰 유효, isAuthenticated=true 설정");
          useAuthStore.setState({ isAuthenticated: true, token });
        }
      },
    }
  )
);
