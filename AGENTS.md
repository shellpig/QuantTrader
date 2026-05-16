# Agent Instructions

# QuantTrader

台股量化交易研究工具（個人版），純 Python，聚焦研究與回測，不接實盤。

## New Conversation Opening Check

At conversation start, read in this layered order. Ignore `舊文件/`.

**Layer 1 — Always read (build full picture fast):**
1. `AGENTS.md` (this file)
2. `PROJECT_BRIEF.md` (architecture, progress, spec index)
3. `驗證後已知問題.md` (current todos and known gaps)
4. `git log --oneline -10` (recent commits)

**Layer 2 — Expand per current task (targeted sections only):**
- Use line-number index in `PROJECT_BRIEF.md` to read only relevant sections of `量化交易系統規格書_shellpig版.md` / `開發設計方針.md` / `測試指南.md`. Don't read entire files.

**Layer 3 — Reference during implementation:**
- `量化交易系統規格書_shellpig版.md` — 
- `開發設計方針.md` — 
- `測試指南.md` — 
- `驗證後已知問題.md` —
- Source code: read as needed per task

Report to user: current progress, and any issues with their scope of impact.

## Project Skills

This project uses local skills from `C:\Users\User\OneDrive\桌面\AI_Work\Skills\`.

Trigger rules:
- Diagnosing bugs / analyzing errors / finding root cause → read `Skills\engineering\diagnose\SKILL.md` first
- Requirements unclear / spec discussion / planning / need to ask clarifying questions → read `Skills\productivity\grill-me\SKILL.md` first
- Normal state / no urgent or special situation → read `Skills\productivity\caveman\SKILL.md` first

Only modify files when user explicitly requests fix, implement, or commit. Verify/diagnose = report only.

## 文件
- `PROJECT_BRIEF.md` — **專案簡報（新 session 入口）**
- `量化交易系統規格書_shellpig版.md` — 個人版規格書（純 Python、台股、DuckDB、AI 問答）
- `開發設計方針.md` — 實作指引（檔案清單、類別簽名、資料契約）
- `測試指南.md` — 測試流程與驗收標準
- `驗證後已知問題.md` — 驗收問題追蹤（每次必讀）
- `未涵蓋資料項目.md` — 目前不抓不存的資料項目

## 技術棧
- **語言：** Python 3.12+（純 Python，無 Rust）
- **資料：** pandas, pandas-ta, FinMind API, yfinance
- **儲存：** DuckDB + Parquet（零伺服器）
- **UI：** Streamlit + Plotly
- **AI：** OpenAI / Anthropic / Gemini（provider-neutral）
- **套件管理：** uv


## 驗證模式規則

當使用者要求「驗證」時，只能進行檢查、讀檔、執行測試、啟動本機服務與回報結果。

除非使用者明確要求「修」、「修改」、「commit」或「提交」，否則不得：

- 修改任何程式碼或文件
- 自行套 patch
- stage 檔案
- 建立 commit

若驗證中發現問題，只列出問題、影響範圍與建議修法，等待使用者下一步指示。

## 修改程式碼授權規則

除非使用者明確要求「修」、「修改」、「實作」、「處理某個 phase」、「commit」或「提交」，否則不得修改任何程式碼、文件或設定檔。

當使用者只是描述錯誤、貼截圖、詢問原因、要求解釋、要求列出問題、要求驗證，或詢問某功能怎麼使用時，只能分析與回報，不得自行套 patch。

## Python 執行環境規則

後續執行測試、匯入驗證、腳本執行時，預設固定使用專案虛擬環境：

- `.\.venv\Scripts\python.exe`

目標是讓 Agent 與使用者看到一致結果，避免誤用其他全域或內建 runtime Python。
