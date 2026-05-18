# 五下翰林社會第三單元線上測驗

主題：走向民主的中華民國

這是一份可掃描 QR code 作答的線上測驗。學生送出後，系統會記錄作答內容、作答歷程、分數與使用時間；老師可登入後台檢閱資料並下載 CSV。

## 檔案

- `server.py`：線上施測、QR 首頁、老師後台與資料庫 API。
- `quiz_records.sqlite3`：本機測試資料庫，啟動後自動建立。
- `Procfile`、`requirements.txt`、`render.yaml`：Render 部署用。

## 題型與配分

總分 100 分：

- 選擇題 10 題，共 20 分
- 配對題 1 組，共 8 分
- 概念簡答與時序題，共 28 分
- 情境素養題 4 題，共 28 分
- 閱讀與統整簡答，共 16 分

簡答題採關鍵字初評，老師可在後台檢閱後人工調整。

## 本機啟動

```bash
python server.py
```

首頁：

```text
http://127.0.0.1:8765/
```

老師後台：

```text
http://127.0.0.1:8765/teacher
```

## 部署到 Render

1. 將此資料夾上傳到 GitHub repository。
2. 在 Render 建立 Web Service。
3. Start Command 設為：

```bash
python server.py
```

4. 設定環境變數：

```text
ADMIN_PASSWORD=請自行設定老師後台密碼
DB_PATH=/tmp/quiz_records.sqlite3
PUBLIC_BASE_URL=https://你的-render-網址.onrender.com
```

Free 版可先使用 `/tmp/quiz_records.sqlite3`，但資料可能因服務重啟消失。正式施測建議使用 Persistent Disk，並改成：

```text
DB_PATH=/var/data/quiz_records.sqlite3
```

Persistent Disk 掛載路徑：

```text
/var/data
```

## 使用方式

部署完成後開啟公開網址首頁，投影或分享 QR code 給學生。學生作答網址會是：

```text
https://你的-render-網址.onrender.com/quiz
```

老師後台：

```text
https://你的-render-網址.onrender.com/teacher
```

公開上網時請務必設定 `ADMIN_PASSWORD`，避免學生資料被未授權檢閱。
