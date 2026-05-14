# Phase 10 個股分析頁 — 實作指引

> 對象：將 Claude Design 產出的設計稿移植到 [web/](web/)（Next.js + Tailwind）的實作者。
> 任務範圍：**只做「個股分析」單一頁面**，回測 / 資料管理 / AI 問答 / 設定 四頁不在本次範圍。

---

## 1. 設計來源

| 項目 | 位置 |
|---|---|
| 設計截圖 | 由 Claude Design 提供（單頁不捲動版本，台積電 2330 樣式可在 `docs/mock_dashboard_payload.json` 對照） |
| 設計沙箱路徑（**僅供 Claude Design 內部使用**） | `ui_kits/quanttrader-web/index.html` |
| 既有 Streamlit 實作（功能對照基準） | [src/ui/pages/dashboard.py](src/ui/pages/dashboard.py) |
| 後端服務層（payload 來源） | [src/services/dashboard_service.py](src/services/dashboard_service.py) |
| Mock API 回應（真實 2330 資料） | [docs/mock_dashboard_payload.json](docs/mock_dashboard_payload.json) |

實作前**先讀** mock JSON——所有欄位、單位、邊界值都在裡面。

---

## 2. 後端 API（尚未存在，需新增）

`api/routers/` 目前只有 `config / data / jobs`。本頁需要新增：

```
GET /api/dashboard/{symbol}?market=tw|us&bars=120

回傳：DashboardPayload (JSON)
```

實作者**不需要寫**這個 endpoint。後端負責的人會以 `src/services/dashboard_service.build_dashboard_payload()` 包成 FastAPI router；屆時前端只要 `fetch(/api/dashboard/2330?market=tw)` 即可。

開發階段請以 `docs/mock_dashboard_payload.json` 作為 SWR/fetch 的假回應。

### Payload schema 快速對照

| JSON 欄位 | UI 區塊 | 缺值時行為 |
|---|---|---|
| `symbol` / `subject_name` / `analysis_time` | 頁首標題列 | — |
| `quote` | 報價列（O/H/L/PC/V/內外盤）| 美股可能為 `null` |
| `technical` | 右側「技術分析總覽」+「關鍵價位」 | 必有 |
| `chip` | 右側「籌碼分析」| 美股為 `null` |
| `chip_recent_df` | 籌碼「查看 5 日明細」Drawer | 美股為 `[]` |
| `bid_ask` | 籌碼區頂部「買賣力道」**（截圖缺）** | 五檔不可用時為 `null` |
| `candle_patterns` | 底部「K 線型態」 | 必有（每項含 `detected: bool`） |
| `chart_patterns` | 底部「K 線型態」附加段 | 必有（W底 / M頭） |
| `multi_timeframe` | 底部「多週期·量價」 | 必有 |
| `analysis` | 底部「隔日操作劇本」 | AI 關閉時為 `null`，顯示「啟用 AI 預覽」CTA |
| `ai_enabled` | 控制劇本區顯示狀態 | `false` 時不發 AI 請求 |

---

## 3. 設計截圖已對齊的部分（直接照刻）

以下項目截圖實作正確，照搬即可：

- 頁首：market toggle（台股 / 美股）、symbol input、分析 / 即時更新按鈕
- 報價列：`O / H / L / PC / V / 內外盤`，密度往 Bloomberg terminal 看齊
- 中央 K 線圖：MA5 / MA20 / MA60 + 下方 VOL bars，日 K / 週 K / 月 K / 分 K tab
- 右上「技術分析總覽」：趨勢方向、MA、KD、MACD、RSI 14、成交量、量價關係、乖離 MA20、短線分數，每項旁掛 ℹ️ icon
- 右中「關鍵價位」：壓力區 / 支撐區，數值來自 `technical.resistance_levels[]` / `support_levels[]`
- 右下「籌碼分析 近 5 日」：外資 / 投信 / 自營商買賣超 + 籌碼集中度
- 底部「K 線型態」表：照 `candle_patterns[]` 渲染（`detected=true` 標「成立」，反之「未成」）
- 底部「多週期·量價」上半：日 / 週 / 月 K 趨勢與強度
- 底部「隔日操作劇本」：預設顯示「AI · OFF」+「啟用 AI 預覽」CTA（不發 AI 請求）

---

## 4. 設計截圖**缺**的部分（請補上）

四項功能在舊 Streamlit 有、但截圖未呈現。位置、UI 樣式、tooltip 文案如下。

### 4.1 買賣力道估算（**重要**）

**資料來源**：`bid_ask` 物件，欄位 `label`（如「賣壓較重」）、`bid_ratio`、`ask_ratio`、`total_bid_vol`、`total_ask_vol`。

**位置**：右側「籌碼分析」面板**最頂端**，在「外資 / 投信 / 自營商」之前獨立一格。

**UI 示意**：

```
┌─ 籌碼分析 近 5 日 ───── ℹ️ ───┐
│                                │
│ 買賣力道  ℹ️    賣壓較重 🔴   │   ← 新增
│   買方 20.08% / 賣方 79.92%   │
│                                │
│ ─────────────────────────     │
│ 外資  ℹ️    買超  +86 張      │
│ 投信  ℹ️    買超  +36 張      │
│ ...                            │
```

**Tooltip 文字**（直接照抄）：
> 以五檔掛單量估算買賣力道。買方掛量佔比高表示買盤積極，但掛單可能撤單，僅供即時參考。

**美股**：`bid_ask` 為 `null` 時，這一格不顯示（不要顯示 placeholder）。

---

### 4.2 量價結構分析三段（**重要**）

**資料來源**：`technical.volume_price_divergence`、`technical.ma_bias`、`technical.operation_observation` — 三段獨立的人類可讀文字。

**位置**：底部「多週期·量價」格的**下半部**，在「日/週/月 K」表格之下加一個副區。

**UI 示意**：

```
┌─ 多週期 · 量價 ───────────────┐
│ 日 K  多頭  強                  │
│ 週 K  多頭  中強                │
│ 月 K  多頭  強                  │
│                                 │
│ ─── 量價結構 ──────────────    │   ← 新增副區（標題分隔）
│ • 量價背離 ℹ️                   │
│   量價背離：價漲量縮（短線整理）  │
│ • 均線乖離 ℹ️                   │
│   與 MA20 乖離約 +4.00%，偏高   │
│ • 操作觀察 ℹ️                   │
│   目前趨勢：多頭趨勢。量價背離… │
└────────────────────────────────┘
```

**Tooltip 文字**：

- 量價背離：
  > 量價背離（如價漲量縮）表示方向缺乏成交量配合；量價同步（如價漲量增）通常代表趨勢可信度較高。
- 均線乖離：
  > 乖離率 = (收盤 - MA20) / MA20 × 100%。常用來觀察短線偏離程度；乖離過大後，價格可能向均線回歸。
- 操作觀察：
  > 此欄為系統規則判讀結論，整合趨勢、量價、乖離與籌碼。不是 AI 生成，也不構成投資建議。

**注意**：原 Streamlit 右側「技術分析總覽」也有 `量價關係` 一行（顯示「價漲量縮（短整）」這種短結論）——請保留，與此處的展開三段並存（短結論在右側、長解釋在底部）。

---

### 4.3 融資 / 融券餘額變化

**資料來源**：`chip.margin_balance_change`（張）、`chip.short_balance_change`（張）。

**位置**：右側「籌碼分析」面板內，在「自營商」之下、「籌碼集中度」之上，兩個小欄位並排。

**UI 示意**：

```
│ 自營商  ℹ️    賣超  -52 張    │
│ ─────────────────────────    │
│ 融資 ℹ️   +785 張             │   ← 新增
│ 融券 ℹ️    -9 張              │
│ ─────────────────────────    │
│ 籌碼集中度  ℹ️   趨於穩定     │
```

**Tooltip 文字**：

- 融資：
  > 融資是借錢買股。融資餘額增加常代表散戶風險偏好上升；快速增加且股價不漲時需提高警覺。
- 融券：
  > 融券是借券賣出（放空）。融券餘額增加常代表看空力道增強；大量回補可能形成軋空。

**美股**：與 `chip` 同步隱藏。

---

### 4.4 三大法人近 5 日逐日明細

**資料來源**：`chip_recent_df`，每列含 `日期 / 外資 / 投信 / 自營商` 四欄。

**位置**：右側「籌碼分析」面板**標題列右側**加一個小按鈕「查看 5 日明細」或 ⓘ icon。點擊後彈出 **Drawer（右側抽屜）或 Modal**，**不要塞主畫面**——這是避免破壞「單頁不捲動」原則的關鍵。

**UI 示意（Drawer 內容）**：

```
┌─ 三大法人 近 5 交易日（張）──── ✕ ┐
│                                   │
│ 日期        外資     投信   自營商 │
│ 2026-05-07  +3885   +1433   +148  │
│ 2026-05-08   -857   +1268   +107  │
│ 2026-05-11 -17753     -53     -7  │
│ 2026-05-12  -9237   +8879   +424  │
│ 2026-05-13 -11970   +5473   -588  │
│                                   │
│  正數紅、負數綠（買進為紅、賣出為綠）│
└───────────────────────────────────┘
```

**色彩規範**：依台股慣例「紅買綠賣」。

**美股**：按鈕隱藏（`chip_recent_df` 為空陣列）。

---

## 5. 名詞說明字典（ℹ️ tooltip 文案）

所有 tooltip 文案以下表為準，**請勿自行改寫**——這些文字經過 Phase 8-G 人工驗收。

| Key | 對應 UI 位置 | 文案 |
|---|---|---|
| `trend_direction` | 趨勢方向 | 根據 5 日、20 日、60 日移動平均線（MA）的排列判定。MA5 > MA20 > MA60 為多頭趨勢；反之為空頭趨勢；交錯排列為盤整。移動平均線是過去 N 日收盤價平均，用來平滑短期波動並觀察趨勢。 |
| `ma_status` | MA 狀態 | 觀察 MA5、MA20、MA60 的相對位置。多頭排列代表短中長期均價依序墊高；空頭排列相反；均線糾結表示方向不明，常見於盤整或轉折期。 |
| `kd_status` | KD | KD 指標衡量收盤價在近期高低區間中的位置，由 K 與 D 組成（0~100）。K 上穿 D 為黃金交叉（偏多），K 下穿 D 為死亡交叉（偏空）。K、D 皆 > 80 常視為高檔鈍化，皆 < 20 常視為低檔鈍化。 |
| `macd_status` | MACD | MACD 由 DIF（12EMA-26EMA）與 DEA（DIF 的 9EMA）構成。DIF > 0 且 DIF > DEA 為正值擴張（多方增強）；DIF > 0 且 DIF ≤ DEA 為正值收斂（多方轉弱）；空方區同理。 |
| `volume_status` | 成交量 | 比較今日量與近 5 日均量倍數。> 1.5 倍為量能放大，> 3 倍為爆量；0.7~1.5 倍為正常；< 0.7 倍為量縮。量能常用來判斷價格趨勢是否有足夠參與度支持。 |
| `volume_price_relation` | 量價關係（右側結論行） | 結合漲跌與量能的判讀。價漲量增通常較健康；價漲量縮表示追價力道偏弱；價跌量增代表賣壓較重；價跌量縮可能是賣壓趨緩。 |
| `resistance` | 壓力區 | 壓力區是股價上行時可能遇到賣壓的價位。本系統使用近 60 日高點與近 20 日高點作為壓力參考。 |
| `support` | 支撐區 | 支撐區是股價下行時可能出現承接買盤的價位。本系統使用近期低點、MA20、MA60 作為支撐參考。 |
| `short_term_score` | 短線分數 | 短線綜合分數由四面向加權：均線結構 30%、KD 25%、量價關係 25%、突破狀態 20%。分級：70% 以上強勢偏多；50% 以上且未滿 70% 中等偏多；30% 以上且未滿 50% 中性；未滿 30% 偏空。 |
| `foreign` | 外資 | 外資是外國機構投資人，通常是台股最大法人資金來源。買超常被視為偏多，但可能包含避險或 ETF 調倉等非方向性交易。 |
| `trust` | 投信 | 投信是共同基金管理機構。投信買超常代表基金經理人中期看法偏多，操作多偏波段。 |
| `dealer` | 自營商 | 自營商是券商自有資金部位。交易節奏通常較短，部分部位可能屬避險用途。 |
| `chip_concentration` | 籌碼集中度 | 觀察近 N 日法人淨買賣方向一致性。連續同向買入偏向籌碼集中（偏多），連續同向賣出偏分散（偏空），交錯則偏中性。 |
| `margin_balance` | 融資（4.3 新增） | 融資是借錢買股。融資餘額增加常代表散戶風險偏好上升；快速增加且股價不漲時需提高警覺。 |
| `short_balance` | 融券（4.3 新增） | 融券是借券賣出（放空）。融券餘額增加常代表看空力道增強；大量回補可能形成軋空。 |
| `bid_ask` | 買賣力道（4.1 新增） | 以五檔掛單量估算買賣力道。買方掛量佔比高表示買盤積極，但掛單可能撤單，僅供即時參考。 |
| `volume_price_divergence` | 量價背離（4.2 新增） | 量價背離（如價漲量縮）表示方向缺乏成交量配合；量價同步（如價漲量增）通常代表趨勢可信度較高。 |
| `ma_bias` | 均線乖離（4.2 新增 / 右側乖離 MA20） | 乖離率 = (收盤 - MA20) / MA20 × 100%。常用來觀察短線偏離程度；乖離過大後，價格可能向均線回歸。 |
| `operation_observation` | 操作觀察（4.2 新增） | 此欄為系統規則判讀結論，整合趨勢、量價、乖離與籌碼。不是 AI 生成，也不構成投資建議。 |
| `timeframe_daily` | 多週期·日 | 日線反映短期（數日至數週）趨勢方向與強度。 |
| `timeframe_weekly` | 多週期·週 | 週線由日線彙總：開盤取該週第一個有效交易日、收盤取該週最後一個有效交易日，高低點取週內極值、成交量取週總量，反映中期（數週至數月）趨勢。 |
| `timeframe_monthly` | 多週期·月 | 月線由日線彙總而成，反映長期（數月至數年）趨勢。 |
| `timeframe_strength` | 多週期·強度說明 | 趨勢強度依均線排列與 RSI 綜合判定。日、週、月線方向一致時，通常代表趨勢一致性較高。 |

### K 線型態詳細說明（hover/click 時顯示）

| 型態 | 說明 |
|---|---|
| 長紅 K | 當日陽線實體明顯放大，代表買盤主導；低檔出現時常被視為轉強訊號。 |
| 長黑 K | 當日陰線實體明顯放大，代表賣壓主導；高檔出現時常被視為轉弱訊號。 |
| 十字線 | 開收接近、實體很小，表示多空拉鋸；趨勢末端出現時需留意反轉風險。 |
| 錘子 | 長下影短上影，常見於跌勢末端，代表低檔有承接，可能止跌反彈。 |
| 吊人 | 形態近似錘子但出現在漲勢中，代表上方追價動能可能轉弱。 |
| 吞噬 | 今日實體完全包覆前日實體，多空力道轉換明顯，屬較強反轉訊號。 |
| 晨星 | 三根 K 的底部反轉型態，常解讀為空方衰竭後多方接手。 |
| 夜星 | 晨星反向型態，常解讀為多方衰竭後空方轉強。 |
| 帶上影線 | 上影明顯偏長，表示盤中上攻遇壓，短線上檔賣壓較重。 |
| 帶下影線 | 下影明顯偏長，表示盤中下殺有撐，短線下檔承接較強。 |
| W底（雙底） | 兩低點接近且突破頸線後成立，常作為中短期轉強訊號。 |
| M頭（雙頂） | 兩高點接近且跌破頸線後成立，常作為中短期轉弱訊號。 |

---

## 6. AI 劇本啟用流程

「隔日操作劇本」區塊有三個狀態：

| `ai_enabled` | `analysis` | UI 顯示 |
|---|---|---|
| `false` | `null` | 灰階占位 + CTA：「AI · OFF」「啟用 AI 預覽」按鈕 |
| `true` | 物件 | 三情境卡片：開高走高 / 震盪整理 / 開低回測，每張顯示進場價 / 停損 / 目標 |
| `true` | `null` | 「AI 分析失敗，請稍後重試」（後端設定錯誤或 API 配額用盡） |

**啟用 AI 預覽 CTA** 點擊後行為（前端只需顯示，不需實作開關邏輯）：
- 預期：呼叫後端切換 `config.ai.enabled = true`，重新 fetch payload
- 失敗：顯示「請先於設定頁配置 API Key」並提供連到設定頁的連結

**重要**：截圖中「啟用 AI 預覽」目前只是占位，實際後端切換流程由後端負責人定義；前端先做 UI 與 disabled / loading 狀態即可。

---

## 7. 美股市場差異

切到「美股」時，以下整區隱藏或灰階：

- ❌ 即時報價列（無 TWSE MIS）→ `quote` 為 `null`
- ❌ 買賣力道估算（依賴五檔）→ `bid_ask` 為 `null`
- ❌ 籌碼分析整個面板 → `chip` 為 `null`、`chip_recent_df` 為 `[]`
- ❌ 融資 / 融券 → 同上
- ✅ 技術分析總覽、關鍵價位、K 線型態、多週期、AI 劇本 → 照常顯示
- ✅ 美股使用 **adjusted** 日 K（split-adjusted），不顯示「股」單位數量

切換市場時請 reset state（避免顯示前一市場殘留資料）。

---

## 8. 字型與色彩

- **字型**：JetBrains Mono（已決定）。請用 `next/font` 匯入，不要 CDN。
  ```ts
  import { JetBrains_Mono } from 'next/font/google'
  const mono = JetBrains_Mono({ subsets: ['latin'], variable: '--font-mono' })
  ```
- **數字色彩**：紅漲綠跌（台股慣例，**不要**用美股的綠漲紅跌）。所有金額、漲跌幅、買賣超欄位都遵守。
- **AI OFF 狀態**：占位區用 `text-muted-foreground` 與較低對比，明確區別「有資料」vs「未啟用」。

---

## 9. 驗收標準

實作完成後請確認：

1. **1440×900 viewport 不捲動**可看完整頁（含上述 4 項補上的元件）
2. **1920×1080 / 2560×1440** 不會出現大量留白（用 `max-width` + 中央對齊或欄寬自適應）
3. 所有 ℹ️ tooltip 內容與第 5 節文案**逐字一致**
4. 切換台股 / 美股時，籌碼相關區塊正確隱藏
5. AI OFF 狀態下，劇本區**不發出 AI API 請求**（用 mock JSON 開發時自然 OK；接真實後端時需驗證）
6. 用 `docs/mock_dashboard_payload.json` 渲染，畫面與設計稿吻合（除去本文第 4 節補上的元件）

---

## 10. Next.js 整合須知（必讀）

本章補齊「實作者在 [web/](web/) 中要怎麼動手」。**先讀完本章再開始寫**，避免重複造輪子或踩到既有 scaffold。

### 10.1 既有 scaffold 結構

Phase 10-B 已建立的可重用基礎，**請沿用、不要重寫**：

```
web/
├── package.json              ── Next 15 + React 19 + Tailwind 4 + SWR + lightweight-charts + Radix UI
├── src/
│   ├── app/
│   │   ├── layout.tsx        ── 根 layout（含 Sidebar、ThemeProvider、Inter 字型、max-w-7xl 容器）
│   │   ├── globals.css       ── Tailwind v4 globals + theme tokens
│   │   ├── page.tsx          ── 首頁
│   │   ├── dashboard/page.tsx  ← 【實作目標：覆蓋這個 placeholder】
│   │   ├── backtest/page.tsx ── 其他頁面 placeholder，不要動
│   │   ├── data/page.tsx
│   │   ├── ai/page.tsx
│   │   └── settings/page.tsx
│   ├── components/
│   │   ├── sidebar.tsx           ── 左側導覽（已連好 /dashboard），不要動
│   │   ├── market-switcher.tsx   ── 台股/美股 toggle，請直接 import 使用
│   │   ├── stock-selector.tsx    ── 股票代碼輸入（Enter 送出），請直接 import 使用
│   │   └── theme-provider.tsx    ── 主題切換，不要動
│   ├── lib/
│   │   ├── api-client.ts     ── apiFetch / apiGet / ApiClientError，用這個發 HTTP
│   │   ├── formatters.ts     ── formatNumber / formatPct / formatVolume / changeColor，全部沿用
│   │   └── utils.ts          ── cn() helper
│   └── types/
│       ├── analysis.ts       ← 【實作目標：要重寫，schema 已過時，見 §10.3】
│       ├── market.ts         ── 沿用 Market type 與 MARKET_LABELS
│       ├── backtest.ts       ── 與本頁無關
│       └── config.ts         ── 之後可能需要讀 ai.enabled
```

### 10.2 路徑與檔案落點

| 任務 | 檔案 |
|---|---|
| 主頁面 | **覆蓋** [web/src/app/dashboard/page.tsx](web/src/app/dashboard/page.tsx)（目前是 placeholder） |
| 重寫 types | **覆蓋** [web/src/types/analysis.ts](web/src/types/analysis.ts) |
| 新增 SWR hooks | `web/src/lib/hooks/useDashboard.ts`（新增） |
| 新增 dashboard-only components | `web/src/components/dashboard/`（新增資料夾，依需要拆檔） |
| Mock 資料 | 複製 `docs/mock_dashboard_payload.json` 到 `web/public/mock/dashboard_2330.json` 供 dev 用 |
| 測試 | `web/src/tests/components/dashboard/*.test.tsx` |

**不要**：建立新的 layout、新的 sidebar、新的 routing 結構。

### 10.3 TypeScript types — 必須重寫

[web/src/types/analysis.ts](web/src/types/analysis.ts) 的 schema 與後端**完全不一致**（例如把 `ma_status: string` 寫成 `ma5/ma20/ma60: number`、加了不存在的布林通道 `bb_*` 欄位）。

**唯一真實來源**：[docs/mock_dashboard_payload.json](docs/mock_dashboard_payload.json) 與後端 dataclass（見指引附錄 B）。

實作者要做的：
1. 讀完 mock JSON，重新寫 `TechnicalSummary / ChipSummary / BidAskStructure / RealtimeQuote / DashboardAnalysis / TradingScenario / PriceLevel / OhlcvBar / CandlePattern / ChartPatternResult / MultiTimeframeAnalysis / TimeframeTrend` 等 interface
2. 加上 `DashboardPayloadResponse` 整合型別
3. **嚴禁猜欄位**——mock JSON 沒有的欄位就不要加

特別注意：
- `OhlcvBar.date` 是 ISO 帶時區字串（`"2025-11-11T00:00:00+08:00"`），不是 `"YYYY-MM-DD"`
- `RealtimeQuote` 含 `best_bid[] / best_ask[] / best_bid_vol[] / best_ask_vol[]`（五檔）
- `BidAskStructure` 是獨立物件，不是 `RealtimeQuote` 內欄位
- 數字欄位區分「整數張」與「浮點價格」，前者不要 toFixed

### 10.4 資料層：SWR + 條件式 fetcher

**dev / Phase 10-D 開發階段**：mock JSON 為主，後端 endpoint 尚未存在。

新增 `web/src/lib/hooks/useDashboard.ts`：

```ts
import useSWR from "swr";
import type { DashboardPayloadResponse } from "@/types/analysis";
import type { Market } from "@/types/market";

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK_DASHBOARD === "1";

export function useDashboard(symbol: string | null, market: Market) {
  const key = symbol ? `dashboard/${market}/${symbol}` : null;

  return useSWR<DashboardPayloadResponse>(
    key,
    async () => {
      if (USE_MOCK) {
        const res = await fetch(`/mock/dashboard_${symbol}.json`);
        if (!res.ok) throw new Error("mock not found");
        return res.json();
      }
      // 真實後端尚未實作，先 throw 避免靜默失敗
      throw new Error("Real dashboard endpoint not yet wired");
    },
    { revalidateOnFocus: false, dedupingInterval: 30_000 },
  );
}
```

開發時設 `NEXT_PUBLIC_USE_MOCK_DASHBOARD=1`（放 `web/.env.local`）。

**Phase 10-E（後端串接後）**：把 mock 分支換成 `apiGet<DashboardPayloadResponse>('/api/dashboard/' + symbol + '?market=' + market)`，並注意後端會包 `ApiResponse<T>` envelope（`{ data, meta }`），到時要 `.data` 取出。

### 10.5 K 線圖：lightweight-charts v5

`lightweight-charts: ^5.0.5` 已安裝，**就用這個**。

關鍵 API：
- `createChart(container, options)` 建圖
- `chart.addCandlestickSeries({ upColor, downColor, ... })` 主圖
- `chart.addHistogramSeries({ priceScaleId: '' })` 成交量副圖（不同 priceScale）
- `chart.addLineSeries(...)` 為 MA5 / MA20 / MA60
- 顏色：上漲紅（`#ef4444` 系）、下跌綠（`#22c55e` 系）— **台股慣例**
- 響應式：用 `ResizeObserver` 監聽容器寬度變化呼叫 `chart.applyOptions({ width })`
- 在 `useEffect` cleanup 時呼叫 `chart.remove()`

V5 注意事項：API 命名與 v4 不同；遇到問題優先看官方 v5 文件，不要套 v4 教學。

### 10.6 既有 components 怎麼用

```tsx
// dashboard/page.tsx
"use client";

import { useState } from "react";
import { MarketSwitcher } from "@/components/market-switcher";
import { StockSelector } from "@/components/stock-selector";
import { useDashboard } from "@/lib/hooks/useDashboard";
import type { Market } from "@/types/market";

export default function DashboardPage() {
  const [market, setMarket] = useState<Market>("tw");
  const [symbol, setSymbol] = useState<string | null>(null);
  const [pendingSymbol, setPendingSymbol] = useState("");

  const { data, error, isLoading, mutate } = useDashboard(symbol, market);

  return (
    <div className="...">
      {/* 頁首 */}
      <header>
        <MarketSwitcher value={market} onChange={setMarket} />
        <StockSelector
          market={market}
          value={pendingSymbol}
          onChange={setPendingSymbol}
        />
        <button onClick={() => setSymbol(pendingSymbol)}>分析</button>
        <button onClick={() => mutate()} disabled={!symbol}>即時更新</button>
      </header>

      {/* 主版面 */}
      {isLoading && <DashboardSkeleton />}
      {error && <DashboardError error={error} />}
      {data && <DashboardContent payload={data} market={market} />}
    </div>
  );
}
```

### 10.7 Layout 與 viewport 約束

根 layout 目前用 `container mx-auto px-4 py-6 max-w-7xl` (= 1280px 寬度上限)。**這對 1440×900 不捲動會失敗**——容器邊緣會留白，內容被擠壓。

實作者請：
1. 在 [web/src/app/dashboard/page.tsx](web/src/app/dashboard/page.tsx) 用 React Server Component / Client Component 包裝後，**自行撐到 viewport 寬度**（不要受 layout container 限制）
2. 作法：在頁面外層加 `className="-mx-4 -my-6 lg:-ml-0"` 或乾脆改根 layout 把容器約束移到 `<children>` 之內、讓特定頁面可以 opt-out
3. 建議：用 CSS Grid `grid-cols-[1fr_320px]` 切左中右兩欄（中央圖表 + 右側面板），底部三格用 `grid-cols-3`

**驗收基準**（與指引 §9 一致）：
- 1440×900：剛好不捲動
- 1920×1080：右側面板不要過寬，圖表區自動延伸
- 2560×1440：頁面 max-width 設個合理上限（e.g. 2400px）避免過鬆

### 10.8 顏色 / 字型 token

#### 字型

根 layout 已用 Inter 作為 `--font-sans`。**新增** JetBrains Mono 作為 `--font-mono`（用於數字、表頭、tabular 內容）：

```tsx
// app/layout.tsx 加入
import { Inter, JetBrains_Mono } from "next/font/google";
const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });
// body className 改成 `${inter.variable} ${mono.variable}`
```

數字欄位（價格、漲跌、買賣超、KD/MACD 數值）統一加 `font-mono` class。

#### 紅綠規則

**直接用既有的 [formatters.ts](web/src/lib/formatters.ts) 裡的 `changeColor(value, market)`**——它已正確處理台股紅漲綠跌、美股綠漲紅跌的差異，回傳 `text-rise / text-fall / text-neutral` class（這些 class 需在 `globals.css` 或 `tailwind` theme 內定義對應顏色）。

如果 `globals.css` 還沒有對應 token，請補上：

```css
:root {
  --color-rise: #ef4444;   /* 漲（台股紅、美股下跌時用） */
  --color-fall: #22c55e;   /* 跌（台股綠、美股上漲時用） */
  --color-neutral: oklch(...);
}
.text-rise { color: var(--color-rise); }
.text-fall { color: var(--color-fall); }
```

K 線圖、成交量柱、`bid_ask` 標籤（賣壓較重 / 買盤積極）也用同一組色。

### 10.9 Loading / Error / Empty 狀態

| 狀態 | UI |
|---|---|
| 未輸入 symbol | 主版面置中提示「請輸入股票代碼或名稱後點選『分析』」 |
| `isLoading` | Skeleton：頁首正常顯示，主版面顯示 6~8 個 `animate-pulse` 灰色矩形對應各區塊位置 |
| `ApiClientError` (404 SYMBOL_NOT_FOUND) | 主版面顯示「{symbol} 尚無可用日線資料」+ 重試按鈕 |
| 其他 error | 顯示通用「分析失敗：{message}」+ 重試 |
| 美股 + 籌碼相關區塊 | 整塊隱藏（不要顯示 disabled placeholder，避免占版面） |
| `bid_ask = null` | 「買賣力道」格隱藏（非交易時段或五檔不可用） |
| `analysis = null` + `ai_enabled = true` | 劇本區顯示「AI 分析失敗，請稍後重試」 |

### 10.10 「即時更新」與「啟用 AI 預覽」的範圍邊界

| 按鈕 | Phase 10-D 範圍 | Phase 10-E+ 範圍 |
|---|---|---|
| 即時更新 | 呼叫 `mutate()` 重新觸發 SWR fetch（mock 模式下會重撈同一份 JSON） | 接真實後端後自然生效 |
| 啟用 AI 預覽 | **只做 UI**：點擊後 toast 顯示「請先於設定頁啟用 AI（Phase 10-E 完成串接）」，按鈕保持 disabled / 半透明 | PATCH `/api/config` 切換 `ai.enabled`，重抓 payload |

**不要在 Phase 10-D 直接呼叫 OpenAI / Anthropic API**，所有 AI 行為都要透過後端代理。

### 10.11 測試

既有用 vitest + @testing-library/react。實作者請補：

1. `useDashboard` hook 單元測試（mock fetch、驗證 `revalidateOnFocus: false`）
2. `<MarketSwitcher>` 切換時 `useDashboard` 的 key 會變
3. payload 渲染時，紅綠色 class 正確套用（台股 vs 美股場景）
4. AI OFF 時不發出任何 AI 相關請求（spy fetch）
5. K 線圖 mount / unmount 不洩漏（spy `chart.remove`）

```bash
cd web && pnpm test
```

### 10.12 開發環境啟動

```bash
# 後端（非必要，dev 用 mock 即可）
.venv/Scripts/python.exe -m uvicorn api.main:app --reload --port 8000

# 前端
cd web
echo NEXT_PUBLIC_USE_MOCK_DASHBOARD=1 > .env.local
pnpm install        # 若 node_modules 未安裝
pnpm dev            # 預設 http://localhost:3000/dashboard
```

實作者完成後請：
1. 至少在 Chrome 1440×900、1920×1080 兩種視窗大小驗收
2. 跑 `pnpm test` 全綠
3. 跑 `pnpm build` 無 TypeScript error
4. 跑 `pnpm lint` 無 ESLint error

---

## 附錄 A：產出 mock JSON 的方式

```bash
.venv/Scripts/python.exe scripts/dump_dashboard_payload_example.py
```

腳本：[scripts/dump_dashboard_payload_example.py](scripts/dump_dashboard_payload_example.py)
輸出：[docs/mock_dashboard_payload.json](docs/mock_dashboard_payload.json)（約 29 KB，含 120 日 K + 全部欄位）

要換股票或加長 K 線：修改腳本內 `build_dashboard_payload("2330", ...)` 與 `DAILY_TAIL_BARS`。

## 附錄 B：相關後端模組（前端不需引用，僅供查欄位定義）

| 模組 | dataclass | 用途 |
|---|---|---|
| [src/analysis/technical_summary.py](src/analysis/technical_summary.py) | `TechnicalSummary` / `PriceLevel` | 技術分析總覽 |
| [src/analysis/chip_analysis.py](src/analysis/chip_analysis.py) | `ChipSummary` | 籌碼 |
| [src/analysis/pattern.py](src/analysis/pattern.py) | `CandlePattern` / `ChartPatternResult` / `MultiTimeframeAnalysis` | 型態與週期 |
| [src/data/realtime.py](src/data/realtime.py) | `RealtimeQuote` / `BidAskStructure` | 即時報價與買賣力道 |
| [src/ai/advisor.py](src/ai/advisor.py) | `DashboardAnalysis` / `TradingScenario` | AI 劇本 |
| [src/services/dashboard_service.py](src/services/dashboard_service.py) | `DashboardPayload` | 整合所有上述資料 |
