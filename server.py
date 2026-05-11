from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlparse
import base64
import csv
import hmac
import html
import io
import json
import os
import socket
import sqlite3
import time
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("DB_PATH", ROOT / "quiz_records.sqlite3"))
PORT = int(os.environ.get("PORT", "8765"))
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")


QUESTIONS = [
    {"id": "q1", "type": "choice", "score": 2, "answer": "B", "prompt": "臺灣各區域發展不同，最可能和下列哪一組因素有關？", "options": {"A": "星座、血型、人口年齡", "B": "地形、交通、歷史、產業", "C": "電視節目、運動項目、飲食習慣", "D": "學校數量、班級人數、考試次數"}, "explain": "區域發展會受到自然條件與人文條件共同影響。"},
    {"id": "q2", "type": "choice", "score": 2, "answer": "B", "prompt": "東部地區發展較晚，主要原因之一是：", "options": {"A": "完全沒有河川", "B": "受到山脈阻隔，交通較不便利", "C": "沒有任何自然景觀", "D": "人們不能從事觀光活動"}, "explain": "東部受中央山脈、海岸山脈等地形影響，交通建設較不容易。"},
    {"id": "q3", "type": "choice", "score": 2, "answer": "A", "prompt": "下列哪一項最能說明「交通建設影響區域發展」？", "options": {"A": "高速公路通車後，南北往來更方便", "B": "學生每天要寫聯絡簿", "C": "天氣熱時大家穿短袖", "D": "考試前要複習"}, "explain": "高速公路是交通建設，會促進人流、物流與區域交流。"},
    {"id": "q4", "type": "choice", "score": 2, "answer": "C", "prompt": "臺灣經濟發展歷程較合理的順序是：", "options": {"A": "高科技 → 農業 → 工業", "B": "工業 → 農業 → 高科技", "C": "農業 → 工業 → 高科技", "D": "農業 → 高科技 → 工業"}, "explain": "臺灣大致由農業社會轉向工業，再發展高科技產業。"},
    {"id": "q5", "type": "choice", "score": 2, "answer": "B", "prompt": "十大建設對臺灣的主要影響是：", "options": {"A": "讓臺灣完全沒有環境問題", "B": "促進交通、能源、工業與都市發展", "C": "使所有人都搬到離島", "D": "讓農業完全消失"}, "explain": "十大建設帶動交通、能源、工業與都市發展。"},
    {"id": "q6", "type": "choice", "score": 2, "answer": "A", "prompt": "臺灣能發展高科技產業，和下列哪一項關係最密切？", "options": {"A": "科學園區、人才培育、研發投資", "B": "只有靠天氣好", "C": "完全不需要教育", "D": "只靠進口產品"}, "explain": "高科技產業需要人才、研發、資金、企業與政府政策支持。"},
    {"id": "q7", "type": "choice", "score": 2, "answer": "B", "prompt": "製作小書時，最適合的第一步是：", "options": {"A": "先畫裝飾圖", "B": "先決定主題和想探究的問題", "C": "先裝訂", "D": "先寫心得"}, "explain": "探究活動應先確定主題與問題，再蒐集資料。"},
    {"id": "q8", "type": "choice", "score": 2, "answer": "A", "prompt": "查詢近期社會事件，最適合參考：", "options": {"A": "新聞或報紙", "B": "十年前的日記", "C": "猜測", "D": "沒有來源的留言"}, "explain": "近期事件應參考新聞、報紙或可靠機關資料。"},
    {"id": "q9", "type": "choice", "score": 2, "answer": "D", "prompt": "民主社會中，人民參與公共事務的方式不包括：", "options": {"A": "選舉", "B": "理性討論", "C": "關心公共議題", "D": "用暴力強迫別人接受意見"}, "explain": "民主社會重視理性、合法參與。"},
    {"id": "q10", "type": "choice", "score": 2, "answer": "B", "prompt": "臺灣多元文化的正確態度是：", "options": {"A": "只接受自己的文化", "B": "尊重、理解並欣賞不同文化", "C": "覺得不同文化都不重要", "D": "要求所有人生活方式完全一樣"}, "explain": "多元文化重視尊重、理解、欣賞與共存共榮。"},
    {"id": "q11", "type": "match", "score": 8, "answer": {"11": "B", "12": "A", "13": "C", "14": "D"}, "prompt": "配對題：請將左邊內容配對到右邊最適合的說明。11北部地區、12東部地區、13實地踏查、14高科技產業。", "options": {"A": "自然景觀豐富，觀光資源多", "B": "政治、經濟、交通中心", "C": "可以取得第一手資料", "D": "需要研發、人才與資金"}, "explain": "北部是政經交通中心；東部觀光資源豐富；實地踏查能取得第一手資料；高科技需要研發、人才與資金。"},
    {"id": "q15", "type": "text", "score": 4, "keywords": ["農業", "工業", "高科技"], "prompt": "從產業表中可看出臺灣產業大致如何轉變？", "explain": "應寫出由農業為主，逐漸轉向工業，再發展高科技。"},
    {"id": "q16", "type": "text", "score": 4, "keywords": ["工廠", "就業", "都市"], "prompt": "工業發展後，為什麼都市人口可能增加？", "explain": "工廠增加帶來工作機會，人們可能移往都市就業。"},
    {"id": "q17", "type": "text", "score": 4, "keywords_any": ["人才", "研發", "資金", "科學園區", "政策", "投資"], "prompt": "現代高科技產業需要哪些條件？請寫出兩項。", "explain": "可答人才、研發、資金、科學園區、政府政策或企業投資。"},
    {"id": "q18", "type": "text", "score": 4, "keywords_any": ["汙染", "污染", "土地", "資源", "生態"], "prompt": "經濟發展可能帶來便利，也可能造成什麼問題？請寫出一項。", "explain": "可答空氣或水汙染、土地開發、資源消耗、生態破壞等。"},
    {"id": "q19", "type": "order", "score": 4, "answer": ["B", "C", "A", "D"], "prompt": "請將事件依時間先後排列：A解嚴後民主發展更進一步、B日本統治臺灣、C戰後中華民國政府治理臺灣、D臺灣進入高科技產業發展階段。", "explain": "先日治，再戰後治理，後來解嚴推動民主發展，再到現代高科技發展。"},
    {"id": "q20", "type": "text", "score": 4, "keywords_any": ["自由", "民主", "言論", "出版", "集會", "公共事務", "建設", "產業", "社會"], "prompt": "請從上題選一個事件，說明它對臺灣社會的影響。", "explain": "答案需說出事件與社會影響的因果關係。"},
    {"id": "q21", "type": "text", "score": 7, "keywords_any": ["山脈", "地形", "交通", "就醫", "就學", "工作", "觀光", "運輸"], "prompt": "情境題：東部交通較受限制和哪種自然因素有關？交通改善會造成哪些影響？爸爸的說法是否合理？", "explain": "重點是山脈與地形仍影響交通；改善後有助就醫、就學、工作、觀光與貨物運輸。"},
    {"id": "q22", "type": "text", "score": 7, "keywords_any": ["就業", "經濟", "汙染", "污染", "環評", "污水", "居民", "檢測", "綠地"], "prompt": "情境題：工業區可能帶來什麼好處與問題？你會提出什麼平衡發展與環境的建議？", "explain": "須同時看到就業與經濟好處，也提出環境保護建議。"},
    {"id": "q23", "type": "text", "score": 7, "keywords_any": ["訪問", "第一手", "來源", "可信", "圖片", "地圖", "標題", "版面"], "prompt": "情境題：臺灣茶文化小書中，訪問茶農是哪種資料蒐集方式？網路資料要注意什麼？如何讓讀者看懂？", "explain": "訪問屬第一手資料；網路資料要查來源可信度；呈現時可用標題、圖片、地圖與清楚版面。"},
    {"id": "q24", "type": "text", "score": 7, "keywords_any": ["第二", "公民", "行動", "環保", "自備", "餐具", "水壺", "分類"], "prompt": "情境題：討論減少一次性餐具時，哪位同學較符合公民參與精神？為什麼？請提出一個具體行動。", "explain": "第二位同學提出可行公共行動；具體行動可包含自備餐具、水壺或垃圾分類。"},
    {"id": "q25", "type": "text", "score": 4, "keywords_any": ["交通", "工商業", "政治", "經濟"], "prompt": "根據資料，北部的重要特色是什麼？", "explain": "北部交通便利、工商業發達，也常是政治經濟中心。"},
    {"id": "q26", "type": "text", "score": 4, "keywords_any": ["山脈", "地形"], "prompt": "東部發展受到哪一項自然因素影響？", "explain": "東部主要受山脈阻隔或地形因素影響。"},
    {"id": "q27", "type": "text", "score": 4, "keywords_any": ["海洋", "交通", "本島", "物資", "觀光", "產業"], "prompt": "如果要介紹離島生活，為什麼不能只看地圖，還要了解交通與產業？", "explain": "離島生活、物資運輸、觀光與產業都受海洋交通及本島連結影響。"},
    {"id": "q28", "type": "text", "score": 4, "keywords_any": ["升級", "科學園區", "人才", "研發", "半導體", "科技"], "prompt": "請用「原因 → 經過 → 影響」說明臺灣成為科技島的過程。", "explain": "可寫產業升級需求、政府設科學園區與培育人才、半導體等產業在世界具有重要地位。"},
    {"id": "q29", "type": "text", "score": 4, "keywords_any": ["米食", "音樂", "節慶", "原住民", "新住民", "尊重", "理解", "欣賞"], "prompt": "請舉一個臺灣多元文化的例子，並說明我們應該如何面對不同文化。", "explain": "可舉米食、音樂、節慶、原住民族或新住民文化；態度須包含尊重、理解、欣賞。"},
]


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS submissions (id TEXT PRIMARY KEY, student TEXT, class_name TEXT, seat TEXT, score INTEGER, answers TEXT, events TEXT, started_at TEXT, submitted_at TEXT, seconds_used INTEGER)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS progress (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, student TEXT, class_name TEXT, seat TEXT, event_type TEXT, payload TEXT, created_at TEXT)"
    )
    conn.commit()
    return conn


def now_text():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def grade_answer(q, value):
    if q["type"] == "choice":
        return q["score"] if value == q["answer"] else 0
    if q["type"] == "match":
        value = value or {}
        each = q["score"] / len(q["answer"])
        return round(sum(each for k, v in q["answer"].items() if value.get(k) == v))
    if q["type"] == "order":
        return q["score"] if value == q["answer"] else 0
    text = str(value or "")
    if not text.strip():
        return 0
    required = q.get("keywords")
    any_words = q.get("keywords_any")
    if required:
        hits = sum(1 for word in required if word in text)
        return round(q["score"] * hits / len(required))
    if any_words:
        hits = sum(1 for word in any_words if word in text)
        threshold = 1 if q["id"] in {"q18", "q25", "q26"} else (2 if q["score"] <= 4 else 3)
        return min(q["score"], round(q["score"] * hits / threshold))
    return 0


def grade_all(answers):
    total = 0
    detail = {}
    for q in QUESTIONS:
        score = grade_answer(q, answers.get(q["id"]))
        detail[q["id"]] = score
        total += score
    return total, detail


def response_page(title, body):
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{CSS}</style></head><body>{body}</body></html>""".encode("utf-8")


CSS = """
body{margin:0;background:#f6f4ee;color:#16202a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang TC','Noto Sans TC',sans-serif;line-height:1.55}
.wrap{width:min(1080px,calc(100% - 28px));margin:0 auto;padding:28px 0 48px}
.top{display:flex;justify-content:space-between;gap:16px;align-items:center;border-bottom:1px solid #d7d1c4;padding-bottom:16px;margin-bottom:18px}
h1{margin:0;font-size:28px;color:#12355b} h2{margin:22px 0 10px;font-size:20px;color:#0b5f59}.muted{color:#64707d}.card{background:white;border:1px solid #d9d4ca;border-radius:8px;padding:18px;margin:14px 0;box-shadow:0 8px 22px rgba(18,35,60,.06)}
label{display:block;font-weight:700;margin:10px 0 4px}input,textarea,select{font:inherit;width:100%;box-sizing:border-box;border:1px solid #c9c2b8;border-radius:6px;padding:9px;background:#fff}textarea{min-height:96px}
button,.btn{display:inline-flex;align-items:center;justify-content:center;gap:7px;border:1px solid #0f766e;background:#0f766e;color:white;border-radius:6px;padding:9px 13px;font-weight:800;text-decoration:none;cursor:pointer}button.secondary,.btn.secondary{background:white;color:#0f766e}.row{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.q{border-top:1px solid #ece7dd;padding-top:14px}.opts{display:grid;gap:8px}.opts label{font-weight:500;margin:0;display:flex;gap:8px}.opts input{width:auto}.score{font-size:36px;font-weight:900;color:#12355b}.pill{display:inline-block;border-radius:999px;background:#e0f2fe;color:#075985;padding:3px 9px;font-weight:800;font-size:13px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.qr img{width:210px;height:210px;border:1px solid #ddd;background:white;padding:8px}.table{width:100%;border-collapse:collapse;background:white}.table th,.table td{border:1px solid #d7d1c4;padding:8px;text-align:left;vertical-align:top}.table th{background:#eef4f3}.small{font-size:13px}.danger{color:#b91c1c}@media(max-width:720px){.top,.row,.grid{display:block}.top>*{margin-bottom:10px}}
"""


def home_html(base_url):
    quiz_url = f"{base_url}/quiz"
    teacher_note = "老師後台可查看分數、作答內容、作答歷程，並下載 CSV。"
    if ADMIN_PASSWORD:
        teacher_note = "老師後台已啟用密碼保護，可查看分數、作答內容、作答歷程，並下載 CSV。"
    return response_page(
        "翰林五下社會線上測驗",
        f"""<main class="wrap"><div class="top"><div><h1>翰林五下社會期末複習卷</h1><p class="muted">線上施測、紀錄作答歷程、老師後台檢閱資料庫</p></div><a class="btn secondary" href="/teacher">老師後台</a></div><section class="grid"><div class="card qr"><h2>學生掃描作答</h2><img src="/qr.svg?data={quote(quiz_url)}" alt="quiz qrcode"><p class="muted">網址：<br><strong>{html.escape(quiz_url)}</strong></p><a class="btn" href="/quiz">直接作答</a></div><div class="card"><h2>使用提醒</h2><p>若部署到雲端，學生可用任何網路掃描 QR code 作答。學生送出後，資料會存入伺服器資料庫。</p><p>{teacher_note}</p><p class="muted small">公開上網時請務必設定 <code>ADMIN_PASSWORD</code>，並使用平台提供的 HTTPS 網址。</p></div></section></main>""",
    )


def quiz_html():
    data = html.escape(json.dumps(QUESTIONS, ensure_ascii=False))
    return response_page(
        "學生作答",
        f"""<main class="wrap"><div class="top"><div><h1>國小五下社會期末複習卷</h1><p class="muted">翰林版主軸｜滿分100分</p></div><span class="pill" id="timer">00:00</span></div><section class="card" id="studentBox"><div class="row"><div><label>班級</label><input id="className" placeholder="例：五年1班"></div><div><label>座號</label><input id="seat" placeholder="例：12"></div><div><label>姓名</label><input id="student" placeholder="請輸入姓名"></div></div><p><button id="startBtn">開始作答</button></p></section><form id="quizForm" hidden></form><section class="card" id="result" hidden></section></main><script>const QUESTIONS=JSON.parse(document.getElementById('qdata')?.textContent||'{data}');</script><script type="application/json" id="qdata">{data}</script><script>{QUIZ_JS}</script>""",
    )


QUIZ_JS = r"""
let sessionId = crypto.randomUUID(), startedAt = null, seconds = 0, tick = null, events = [], answers = {};
const $ = (id)=>document.getElementById(id);
function log(type, payload={}) {
  const e = {type, payload, at:new Date().toISOString(), seconds};
  events.push(e);
  fetch('/api/progress',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...idInfo(), sessionId, eventType:type, payload:e})}).catch(()=>{});
}
function idInfo(){return {student:$('student').value.trim(), className:$('className').value.trim(), seat:$('seat').value.trim()};}
function render(){
  const form=$('quizForm'); form.innerHTML='';
  QUESTIONS.forEach((q,idx)=>{
    const div=document.createElement('section'); div.className='card q'; div.dataset.qid=q.id;
    div.innerHTML=`<h2>${idx+1}. ${q.prompt} <span class="pill">${q.score}分</span></h2>`;
    if(q.type==='choice'){
      const opts=document.createElement('div'); opts.className='opts';
      Object.entries(q.options).forEach(([k,v])=>{opts.insertAdjacentHTML('beforeend',`<label><input type="radio" name="${q.id}" value="${k}"> ${k}. ${v}</label>`);});
      div.appendChild(opts);
    } else if(q.type==='match') {
      ['11','12','13','14'].forEach(no=>{div.insertAdjacentHTML('beforeend',`<label>${no} 配對答案</label><select name="${q.id}_${no}"><option value="">請選擇</option><option>A</option><option>B</option><option>C</option><option>D</option></select>`);});
      div.insertAdjacentHTML('beforeend',`<p class="muted small">選項：A ${q.options.A}｜B ${q.options.B}｜C ${q.options.C}｜D ${q.options.D}</p>`);
    } else if(q.type==='order') {
      div.insertAdjacentHTML('beforeend',`<div class="row">${[1,2,3,4].map(n=>`<div><label>第${n}個</label><select name="${q.id}_${n}"><option value="">請選擇</option><option>A</option><option>B</option><option>C</option><option>D</option></select></div>`).join('')}</div>`);
    } else {
      div.insertAdjacentHTML('beforeend',`<textarea name="${q.id}" placeholder="請輸入你的答案"></textarea>`);
    }
    form.appendChild(div);
  });
  form.insertAdjacentHTML('beforeend','<section class="card"><button type="submit">交卷並查看分數</button> <button type="button" class="secondary" id="saveBtn">儲存目前作答歷程</button></section>');
  form.addEventListener('input', collectAndLog);
  $('saveBtn').addEventListener('click',()=>{collect(); log('manual-save',{answers}); alert('已記錄目前作答歷程');});
}
function collect(){
  answers={};
  QUESTIONS.forEach(q=>{
    if(q.type==='choice') answers[q.id]=document.querySelector(`[name="${q.id}"]:checked`)?.value||'';
    else if(q.type==='match') {answers[q.id]={}; ['11','12','13','14'].forEach(no=>answers[q.id][no]=document.querySelector(`[name="${q.id}_${no}"]`)?.value||'');}
    else if(q.type==='order') answers[q.id]=[1,2,3,4].map(n=>document.querySelector(`[name="${q.id}_${n}"]`)?.value||'');
    else answers[q.id]=document.querySelector(`[name="${q.id}"]`)?.value||'';
  });
}
let logTimer=null;
function collectAndLog(){collect(); clearTimeout(logTimer); logTimer=setTimeout(()=>log('answer-change',{answers}),600);}
$('startBtn').addEventListener('click',()=>{
  if(!$('student').value.trim()){alert('請先輸入姓名');return;}
  startedAt=new Date(); $('studentBox').hidden=true; $('quizForm').hidden=false; render(); log('start');
  tick=setInterval(()=>{seconds++; $('timer').textContent=String(Math.floor(seconds/60)).padStart(2,'0')+':'+String(seconds%60).padStart(2,'0');},1000);
});
$('quizForm').addEventListener('submit',async e=>{
  e.preventDefault(); collect(); log('submit-click',{answers}); clearInterval(tick);
  const res=await fetch('/api/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...idInfo(), sessionId, answers, events, startedAt:startedAt?.toISOString(), secondsUsed:seconds})});
  const data=await res.json(); $('quizForm').hidden=true; const r=$('result'); r.hidden=false;
  r.innerHTML=`<h2>作答完成</h2><div class="score">${data.score} / 100</div><p class="muted">老師後台已收到作答資料。</p><h2>解析</h2>${QUESTIONS.map(q=>`<p><strong>${q.id}</strong>：${q.explain}</p>`).join('')}`;
});
window.addEventListener('visibilitychange',()=>log(document.hidden?'page-hidden':'page-visible'));
"""


def teacher_html():
    return response_page(
        "老師後台",
        f"""<main class="wrap"><div class="top"><div><h1>老師檢閱資料庫</h1><p class="muted">查看分數、答案與作答歷程</p></div><div><a class="btn secondary" href="/">QR 首頁</a> <a class="btn" href="/api/export.csv">下載 CSV</a></div></div><section class="card"><table class="table" id="tbl"><thead><tr><th>時間</th><th>班級</th><th>座號</th><th>姓名</th><th>分數</th><th>秒數</th><th>詳細</th></tr></thead><tbody></tbody></table></section><section class="card" id="detail"><h2>詳細資料</h2><p class="muted">點選任一筆「詳細」檢閱。</p></section></main><script>{TEACHER_JS}</script>""",
    )


TEACHER_JS = r"""
async function load(){
  const rows=await (await fetch('/api/submissions')).json();
  const tb=document.querySelector('#tbl tbody'); tb.innerHTML='';
  rows.forEach(r=>{const tr=document.createElement('tr'); tr.innerHTML=`<td>${r.submitted_at}</td><td>${r.class_name||''}</td><td>${r.seat||''}</td><td>${r.student||''}</td><td><strong>${r.score}</strong></td><td>${r.seconds_used}</td><td><button data-id="${r.id}">詳細</button></td>`; tb.appendChild(tr);});
  tb.addEventListener('click',async e=>{if(e.target.dataset.id){const d=await (await fetch('/api/submissions?id='+e.target.dataset.id)).json(); show(d[0]);}});
}
function show(r){
  const answers=JSON.parse(r.answers||'{}'), events=JSON.parse(r.events||'[]');
  document.getElementById('detail').innerHTML=`<h2>${r.student}｜${r.score}分</h2><p class="muted">${r.class_name||''} ${r.seat||''}號｜${r.submitted_at}</p><h2>作答內容</h2><pre>${escapeHtml(JSON.stringify(answers,null,2))}</pre><h2>作答歷程</h2><pre>${escapeHtml(JSON.stringify(events,null,2))}</pre>`;
}
function escapeHtml(s){return s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
load();
"""


def qr_svg(data):
    matrix = make_qr_matrix(data[:70])
    scale = 8
    quiet = 4
    size = (len(matrix) + quiet * 2) * scale
    rects = []
    for y, row in enumerate(matrix):
        for x, dark in enumerate(row):
            if dark:
                rects.append(f'<rect x="{(x+quiet)*scale}" y="{(y+quiet)*scale}" width="{scale}" height="{scale}"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}"><rect width="100%" height="100%" fill="#fff"/><g fill="#000">{"".join(rects)}</g></svg>'.encode()


def make_qr_matrix(text):
    version, ecc_len, data_len = 4, 20, 80
    size = 17 + 4 * version
    modules = [[None] * size for _ in range(size)]

    def set_mod(x, y, dark):
        if 0 <= x < size and 0 <= y < size:
            modules[y][x] = dark

    def finder(x, y):
        for dy in range(-1, 8):
            for dx in range(-1, 8):
                xx, yy = x + dx, y + dy
                if 0 <= xx < size and 0 <= yy < size:
                    dark = (0 <= dx <= 6 and 0 <= dy <= 6 and (dx in (0, 6) or dy in (0, 6) or (2 <= dx <= 4 and 2 <= dy <= 4)))
                    set_mod(xx, yy, dark)

    finder(0, 0)
    finder(size - 7, 0)
    finder(0, size - 7)
    for i in range(8, size - 8):
        set_mod(i, 6, i % 2 == 0)
        set_mod(6, i, i % 2 == 0)
    for ax in (6, 26):
        for ay in (6, 26):
            if modules[ay][ax] is not None:
                continue
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    set_mod(ax + dx, ay + dy, max(abs(dx), abs(dy)) != 1)
    set_mod(8, size - 8, True)

    bits = [0, 1, 0, 0]
    data = text.encode("utf-8")
    bits += [(len(data) >> i) & 1 for i in range(7, -1, -1)]
    for b in data:
        bits += [(b >> i) & 1 for i in range(7, -1, -1)]
    bits += [0] * min(4, data_len * 8 - len(bits))
    while len(bits) % 8:
        bits.append(0)
    codewords = [sum(bits[i + j] << (7 - j) for j in range(8)) for i in range(0, len(bits), 8)]
    pads = [0xEC, 0x11]
    k = 0
    while len(codewords) < data_len:
        codewords.append(pads[k % 2])
        k += 1
    codewords += rs_ecc(codewords, ecc_len)
    all_bits = [(b >> i) & 1 for b in codewords for i in range(7, -1, -1)]

    i = 0
    upward = True
    x = size - 1
    while x > 0:
        if x == 6:
            x -= 1
        rows = range(size - 1, -1, -1) if upward else range(size)
        for y in rows:
            for dx in (0, 1):
                xx = x - dx
                if modules[y][xx] is None:
                    bit = all_bits[i] if i < len(all_bits) else 0
                    mask = (xx + y) % 2 == 0
                    modules[y][xx] = bool(bit) ^ mask
                    i += 1
        upward = not upward
        x -= 2
    draw_format(modules, 1, 0)
    return [[bool(v) for v in row] for row in modules]


def rs_ecc(data, degree):
    gen = [1]
    for i in range(degree):
        gen = poly_mul(gen, [1, gf_pow(2, i)])
    res = [0] * degree
    for b in data:
        factor = b ^ res.pop(0)
        res.append(0)
        for j in range(degree):
            res[j] ^= gf_mul(gen[j + 1], factor)
    return res


def poly_mul(p, q):
    out = [0] * (len(p) + len(q) - 1)
    for i, a in enumerate(p):
        for j, b in enumerate(q):
            out[i + j] ^= gf_mul(a, b)
    return out


def gf_mul(x, y):
    z = 0
    for i in range(8):
        if (y >> i) & 1:
            z ^= x << i
    for i in range(14, 7, -1):
        if (z >> i) & 1:
            z ^= 0x11D << (i - 8)
    return z


def gf_pow(x, n):
    y = 1
    for _ in range(n):
        y = gf_mul(y, x)
    return y


def draw_format(m, ecc, mask):
    size = len(m)
    data = (ecc << 3) | mask
    rem = data
    for _ in range(10):
        rem = (rem << 1) ^ ((rem >> 9) * 0x537)
    bits = ((data << 10) | rem) ^ 0x5412
    coords1 = [(8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8), (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)]
    coords2 = [(size - 1, 8), (size - 2, 8), (size - 3, 8), (size - 4, 8), (size - 5, 8), (size - 6, 8), (size - 7, 8), (8, size - 8), (8, size - 7), (8, size - 6), (8, size - 5), (8, size - 4), (8, size - 3), (8, size - 2), (8, size - 1)]
    for i, (x, y) in enumerate(coords1):
        m[y][x] = bool((bits >> i) & 1)
    for i, (x, y) in enumerate(coords2):
        m[y][x] = bool((bits >> i) & 1)


class Handler(BaseHTTPRequestHandler):
    def send_bytes(self, body, content_type="text/html; charset=utf-8"):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def base_url(self):
        if PUBLIC_BASE_URL:
            return PUBLIC_BASE_URL
        scheme = self.headers.get("X-Forwarded-Proto", "http")
        host = self.headers.get("Host", f"{local_ip()}:{PORT}")
        return f"{scheme}://{host}".rstrip("/")

    def teacher_authorized(self):
        if not ADMIN_PASSWORD:
            return True
        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            return False
        try:
            decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
        except Exception:
            return False
        _, _, password = decoded.partition(":")
        return hmac.compare_digest(password, ADMIN_PASSWORD)

    def require_teacher(self):
        if self.teacher_authorized():
            return True
        body = response_page(
            "需要老師密碼",
            """<main class="wrap"><section class="card"><h1>需要老師密碼</h1><p class="muted">請輸入部署時設定的老師後台密碼。</p></section></main>""",
        )
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Teacher Dashboard"')
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return False

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_bytes(home_html(self.base_url()))
        elif parsed.path == "/quiz":
            self.send_bytes(quiz_html())
        elif parsed.path == "/teacher":
            if not self.require_teacher():
                return
            self.send_bytes(teacher_html())
        elif parsed.path == "/qr.svg":
            data = unquote(parse_qs(parsed.query).get("data", [""])[0])
            self.send_bytes(qr_svg(data), "image/svg+xml")
        elif parsed.path == "/healthz":
            self.send_bytes(b'{"ok":true}', "application/json")
        elif parsed.path == "/api/submissions":
            if not self.require_teacher():
                return
            q = parse_qs(parsed.query)
            conn = db()
            if "id" in q:
                rows = conn.execute("SELECT * FROM submissions WHERE id=?", (q["id"][0],)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM submissions ORDER BY submitted_at DESC").fetchall()
            self.send_bytes(json.dumps([dict(r) for r in rows], ensure_ascii=False).encode(), "application/json; charset=utf-8")
        elif parsed.path == "/api/export.csv":
            if not self.require_teacher():
                return
            conn = db()
            rows = conn.execute("SELECT * FROM submissions ORDER BY submitted_at DESC").fetchall()
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerow(["submitted_at", "class_name", "seat", "student", "score", "seconds_used", "answers", "events"])
            for r in rows:
                writer.writerow([r["submitted_at"], r["class_name"], r["seat"], r["student"], r["score"], r["seconds_used"], r["answers"], r["events"]])
            self.send_bytes(out.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8")
        else:
            self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(length) or b"{}")
        conn = db()
        if self.path == "/api/progress":
            conn.execute(
                "INSERT INTO progress(session_id,student,class_name,seat,event_type,payload,created_at) VALUES(?,?,?,?,?,?,?)",
                (data.get("sessionId"), data.get("student"), data.get("className"), data.get("seat"), data.get("eventType"), json.dumps(data.get("payload"), ensure_ascii=False), now_text()),
            )
            conn.commit()
            self.send_bytes(b'{"ok":true}', "application/json")
        elif self.path == "/api/submit":
            answers = data.get("answers", {})
            score, detail = grade_all(answers)
            sid = str(uuid.uuid4())
            events = data.get("events", [])
            events.append({"type": "server-graded", "score": score, "detail": detail, "at": now_text()})
            conn.execute(
                "INSERT INTO submissions(id,student,class_name,seat,score,answers,events,started_at,submitted_at,seconds_used) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (sid, data.get("student"), data.get("className"), data.get("seat"), score, json.dumps(answers, ensure_ascii=False), json.dumps(events, ensure_ascii=False), data.get("startedAt"), now_text(), data.get("secondsUsed", 0)),
            )
            conn.commit()
            self.send_bytes(json.dumps({"ok": True, "score": score}, ensure_ascii=False).encode(), "application/json; charset=utf-8")
        else:
            self.send_error(404)


if __name__ == "__main__":
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db().close()
    host = local_ip()
    computer_name = socket.gethostname()
    print(f"學生 QR 首頁：http://{host}:{PORT}/")
    print(f"本機名稱網址：http://{computer_name}.local:{PORT}/")
    if PUBLIC_BASE_URL:
        print(f"公開網址：{PUBLIC_BASE_URL}/")
    print(f"老師後台：http://{host}:{PORT}/teacher")
    if not ADMIN_PASSWORD:
        print("提醒：目前未設定 ADMIN_PASSWORD，公開部署前請務必設定老師後台密碼。")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
