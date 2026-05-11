# 翰林五下社會期末複習卷套件

## 檔案

- `翰林五下社會期末複習卷_B4.docx`：B4 直式，4 面列印版。
- `翰林五下社會期末複習卷_B4.pdf`：同版面 PDF。
- `server.py`：線上施測與老師後台。
- `quiz_records.sqlite3`：線上施測資料庫，啟動後自動建立。

## 啟動線上測驗

在此資料夾執行：

```bash
/Users/simon/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 server.py
```

開啟首頁：

```text
http://127.0.0.1:8765/
```

若學生要用平板或手機掃 QR code，請讓學生裝置與教師電腦在同一個 Wi-Fi，並用教師電腦名稱或區網 IP 開首頁，例如：

```text
http://ChangdeMacBook-Air.local:8765/
```

首頁會顯示學生作答 QR code。老師後台在：

```text
http://127.0.0.1:8765/teacher
```

## 紀錄內容

系統會記錄：

- 班級、座號、姓名
- 作答內容
- 自動初評分數
- 開始、草稿儲存、答案變更、交卷等作答歷程
- 使用秒數

老師後台可檢閱每筆資料，也可下載 CSV。簡答題採關鍵字初評，建議老師以後台詳細答案再人工調整。

## 放到網路上，讓任何網路都能掃 QR 作答

本系統不能只丟到 Google Drive 或一般靜態網頁空間，因為它需要伺服器接收答案、寫入資料庫、提供老師後台。建議部署到 Render、Railway、Fly.io 或學校伺服器。

### Render 部署方式

1. 將 `hanlin-social-final` 這個資料夾放到 GitHub repository。
2. 到 Render 建立新的 Web Service，連接該 repository。
3. Root Directory 設為 `hanlin-social-final`。
4. Start Command 使用：

```bash
python server.py
```

5. 設定環境變數：

```text
ADMIN_PASSWORD=請自行設定老師後台密碼
DB_PATH=/var/data/quiz_records.sqlite3
PUBLIC_BASE_URL=https://你的-render-網址.onrender.com
```

6. 加上 Persistent Disk，掛載路徑設為：

```text
/var/data
```

7. 部署完成後，開啟：

```text
https://你的-render-網址.onrender.com/
```

首頁上的 QR code 就會指向公開網址，學生可用不同網路掃描作答。

### 為什麼要設定 ADMIN_PASSWORD

公開上網後，任何知道網址的人都可能打開老師後台。設定 `ADMIN_PASSWORD` 後，進入 `/teacher`、下載 CSV、讀取作答資料時都會要求密碼。

### 資料保存提醒

如果使用免費或無硬碟的雲端平台，SQLite 檔案可能會在重啟後消失。正式施測請使用 Render Persistent Disk，或改接 PostgreSQL、Supabase、Firebase 等雲端資料庫。
