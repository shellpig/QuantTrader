# QuantTrader

股市量化交易系統開發專案。

## 專案目標
建立一套 Python + Rust 混合架構的量化交易系統，支援台股、美股、加密貨幣，涵蓋策略研發、回測、實盤交易全生命週期。

## 文件
- `量化交易系統規格書_V3.0.md` — 完整系統規格書（語言評估、4 階段開發計畫、風控、OMS/EMS、部署）
- `量化交易系統規格書_shellpig版.md` — 個人版規格書（純 Python、台股、DuckDB、Claude AI 問答）

## 技術棧
- **研究層：** Python (Pandas, NumPy, Jupyter)
- **執行層：** Rust (tokio, PyO3)
- **通訊：** gRPC (Protocol Buffers)
- **資料庫：** TimescaleDB, Redis
- **監控：** Prometheus + Grafana

---

## AI 協作工作流程（Claude + Gemini 聯合討論）

本專案採用雙 AI 協作模式進行設計決策與文件產出。用戶作為兩個 AI 之間的中繼。

### 流程說明

```
Claude 撰寫需求/問題
        ↓
用戶將內容轉貼給 Gemini
        ↓
Gemini 產出結果，用戶貼回給 Claude
        ↓
Claude Review Gemini 的產出
        ↓
Claude 有疑慮 → 以「提問」方式表達（不直接指示修改）
        ↓
用戶將 Claude 的提問轉貼給 Gemini
        ↓
Gemini 給出新想法，用戶貼回給 Claude
        ↓
重複直到 Claude 滿意為止 → 完成
```

### 重要原則

- **Claude 對 Gemini 的回應方式是「提出疑慮 + 詢問想法」**，而非「這裡錯了，改成這樣」
- 目的是讓 Gemini 有機會提出 Claude 未考慮到的角度，避免淪為單向指令
- Claude 負責最終 Review，確認產出符合 shellpig 版規格的設計原則
- 用戶是唯一的人類決策者，兩個 AI 的結論有衝突時由用戶裁決
