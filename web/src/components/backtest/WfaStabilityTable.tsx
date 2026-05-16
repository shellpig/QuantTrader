"use client";

// WFA Stability table — CV-based stability for each param (Phase 10-E-4)

interface StabilityParam {
  values: number[];
  cv: number | null;
  mean: number;
  std: number;
  status: string;
}

interface WfaStabilityTableProps {
  params: Record<string, StabilityParam>;
}

function stabilityLabel(status: string): { text: string; colorClass: string } {
  if (status === "stable") return { text: "穩定", colorClass: "text-green-500" };
  if (status === "moderate") return { text: "中等", colorClass: "text-amber-500" };
  if (status === "unstable") return { text: "不穩定", colorClass: "text-red-500" };
  return { text: "未知", colorClass: "text-slate-400" };
}

export function WfaStabilityTable({ params }: WfaStabilityTableProps) {
  const entries = Object.entries(params);

  if (entries.length === 0) {
    return <p className="text-sm text-slate-500">尚無穩定性資料</p>;
  }

  return (
    <div data-testid="wfa-stability-table" className="overflow-x-auto">
      <table className="w-full min-w-[600px] text-sm">
        <thead>
          <tr className="border-b border-slate-700 text-xs text-slate-400">
            <th className="px-2 py-2 text-left">參數</th>
            <th className="px-2 py-2 text-left">各視窗的值</th>
            <th className="px-2 py-2 text-right">平均</th>
            <th className="px-2 py-2 text-right">CV（變異係數）</th>
            <th className="px-2 py-2 text-left">穩定性</th>
          </tr>
        </thead>
        <tbody>
          {entries.map(([paramName, stat]) => {
            const { text, colorClass } = stabilityLabel(stat.status);
            return (
              <tr
                key={paramName}
                data-testid={`stability-row-${paramName}`}
                className="border-b border-slate-800"
              >
                <td className="px-2 py-2 font-mono text-slate-200">{paramName}</td>
                <td className="px-2 py-2">
                  <div className="flex flex-wrap gap-1">
                    {stat.values.map((v, i) => (
                      <span
                        // eslint-disable-next-line react/no-array-index-key
                        key={i}
                        className="rounded bg-slate-700 px-1.5 py-0.5 text-xs text-slate-200"
                      >
                        {v}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-2 py-2 text-right tabular-nums text-slate-300">
                  {stat.mean.toFixed(2)}
                </td>
                <td className="px-2 py-2 text-right tabular-nums text-slate-300">
                  {stat.cv != null ? stat.cv.toFixed(4) : "—"}
                </td>
                <td
                  data-testid={`stability-label-${paramName}`}
                  className={`px-2 py-2 font-semibold ${colorClass}`}
                >
                  {text}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
