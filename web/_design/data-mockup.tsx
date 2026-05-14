/*
 * QuantTrader — Phase 10-C 資料管理頁 第 1 輪交付（視覺稿）
 * 路徑：web/_design/data-mockup.tsx
 *
 * ⚠️ 本檔為純視覺稿：
 *   - 假資料寫死（6 檔台股 + 3 檔美股範例）
 *   - loading / error / empty 狀態本輪省略（第 3 輪實作端補）
 *   - 同時呈現 Dark / Light 兩版（上下並排）
 *   - 不 import web/src/ 內部模組（避免循環依賴）
 *
 * ─────────────────────────────────────────────────────────────
 * 設計建議變更（請使用者裁決，不擅自改規格）
 * ─────────────────────────────────────────────────────────────
 *  ① 美股 raw / adjusted 雙態顯示
 *     舊 Streamlit 版 (src/ui/pages/data_management.py) 對美股額外
 *     顯示 raw daily / adjusted daily 兩列。新規格只給單列。
 *     建議：美股一筆標的展開成兩列，便於人眼比對 split-adjusted。
 *     本稿折衷做法：合併單列，「區間」欄加註 (raw+adj)，並在「大小」
 *     欄顯示總計。等使用者裁決。
 *
 *  ② 「全部重建」也是破壞性操作
 *     rebuild 會清掉本機快取後重抓，誤點代價高。建議比照 DELETE
 *     加二次確認 dialog。本稿先依規格不加，但 button hover 上加 tooltip
 *     提醒「會重建全部本機快取」。
 *
 *  ③ 美股能力提示
 *     舊版有「美股不支援分 K / 籌碼」的 caption。市場切到美股時
 *     建議保留 inline hint。本稿在表格上方加一條 callout。
 *
 *  ④ 「+ 新增標的」彈窗
 *     規格未說明新增流程（名稱搜尋？貼代碼？批次貼上？）。
 *     本稿先放按鈕；具體互動交由第 2 輪 components.md 補。
 *
 *  ⑤ 狀態 badge 判定閾值
 *     「最新 / 需更新 / 缺資料」三態切分規格未明。建議：
 *       · 最新   ：last_date == 最近交易日
 *       · 需更新 ：last_date 落後 1～5 個交易日
 *       · 缺資料 ：落後 >5 日 或 區間中有缺口
 *     本稿假資料依此規則上色。
 *
 *  ⑥ 「動作」欄 ＝ 更新 + 刪除 兩鈕
 *     刪除為破壞性 → 紅色 (destructive variant)；
 *     更新非破壞性 → ghost / outline，hover 才顯示藍色語意，
 *     避免整欄滿江紅藍干擾資訊閱讀。
 */

"use client";

import { useMemo, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import {
  Search,
  Plus,
  RefreshCw,
  Hammer,
  RotateCw,
  Trash2,
  AlertTriangle,
  X,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────
// 假資料
// ─────────────────────────────────────────────────────────────

type Market = "tw" | "us";
type Status = "fresh" | "stale" | "missing";

interface SymbolRow {
  symbol: string;
  name: string;
  firstDate: string;
  lastDate: string;
  bars: number;
  sizeMB: number;
  status: Status;
  /** 美股可能同時持有 raw + adjusted 兩份 */
  variants?: string;
}

const TW_ROWS: SymbolRow[] = [
  { symbol: "2330",   name: "台積電",            firstDate: "2010-01-04", lastDate: "2026-05-14", bars: 4012, sizeMB: 1.21, status: "fresh"   },
  { symbol: "2317",   name: "鴻海",              firstDate: "2010-01-04", lastDate: "2026-05-14", bars: 4012, sizeMB: 1.14, status: "fresh"   },
  { symbol: "2454",   name: "聯發科",            firstDate: "2010-01-04", lastDate: "2026-05-09", bars: 4008, sizeMB: 1.12, status: "stale"   },
  { symbol: "2412",   name: "中華電",            firstDate: "2010-01-04", lastDate: "2026-05-14", bars: 4012, sizeMB: 0.92, status: "fresh"   },
  { symbol: "00981A", name: "中信中國高股息",     firstDate: "2024-08-01", lastDate: "2026-05-14", bars:  432, sizeMB: 0.13, status: "missing" },
  { symbol: "2603",   name: "長榮",              firstDate: "2010-01-04", lastDate: "2026-05-14", bars: 4012, sizeMB: 1.03, status: "fresh"   },
];

const US_ROWS: SymbolRow[] = [
  { symbol: "AAPL",  name: "Apple Inc.",            firstDate: "2010-01-04", lastDate: "2026-05-13", bars: 4115, sizeMB: 1.42, status: "fresh", variants: "raw+adj" },
  { symbol: "MSFT",  name: "Microsoft Corp.",       firstDate: "2010-01-04", lastDate: "2026-05-13", bars: 4115, sizeMB: 1.41, status: "fresh", variants: "raw+adj" },
  { symbol: "BRK-B", name: "Berkshire Hathaway B",  firstDate: "2010-01-04", lastDate: "2026-05-08", bars: 4111, sizeMB: 1.39, status: "stale", variants: "raw+adj" },
];

// ─────────────────────────────────────────────────────────────
// 視覺 tokens — 用 theme 字串切 Tailwind class，不依賴 globals.css 變數
//                這樣 mockup 在哪都能跑、不會被既有 :root 主題覆蓋
// ─────────────────────────────────────────────────────────────

type ThemeName = "dark" | "light";

interface ThemeTokens {
  app: string;          // 整頁背景
  sidebar: string;      // 側欄底
  card: string;         // 卡片底
  hairline: string;     // 細線
  fg: string;           // 主前景
  fgMuted: string;      // 次前景
  fgFaint: string;      // 灰字
  rowHover: string;
  pillTabActive: string;
  pillTabIdle: string;
  inputBg: string;
  inputBorder: string;
  btnGhost: string;
  btnPrimary: string;
  btnDanger: string;
  dialogOverlay: string;
  dialogPanel: string;
  badge: {
    fresh: string;
    stale: string;
    missing: string;
  };
  mono: string;
}

const TOKENS: Record<ThemeName, ThemeTokens> = {
  dark: {
    app:           "bg-slate-950 text-slate-100",
    sidebar:       "bg-slate-900/80 border-r border-slate-800/80",
    card:          "bg-slate-900/60 border border-slate-800/80",
    hairline:      "border-slate-800/70",
    fg:            "text-slate-100",
    fgMuted:       "text-slate-300",
    fgFaint:       "text-slate-500",
    rowHover:      "hover:bg-slate-800/40",
    pillTabActive: "bg-slate-100 text-slate-900 shadow-sm",
    pillTabIdle:   "text-slate-400 hover:text-slate-200",
    inputBg:       "bg-slate-900/70",
    inputBorder:   "border-slate-700/80 focus-within:border-slate-500",
    btnGhost:      "border border-slate-700/80 bg-slate-900/40 text-slate-200 hover:bg-slate-800/60",
    btnPrimary:    "bg-slate-100 text-slate-900 hover:bg-white",
    btnDanger:     "bg-rose-600 text-white hover:bg-rose-500 disabled:bg-rose-900/40 disabled:text-rose-300/40",
    dialogOverlay: "bg-slate-950/70 backdrop-blur-sm",
    dialogPanel:   "bg-slate-900 border border-slate-800 shadow-2xl",
    badge: {
      fresh:   "bg-emerald-500/15 text-emerald-300 ring-1 ring-inset ring-emerald-500/30",
      stale:   "bg-amber-500/15  text-amber-300  ring-1 ring-inset ring-amber-500/30",
      missing: "bg-rose-500/15   text-rose-300   ring-1 ring-inset ring-rose-500/30",
    },
    mono:          "[font-family:var(--font-mono,ui-monospace,SFMono-Regular,Menlo,monospace)]",
  },
  light: {
    app:           "bg-slate-50 text-slate-900",
    sidebar:       "bg-white border-r border-slate-200",
    card:          "bg-white border border-slate-200",
    hairline:      "border-slate-200",
    fg:            "text-slate-900",
    fgMuted:       "text-slate-600",
    fgFaint:       "text-slate-400",
    rowHover:      "hover:bg-slate-50",
    pillTabActive: "bg-slate-900 text-white shadow-sm",
    pillTabIdle:   "text-slate-500 hover:text-slate-800",
    inputBg:       "bg-white",
    inputBorder:   "border-slate-300 focus-within:border-slate-500",
    btnGhost:      "border border-slate-300 bg-white text-slate-700 hover:bg-slate-100",
    btnPrimary:    "bg-slate-900 text-white hover:bg-slate-800",
    btnDanger:     "bg-rose-600 text-white hover:bg-rose-500 disabled:bg-rose-200 disabled:text-rose-400",
    dialogOverlay: "bg-slate-900/40 backdrop-blur-sm",
    dialogPanel:   "bg-white border border-slate-200 shadow-2xl",
    badge: {
      fresh:   "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-200",
      stale:   "bg-amber-50   text-amber-700   ring-1 ring-inset ring-amber-200",
      missing: "bg-rose-50    text-rose-700    ring-1 ring-inset ring-rose-200",
    },
    mono:          "[font-family:var(--font-mono,ui-monospace,SFMono-Regular,Menlo,monospace)]",
  },
};

const STATUS_LABEL: Record<Status, string> = {
  fresh:   "最新",
  stale:   "需更新",
  missing: "缺資料",
};

// ─────────────────────────────────────────────────────────────
// 內嵌假側欄（不 import web/src/components/sidebar.tsx）
// 視覺對齊 10-B 既有骨架：240px 寬、QuantTrader logo + 5 nav item
// ─────────────────────────────────────────────────────────────

function FakeSidebar({ t }: { t: ThemeTokens }) {
  const items = [
    { label: "個股分析", icon: "📈" },
    { label: "回測研究", icon: "🧪" },
    { label: "資料管理", icon: "🗂", active: true },
    { label: "AI 問答",  icon: "🤖" },
    { label: "設定",     icon: "⚙" },
  ];
  return (
    <aside className={`w-60 shrink-0 ${t.sidebar} flex flex-col`}>
      <div className={`h-16 px-6 flex items-center border-b ${t.hairline}`}>
        <span className={`text-lg font-semibold tracking-tight ${t.fg}`}>
          QuantTrader
        </span>
      </div>
      <nav className="flex flex-col gap-0.5 p-3">
        {items.map((it) => (
          <div
            key={it.label}
            className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm ${
              it.active
                ? (t === TOKENS.dark
                    ? "bg-slate-800/80 text-slate-50"
                    : "bg-slate-100 text-slate-900 font-medium")
                : `${t.fgMuted} hover:${t.fg.replace("text-", "text-")}`
            }`}
          >
            <span className="w-5 text-center text-base leading-none opacity-80">{it.icon}</span>
            <span>{it.label}</span>
          </div>
        ))}
      </nav>
    </aside>
  );
}

// ─────────────────────────────────────────────────────────────
// Header — 標題 + 副標 + 市場 toggle
// ─────────────────────────────────────────────────────────────

function PageHeader({
  t,
  market,
  onMarketChange,
}: {
  t: ThemeTokens;
  market: Market;
  onMarketChange: (m: Market) => void;
}) {
  return (
    <div className="flex items-end justify-between gap-4">
      <div>
        <div className={`text-[11px] uppercase tracking-[0.18em] ${t.fgFaint}`}>
          資料 / Data Management
        </div>
        <h1 className={`mt-1 text-2xl font-semibold tracking-tight ${t.fg}`}>
          資料管理
        </h1>
        <p className={`mt-1 text-sm ${t.fgMuted}`}>
          管理本機歷史資料、更新與重建。資料儲存於 <code className={`${t.mono} text-[12px]`}>data/parquet</code> 與 DuckDB metadata。
        </p>
      </div>
      <div className={`inline-flex items-center rounded-full p-1 ${t === TOKENS.dark ? "bg-slate-900/80 ring-1 ring-slate-800" : "bg-slate-200/70"}`}>
        {(["tw", "us"] as Market[]).map((m) => (
          <button
            key={m}
            onClick={() => onMarketChange(m)}
            className={`px-4 py-1.5 text-sm rounded-full transition-colors ${
              market === m ? t.pillTabActive : t.pillTabIdle
            }`}
          >
            {m === "tw" ? "台股" : "美股"}
          </button>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Toolbar — 搜尋 + 新增 + 3 個批次操作
// ─────────────────────────────────────────────────────────────

function Toolbar({ t }: { t: ThemeTokens }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="flex items-center gap-2 flex-1 max-w-xl">
        <label
          className={`flex items-center gap-2 flex-1 rounded-md border px-3 h-9 ${t.inputBg} ${t.inputBorder}`}
        >
          <Search className={`h-4 w-4 ${t.fgFaint}`} />
          <input
            type="text"
            placeholder="搜尋代碼或名稱（例：2330、台積電、AAPL）"
            className={`bg-transparent outline-none text-sm flex-1 ${t.fg} placeholder:${t.fgFaint.replace("text-", "text-")}`}
          />
        </label>
        <button
          className={`inline-flex items-center gap-1.5 h-9 px-3 rounded-md text-sm font-medium ${t.btnPrimary}`}
        >
          <Plus className="h-4 w-4" />
          新增標的
        </button>
      </div>

      <div className="flex items-center gap-2">
        <button className={`inline-flex items-center gap-1.5 h-9 px-3 rounded-md text-sm ${t.btnGhost}`}>
          <RotateCw className="h-3.5 w-3.5" />
          重新整理列表
        </button>
        <button className={`inline-flex items-center gap-1.5 h-9 px-3 rounded-md text-sm ${t.btnGhost}`}>
          <RefreshCw className="h-3.5 w-3.5" />
          全部更新
        </button>
        <button
          title="會清掉所有標的的本機快取後重抓 — 建議第 2 輪加二次確認 dialog"
          className={`inline-flex items-center gap-1.5 h-9 px-3 rounded-md text-sm ${t.btnGhost}`}
        >
          <Hammer className="h-3.5 w-3.5" />
          全部重建
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Table
// ─────────────────────────────────────────────────────────────

function StatusBadge({ t, status }: { t: ThemeTokens; status: Status }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium ${t.badge[status]}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          status === "fresh"   ? "bg-emerald-400" :
          status === "stale"   ? "bg-amber-400"   :
                                 "bg-rose-400"
        }`}
      />
      {STATUS_LABEL[status]}
    </span>
  );
}

function DataTable({
  t,
  rows,
  market,
  onDelete,
}: {
  t: ThemeTokens;
  rows: SymbolRow[];
  market: Market;
  onDelete: (row: SymbolRow) => void;
}) {
  return (
    <div className={`rounded-xl ${t.card} overflow-hidden`}>
      <div className={`sticky top-0 z-10 grid grid-cols-[100px_1fr_220px_90px_80px_100px_180px] gap-3 px-4 py-2.5 text-[11px] uppercase tracking-wider ${t.fgFaint} border-b ${t.hairline} ${
        t === TOKENS.dark ? "bg-slate-900/95 backdrop-blur" : "bg-white/95 backdrop-blur"
      }`}>
        <div>代碼</div>
        <div>名稱</div>
        <div>區間</div>
        <div className="text-right">K 棒數</div>
        <div className="text-right">大小</div>
        <div>狀態</div>
        <div className="text-right pr-1">動作</div>
      </div>

      <div>
        {rows.map((row, i) => (
          <div
            key={row.symbol}
            className={`grid grid-cols-[100px_1fr_220px_90px_80px_100px_180px] gap-3 px-4 py-3 items-center text-sm transition-colors ${t.rowHover} ${i !== rows.length - 1 ? `border-b ${t.hairline}` : ""}`}
          >
            <div className={`${t.mono} ${t.fg} font-medium`}>{row.symbol}</div>
            <div className={t.fg}>
              {row.name}
              {row.variants && (
                <span className={`ml-2 text-[10px] uppercase tracking-wider ${t.fgFaint}`}>
                  {row.variants}
                </span>
              )}
            </div>
            <div className={`${t.mono} text-[12.5px] ${t.fgMuted}`}>
              {row.firstDate} <span className={t.fgFaint}>~</span> {row.lastDate}
            </div>
            <div className={`${t.mono} text-right ${t.fgMuted}`}>{row.bars.toLocaleString()}</div>
            <div className={`${t.mono} text-right ${t.fgMuted}`}>
              {row.sizeMB.toFixed(2)}<span className={`ml-0.5 text-[10px] ${t.fgFaint}`}> MB</span>
            </div>
            <div>
              <StatusBadge t={t} status={row.status} />
            </div>
            <div className="flex items-center justify-end gap-1.5">
              <button
                className="inline-flex items-center gap-1 h-7 px-2.5 rounded-md text-xs border border-sky-500/30 bg-sky-500/10 text-sky-300 hover:bg-sky-500/20 dark:text-sky-300"
                style={
                  t === TOKENS.light
                    ? { background: "rgb(240 249 255)", borderColor: "rgb(186 230 253)", color: "rgb(2 132 199)" }
                    : undefined
                }
              >
                <RefreshCw className="h-3 w-3" />
                更新
              </button>
              <button
                onClick={() => onDelete(row)}
                className="inline-flex items-center gap-1 h-7 px-2.5 rounded-md text-xs border border-rose-500/30 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20"
                style={
                  t === TOKENS.light
                    ? { background: "rgb(255 241 242)", borderColor: "rgb(254 205 211)", color: "rgb(225 29 72)" }
                    : undefined
                }
              >
                <Trash2 className="h-3 w-3" />
                刪除
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// 美股 inline 能力提示（規格漏列，建議補）
// ─────────────────────────────────────────────────────────────

function USCapabilityNote({ t }: { t: ThemeTokens }) {
  return (
    <div className={`flex items-start gap-2.5 rounded-md px-3 py-2 text-[12.5px] ${
      t === TOKENS.dark
        ? "bg-slate-900/40 border border-slate-800 text-slate-400"
        : "bg-slate-50 border border-slate-200 text-slate-500"
    }`}>
      <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0 text-amber-400" />
      <span>
        美股模式僅支援日 K（資料來源：yfinance · America/New_York）。
        US-1 範圍不含分 K 與籌碼資料；同一標的會同時保留 <code className={`${t.mono} text-[11.5px]`}>raw</code> 與 <code className={`${t.mono} text-[11.5px]`}>adjusted</code> 兩份。
      </span>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// DELETE Dialog — 單步確認（警示文案 + 取消／確認刪除）
// ─────────────────────────────────────────────────────────────

interface DeleteState {
  open: boolean;
  market: Market;
  row: SymbolRow | null;
}

function DeleteDialog({
  t,
  state,
  onClose,
}: {
  t: ThemeTokens;
  state: DeleteState;
  onClose: () => void;
}) {
  const symbol = state.row?.symbol ?? "";

  return (
    <Dialog.Root open={state.open} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className={`fixed inset-0 z-50 ${t.dialogOverlay}`} />
        <Dialog.Content
          className={`fixed left-1/2 top-1/2 z-50 w-[480px] -translate-x-1/2 -translate-y-1/2 rounded-xl p-6 ${t.dialogPanel}`}
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className={`mt-0.5 flex h-9 w-9 items-center justify-center rounded-full ${
                t === TOKENS.dark ? "bg-rose-500/15" : "bg-rose-100"
              }`}>
                <AlertTriangle className="h-5 w-5 text-rose-500" />
              </div>
              <div>
                <Dialog.Title className={`text-base font-semibold ${t.fg}`}>
                  確認刪除 <code className={`${t.mono} text-[15px]`}>{symbol}</code> 本機快取
                </Dialog.Title>
                <Dialog.Description className={`mt-1.5 text-[13px] leading-relaxed ${t.fgMuted}`}>
                  此動作將刪除「{state.market === "tw" ? "台股" : "美股"} · <code className={t.mono}>{symbol}</code>」的原始與調整後資料。
                  可隨時重新下載；歷史快取無法復原。
                </Dialog.Description>
              </div>
            </div>
            <Dialog.Close
              className={`-mt-1 -mr-1 rounded-md p-1 ${t.fgFaint} hover:${t.fg.replace("text-", "text-")}`}
            >
              <X className="h-4 w-4" />
            </Dialog.Close>
          </div>

          <div className={`mt-6 flex items-center justify-end gap-2 pt-4 border-t ${t.hairline}`}>
            <button
              onClick={onClose}
              className={`h-9 px-4 rounded-md text-sm ${t.btnGhost}`}
            >
              取消
            </button>
            <button
              className={`h-9 px-4 rounded-md text-sm font-medium inline-flex items-center gap-1.5 ${t.btnDanger}`}
            >
              <Trash2 className="h-3.5 w-3.5" />
              確認刪除
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

// ─────────────────────────────────────────────────────────────
// 單一主題下的完整頁面
// ─────────────────────────────────────────────────────────────

function DataManagementPage({
  theme,
  initialDelete,
}: {
  theme: ThemeName;
  /** 給 mockup 預設一個展開的 dialog 狀態以便視覺驗收 */
  initialDelete?: DeleteState;
}) {
  const t = TOKENS[theme];
  const [market, setMarket] = useState<Market>("tw");
  const [del, setDel] = useState<DeleteState>(
    initialDelete ?? { open: false, market: "tw", row: null }
  );

  const rows = useMemo(() => (market === "tw" ? TW_ROWS : US_ROWS), [market]);

  return (
    <div className={`w-[1440px] min-h-[900px] flex ${t.app}`}>
      <FakeSidebar t={t} />

      <main className="flex-1 flex flex-col">
        <div className={`sticky top-0 z-20 px-8 pt-6 pb-4 ${
          t === TOKENS.dark ? "bg-slate-950/90 backdrop-blur" : "bg-slate-50/90 backdrop-blur"
        }`}>
          <PageHeader t={t} market={market} onMarketChange={setMarket} />
          <div className="mt-4">
            <Toolbar t={t} />
          </div>
        </div>

        <div className="px-8 pt-4 flex-1 flex flex-col gap-3">
          {market === "us" && <USCapabilityNote t={t} />}
          <DataTable
            t={t}
            rows={rows}
            market={market}
            onDelete={(row) => setDel({ open: true, market, row })}
          />
        </div>

        <footer className={`px-8 py-3 mt-3 border-t ${t.hairline} flex items-center justify-between text-[11.5px] ${t.fgFaint}`}>
          <span>
            資料來源：FinMind（台股）／ yfinance（美股）　·　本機快取存於{" "}
            <code className={`${t.mono} text-[11px]`}>data/parquet</code> + DuckDB metadata
          </span>
          <span>
            共 <span className={t.fgMuted}>{rows.length}</span> 檔 ·{" "}
            {rows.filter((r) => r.status === "fresh").length} 最新 ·{" "}
            {rows.filter((r) => r.status === "stale").length} 需更新 ·{" "}
            {rows.filter((r) => r.status === "missing").length} 缺資料
          </span>
        </footer>

        <DeleteDialog t={t} state={del} onClose={() => setDel({ ...del, open: false })} />
      </main>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// 預設輸出：Dark 上 / Light 下；各預先撐開 DELETE dialog 一例
// ─────────────────────────────────────────────────────────────

export default function DataMockup() {
  return (
    <div className="flex flex-col gap-8 bg-neutral-200 p-6">
      <FrameLabel label="Dark · 預設" caption="DELETE dialog 開啟（單步確認）" />
      <DataManagementPage
        theme="dark"
        initialDelete={{
          open: true,
          market: "tw",
          row: TW_ROWS[0],
        }}
      />

      <FrameLabel label="Light" caption="列表頁，DELETE dialog 未開啟" />
      <DataManagementPage theme="light" />
    </div>
  );
}

function FrameLabel({ label, caption }: { label: string; caption: string }) {
  return (
    <div className="w-[1440px] flex items-baseline gap-3 text-neutral-700">
      <span className="text-xs uppercase tracking-[0.18em] font-semibold">{label}</span>
      <span className="text-xs text-neutral-500">— {caption}</span>
    </div>
  );
}
