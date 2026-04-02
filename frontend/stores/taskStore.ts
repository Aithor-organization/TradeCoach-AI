/**
 * taskStore — 백그라운드 작업 상태 관리 (persist)
 *
 * 백테스트, 파라미터 최적화, 모의트레이딩 세션을 페이지 이동/새로고침 후에도 복구.
 * 작업 ID만 localStorage에 저장하고, 결과는 서버에서 폴링으로 조회한다.
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

export type TaskType = "backtest" | "optimize" | "walkforward" | "demo";
export type TaskStatus = "running" | "completed" | "failed" | "stopped";

export interface BackgroundTask {
  id: string;           // job_id 또는 session_id
  type: TaskType;
  strategyId: string;
  strategyName: string;
  status: TaskStatus;
  startedAt: string;    // ISO8601
  result?: unknown;     // 완료 시 결과 데이터
  error?: string;
}

interface TaskState {
  tasks: BackgroundTask[];
  addTask: (task: Omit<BackgroundTask, "status" | "startedAt">) => void;
  updateTask: (id: string, updates: Partial<BackgroundTask>) => void;
  removeTask: (id: string) => void;
  getRunningTasks: () => BackgroundTask[];
  getTasksByStrategy: (strategyId: string) => BackgroundTask[];
}

export const useTaskStore = create<TaskState>()(
  persist(
    (set, get) => ({
      tasks: [],
      addTask: (task) =>
        set((state) => ({
          tasks: [
            ...state.tasks,
            { ...task, status: "running", startedAt: new Date().toISOString() },
          ],
        })),
      updateTask: (id, updates) =>
        set((state) => ({
          tasks: state.tasks.map((t) =>
            t.id === id ? { ...t, ...updates } : t
          ),
        })),
      removeTask: (id) =>
        set((state) => ({
          tasks: state.tasks.filter((t) => t.id !== id),
        })),
      getRunningTasks: () => get().tasks.filter((t) => t.status === "running"),
      getTasksByStrategy: (strategyId) =>
        get().tasks.filter((t) => t.strategyId === strategyId),
    }),
    {
      name: "tc-tasks",
      // 24시간 이상 된 완료 작업은 자동 정리
      onRehydrateStorage: () => (state) => {
        if (!state) return;
        const cutoff = Date.now() - 24 * 60 * 60 * 1000;
        const cleaned = state.tasks.filter(
          (t) =>
            t.status === "running" ||
            new Date(t.startedAt).getTime() > cutoff
        );
        if (cleaned.length !== state.tasks.length) {
          useTaskStore.setState({ tasks: cleaned });
        }
      },
    }
  )
);
