"use client";

import React from "react";
import { RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";

type ErrorBoundaryProps = {
  children: React.ReactNode;
  fallback?:
    | React.ReactNode
    | ((error: Error, reset: () => void) => React.ReactNode);
};

type ErrorBoundaryState = {
  error: Error | null;
};

export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    if (process.env.NODE_ENV !== "production") {
      console.error("[ErrorBoundary]", error, info);
    }
  }

  private reset = () => {
    this.setState({ error: null });
  };

  render() {
    if (this.state.error) {
      const { fallback } = this.props;
      if (typeof fallback === "function") {
        return fallback(this.state.error, this.reset);
      }
      return (
        fallback ?? (
          <DefaultErrorFallback error={this.state.error} reset={this.reset} />
        )
      );
    }
    return this.props.children;
  }
}

export function DefaultErrorFallback({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  const router = useRouter();

  function handleReset() {
    reset();
    router.refresh();
  }

  return (
    <div
      className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-rose-300"
      data-testid="error-boundary-fallback"
    >
      <p className="font-semibold">執行發生錯誤</p>
      <p className="mt-1 text-sm">{error.message}</p>
      {process.env.NODE_ENV !== "production" && (
        <pre className="mt-2 max-h-40 overflow-auto text-xs">{error.stack}</pre>
      )}
      <button
        type="button"
        onClick={handleReset}
        className="mt-3 inline-flex items-center gap-1 rounded bg-rose-500 px-3 py-1 text-sm text-white hover:bg-rose-400"
      >
        <RefreshCw className="h-3.5 w-3.5" />
        重置
      </button>
    </div>
  );
}
