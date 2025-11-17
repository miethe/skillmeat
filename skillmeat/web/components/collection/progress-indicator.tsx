"use client";

import { useEffect, useState } from "react";
import { CheckCircle, XCircle, AlertCircle, Loader2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { useSSE } from "@/hooks/useSSE";

export interface ProgressStep {
  step: string;
  status: "pending" | "running" | "completed" | "error";
  message?: string;
  progress?: number;
}

export interface ProgressIndicatorProps {
  /**
   * URL for SSE stream
   */
  streamUrl: string | null;

  /**
   * Whether to enable SSE connection
   */
  enabled?: boolean;

  /**
   * Initial steps (optional)
   */
  initialSteps?: ProgressStep[];

  /**
   * Callback when operation completes
   */
  onComplete?: (success: boolean, message?: string) => void;

  /**
   * Callback when error occurs
   */
  onError?: (error: Error) => void;
}

interface ProgressData {
  step: string;
  status: "running" | "completed" | "error";
  message: string;
  progress?: number;
  totalSteps?: number;
  currentStep?: number;
}

export function ProgressIndicator({
  streamUrl,
  enabled = true,
  initialSteps = [],
  onComplete,
  onError,
}: ProgressIndicatorProps) {
  const [steps, setSteps] = useState<ProgressStep[]>(initialSteps);
  const [overallProgress, setOverallProgress] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [hasError, setHasError] = useState(false);

  const { isConnected, isConnecting, error } = useSSE<ProgressData>(
    streamUrl,
    {
      enabled,
      onMessage: (message) => {
        if (message.event === "progress" && message.data) {
          const data = message.data as ProgressData;

          setSteps((prev) => {
            const existing = prev.find((s) => s.step === data.step);
            if (existing) {
              return prev.map((s) =>
                s.step === data.step
                  ? {
                      ...s,
                      status: data.status,
                      message: data.message,
                      progress: data.progress,
                    }
                  : s
              );
            } else {
              return [
                ...prev,
                {
                  step: data.step,
                  status: data.status,
                  message: data.message,
                  progress: data.progress,
                },
              ];
            }
          });

          // Update overall progress
          if (data.totalSteps && data.currentStep) {
            setOverallProgress((data.currentStep / data.totalSteps) * 100);
          } else if (data.progress !== undefined) {
            setOverallProgress(data.progress);
          }

          // Check for errors
          if (data.status === "error") {
            setHasError(true);
            onError?.(new Error(data.message));
          }
        } else if (message.event === "complete") {
          setIsComplete(true);
          setOverallProgress(100);
          onComplete?.(true, message.data?.message);
        } else if (message.event === "error_event") {
          setHasError(true);
          onError?.(new Error(message.data?.message || "Operation failed"));
          onComplete?.(false, message.data?.message);
        }
      },
      onError: (err) => {
        setHasError(true);
        onError?.(err);
      },
    }
  );

  // Handle SSE connection error
  useEffect(() => {
    if (error) {
      setHasError(true);
    }
  }, [error]);

  if (!streamUrl && !initialSteps.length) {
    return null;
  }

  return (
    <div className="space-y-4">
      {/* Overall Progress */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium">
            {isComplete
              ? "Complete"
              : hasError
                ? "Error"
                : isConnecting
                  ? "Connecting..."
                  : isConnected
                    ? "In Progress"
                    : "Waiting..."}
          </span>
          <span className="text-muted-foreground">
            {Math.round(overallProgress)}%
          </span>
        </div>
        <Progress value={overallProgress} className="h-2" />
      </div>

      {/* Connection Status */}
      {streamUrl && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {isConnecting && (
            <>
              <Loader2 className="h-3 w-3 animate-spin" />
              <span>Connecting to stream...</span>
            </>
          )}
          {isConnected && !isComplete && (
            <>
              <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
              <span>Connected</span>
            </>
          )}
          {error && (
            <>
              <XCircle className="h-3 w-3 text-destructive" />
              <span className="text-destructive">Connection lost</span>
            </>
          )}
        </div>
      )}

      {/* Step-by-step Progress */}
      {steps.length > 0 && (
        <div className="space-y-2 max-h-60 overflow-y-auto">
          {steps.map((step, index) => (
            <StepItem key={`${step.step}-${index}`} step={step} />
          ))}
        </div>
      )}

      {/* Error State */}
      {hasError && error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-4 w-4 text-destructive flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-destructive">
                Operation Failed
              </p>
              <p className="text-xs text-destructive/80 mt-1">
                {error.message}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StepItem({ step }: { step: ProgressStep }) {
  const StatusIcon = {
    pending: () => (
      <div className="h-4 w-4 rounded-full border-2 border-muted" />
    ),
    running: () => <Loader2 className="h-4 w-4 animate-spin text-primary" />,
    completed: () => <CheckCircle className="h-4 w-4 text-green-600" />,
    error: () => <XCircle className="h-4 w-4 text-destructive" />,
  }[step.status];

  return (
    <div className="flex items-start gap-3 rounded-lg border p-3">
      <StatusIcon />
      <div className="flex-1 min-w-0 space-y-1">
        <p className="text-sm font-medium">{step.step}</p>
        {step.message && (
          <p className="text-xs text-muted-foreground">{step.message}</p>
        )}
        {step.progress !== undefined && step.status === "running" && (
          <Progress value={step.progress} className="h-1" />
        )}
      </div>
    </div>
  );
}
