"use client";

import React, { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#0A0F1C] flex items-center justify-center px-4">
          <div className="max-w-md w-full text-center">
            <div className="text-5xl mb-4">⚠️</div>
            <h2 className="text-xl font-bold text-white mb-2">
              오류가 발생했습니다
            </h2>
            <p className="text-sm text-[#94A3B8] mb-6">
              {this.state.error?.message || "예상치 못한 오류가 발생했습니다."}
            </p>
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={this.handleReset}
                className="px-5 py-2.5 rounded-lg bg-[#22D3EE] text-[#0A0F1C] font-semibold text-sm hover:opacity-90 transition"
              >
                다시 시도
              </button>
              <button
                onClick={() => (window.location.href = "/")}
                className="px-5 py-2.5 rounded-lg bg-[#1E293B] border border-[#22D3EE30] text-[#94A3B8] font-semibold text-sm hover:border-[#22D3EE60] transition"
              >
                홈으로
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
