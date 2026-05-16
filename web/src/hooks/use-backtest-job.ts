"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useToast } from "@/hooks/use-toast";

export type BacktestJobStatus = "idle" | "running" | "complete" | "error" | "cancelled";

export interface BacktestProgress {
  current?: number;
  total?: number;
  phase?: string;
  meta?: unknown;
}

export interface BacktestJobError {
  code: string;
  message: string;
}

export interface UseBacktestJobReturn<TResult> {
  jobId: string | null;
  status: BacktestJobStatus;
  progress: BacktestProgress | null;
  result: TResult | null;
  error: BacktestJobError | null;
  start: (type: string, params: Record<string, unknown>) => Promise<void>;
  cancel: () => Promise<void>;
  reset: () => void;
}

export interface UseBacktestJobOptions<TResult> {
  disableDefaultToasts?: boolean;
  onProgress?: (progress: BacktestProgress) => void;
  onResult?: (result: TResult) => void;
  onComplete?: (result: TResult | null) => void;
  onCancelled?: (result: TResult | null) => void;
  onError?: (error: BacktestJobError) => void;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function useBacktestJob<TResult = unknown>(
  options?: UseBacktestJobOptions<TResult>,
): UseBacktestJobReturn<TResult> {
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<BacktestJobStatus>("idle");
  const [progress, setProgress] = useState<BacktestProgress | null>(null);
  const [result, setResult] = useState<TResult | null>(null);
  const [error, setError] = useState<BacktestJobError | null>(null);

  const jobIdRef = useRef<string | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const resultRef = useRef<TResult | null>(null);
  const toast = useToast();

  const _closeStream = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      _closeStream();
    };
  }, [_closeStream]);

  const reset = useCallback(() => {
    _closeStream();
    setStatus("idle");
    setProgress(null);
    setResult(null);
    resultRef.current = null;
    setError(null);
    jobIdRef.current = null;
    setJobId(null);
  }, [_closeStream]);

  const start = useCallback(
    async (type: string, params: Record<string, unknown>): Promise<void> => {
      _closeStream();
      setStatus("running");
      setProgress(null);
      setResult(null);
      resultRef.current = null;
      setError(null);

      let jobId: string;
      try {
        const resp = await fetch(`${API_BASE}/api/jobs`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ type, params }),
        });
        if (!resp.ok) {
          const body = await resp.json().catch(() => ({}));
          const msg = body?.detail?.error?.message ?? `HTTP ${resp.status}`;
          const err = { code: "HTTP_ERROR", message: msg } satisfies BacktestJobError;
          setStatus("error");
          setError(err);
          if (!options?.disableDefaultToasts) {
            toast.error(`回測失敗：${msg}`);
          }
          options?.onError?.(err);
          return;
        }
        const body = await resp.json();
        jobId = body.job_id;
        jobIdRef.current = jobId;
        setJobId(jobId);
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        const err = { code: "NETWORK_ERROR", message: msg } satisfies BacktestJobError;
        setStatus("error");
        setError(err);
        if (!options?.disableDefaultToasts) {
          toast.error(`回測失敗：${msg}`);
        }
        options?.onError?.(err);
        return;
      }

      const es = new EventSource(`${API_BASE}/api/jobs/${jobId}/events`);
      esRef.current = es;

      es.addEventListener("progress", (evt) => {
        try {
          const data = JSON.parse(evt.data);
          const nextProgress = {
            current: data.current,
            total: data.total,
            phase: data.phase,
            meta: data,
          };
          setProgress(nextProgress);
          options?.onProgress?.(nextProgress);
        } catch {
          // ignore parse errors
        }
      });

      es.addEventListener("result", (evt) => {
        try {
          const data = JSON.parse(evt.data) as TResult;
          setResult(data);
          resultRef.current = data;
          options?.onResult?.(data);
        } catch {
          // result parse error handled by error event or onerror
        }
      });

      es.addEventListener("error_event", (evt) => {
        try {
          const data = JSON.parse((evt as MessageEvent).data);
          const err: BacktestJobError = { code: data.code ?? "UNKNOWN", message: data.message ?? "未知錯誤" };
          setStatus("error");
          setError(err);
          if (!options?.disableDefaultToasts) {
            toast.error(`回測失敗：${err.message}`);
          }
          options?.onError?.(err);
          _closeStream();
        } catch {
          const err = { code: "PARSE_ERROR", message: "SSE 事件解析失敗" } satisfies BacktestJobError;
          setStatus("error");
          setError(err);
          if (!options?.disableDefaultToasts) {
            toast.error("回測失敗：SSE 事件解析失敗");
          }
          options?.onError?.(err);
          _closeStream();
        }
      });

      es.onerror = () => {
        // SSE closed = job ended; poll final status
        _closeStream();
        fetch(`${API_BASE}/api/jobs/${jobId}`)
          .then((r) => r.json())
          .then((body) => {
            const s = body.status as BacktestJobStatus;
            if (s === "complete") {
              setStatus("complete");
              if (!options?.disableDefaultToasts) {
                toast.success("回測完成");
              }
              options?.onComplete?.(resultRef.current);
            } else if (s === "cancelled") {
              setStatus("cancelled");
              if (!options?.disableDefaultToasts) {
                toast.info("回測已取消");
              }
              options?.onCancelled?.(resultRef.current);
            } else if (s === "error") {
              setStatus("error");
              const msg = body.message ?? "執行失敗";
              const err = { code: "JOB_ERROR", message: msg } satisfies BacktestJobError;
              setError(err);
              if (!options?.disableDefaultToasts) {
                toast.error(`回測失敗：${msg}`);
              }
              options?.onError?.(err);
            } else {
              // still running? retry a bit later — shouldn't happen
              setStatus("complete");
              if (!options?.disableDefaultToasts) {
                toast.success("回測完成");
              }
              options?.onComplete?.(resultRef.current);
            }
          })
          .catch(() => {
            const err = { code: "POLL_ERROR", message: "無法取得回測結果" } satisfies BacktestJobError;
            setStatus("error");
            setError(err);
            if (!options?.disableDefaultToasts) {
              toast.error("回測失敗：無法取得結果");
            }
            options?.onError?.(err);
          });
      };
    },
    [_closeStream, options, toast],
  );

  const cancel = useCallback(async (): Promise<void> => {
    const jobId = jobIdRef.current;
    if (!jobId) return;
    try {
      await fetch(`${API_BASE}/api/jobs/${jobId}/cancel`, { method: "POST" });
    } catch {
      // ignore — SSE onerror will handle the final state
    }
  }, []);

  return { jobId, status, progress, result, error, start, cancel, reset };
}
