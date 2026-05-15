"use client";

const STORAGE_KEY = "ai_chat.disclaimer_accepted_v1";
const DISCLAIMER =
  "本工具提供的分析僅供研究參考，並非投資建議。投資人需自行評估風險並承擔後果。";

interface DisclaimerGateProps {
  onAccept: () => void;
}

export function DisclaimerGate({ onAccept }: DisclaimerGateProps) {
  function handleAccept() {
    try {
      localStorage.setItem(STORAGE_KEY, "1");
    } catch {
      // localStorage may be unavailable in some environments
    }
    onAccept();
  }

  return (
    <div
      className="flex flex-1 items-center justify-center p-4"
      data-testid="disclaimer-gate"
    >
      <div className="w-full max-w-lg rounded-xl border border-border bg-card p-6 shadow-sm">
        <h2 className="mb-3 text-base font-semibold text-foreground">
          免責聲明
        </h2>
        <p className="text-sm leading-relaxed text-muted-foreground">
          {DISCLAIMER}
        </p>
        <div className="mt-4 flex justify-end">
          <button
            onClick={handleAccept}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            data-testid="disclaimer-accept"
          >
            我了解
          </button>
        </div>
      </div>
    </div>
  );
}

export function isDisclaimerAccepted(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}
