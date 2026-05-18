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
    {"id": "q1", "type": "choice", "score": 2, "answer": "B", "prompt": "「戒嚴」時期，人民生活最可能受到哪一項影響？", "options": {"A": "人民完全不用守法", "B": "言論、出版、集會等自由受到較多限制", "C": "所有公共事務都由學生決定", "D": "每個人都可以任意更改法律"}, "explain": "戒嚴時期政府基於特殊情勢採取較嚴格管制，人民的言論、出版、集會、結社等自由較受限制。"},
    {"id": "q2", "type": "choice", "score": 2, "answer": "C", "prompt": "下列哪一項最能說明「解嚴」對臺灣社會的意義？", "options": {"A": "人民從此不需要遵守法律", "B": "政府不再需要接受人民監督", "C": "社會逐漸走向更自由、開放的民主發展", "D": "選舉和公共討論都被取消"}, "explain": "解嚴後，人民的自由與政治參與空間擴大，是臺灣民主化的重要轉折。"},
    {"id": "q3", "type": "choice", "score": 2, "answer": "A", "prompt": "民主社會中，政府與人民的關係，下列敘述何者較正確？", "options": {"A": "政府應為人民服務，人民也能監督政府", "B": "政府做任何事都不必說明理由", "C": "人民不能表達不同意見", "D": "少數人可以永遠決定所有公共政策"}, "explain": "民主社會重視人民主權、政府責任與公共監督。"},
    {"id": "q4", "type": "choice", "score": 2, "answer": "D", "prompt": "下列哪一項不是民主社會中合宜的公民參與方式？", "options": {"A": "投票選出民意代表", "B": "參加公共議題討論", "C": "向政府提出陳情或建議", "D": "用威脅或暴力強迫別人支持自己"}, "explain": "民主參與應理性、合法，不能用暴力壓迫他人。"},
    {"id": "q5", "type": "choice", "score": 2, "answer": "A", "prompt": "選舉在民主政治中的主要功能是什麼？", "options": {"A": "讓人民選出代表或公職人員", "B": "讓所有人都不用負責任", "C": "讓少數人永久掌權", "D": "讓人民不能討論公共事務"}, "explain": "選舉是人民參與政治與監督政府的重要方式。"},
    {"id": "q6", "type": "choice", "score": 2, "answer": "B", "prompt": "憲法和法律在民主社會中的重要性，最接近下列哪一項？", "options": {"A": "只用來限制學生，和政府無關", "B": "規範政府權力，也保障人民權利與義務", "C": "讓人民不能表達意見", "D": "讓政府完全不受限制"}, "explain": "憲法與法律能規範政府組織與權力，也保障人民權利並規定義務。"},
    {"id": "q7", "type": "choice", "score": 2, "answer": "C", "prompt": "人民爭取權利或推動公共改革時，較符合民主精神的做法是：", "options": {"A": "散播未查證謠言", "B": "阻止所有不同意見發言", "C": "透過合法集會、討論、陳情或投票表達意見", "D": "只要自己喜歡，就可以破壞公共設施"}, "explain": "民主社會可以表達意見，但要尊重法律、事實與他人權利。"},
    {"id": "q8", "type": "choice", "score": 2, "answer": "D", "prompt": "如果班上討論是否更換午餐菜單，最符合民主程序的是：", "options": {"A": "由聲音最大的人直接決定", "B": "只聽一位同學的意見", "C": "不讓反對者說話", "D": "蒐集意見、充分討論，再用公平方式做決定"}, "explain": "民主程序重視討論、尊重不同意見與公平決定。"},
    {"id": "q9", "type": "choice", "score": 2, "answer": "C", "prompt": "下列哪一項較能展現「自由也要負責任」？", "options": {"A": "在網路上隨便罵人也沒關係", "B": "只要是自己的想法，就一定不用查證", "C": "發表意見前查證資料，並尊重他人權利", "D": "可以用假消息影響選舉"}, "explain": "自由不是任意傷害他人；公民表達意見時應重視事實、尊重和責任。"},
    {"id": "q10", "type": "choice", "score": 2, "answer": "A", "prompt": "臺灣走向民主化的過程，最適合用哪一組詞語說明？", "options": {"A": "人民爭取、政府改革、自由擴大、制度進步", "B": "完全沒有衝突，也不需要討論", "C": "只靠一個人命令就完成", "D": "取消選舉、禁止發言、拒絕監督"}, "explain": "民主化是人民參與、社會運動、政府改革與制度調整逐漸累積的結果。"},
    {"id": "q11", "type": "match", "score": 8, "answer": {"11": "D", "12": "B", "13": "C", "14": "A"}, "prompt": "配對題：請將左邊內容配對到右邊最適合的說明。11戒嚴、12解嚴、13選舉、14憲法。", "options": {"A": "規範政府組織與權力，也保障人民權利義務", "B": "解除戒嚴狀態，社會逐漸更自由開放", "C": "人民選出代表或公職人員的重要方式", "D": "特殊時期政府對社會與人民自由採取較多限制"}, "explain": "戒嚴代表較多管制；解嚴代表限制鬆開；選舉是人民參與政治；憲法規範政府並保障人民。"},
    {"id": "q15", "type": "text", "score": 4, "keywords": ["言論", "出版", "集會", "結社"], "prompt": "請寫出戒嚴時期人民生活可能受到限制的兩種自由。", "explain": "可答言論、出版、集會、結社、組黨、新聞報導等自由受到較多限制。"},
    {"id": "q16", "type": "text", "score": 4, "keywords_any": ["人民", "爭取", "政府", "改革", "社會運動", "解嚴", "選舉", "自由"], "prompt": "臺灣為什麼能逐漸走向民主社會？請寫出兩個原因或力量。", "explain": "可從人民爭取權利、社會運動、政府改革、解嚴、開放選舉與自由擴大等面向作答。"},
    {"id": "q17", "type": "text", "score": 4, "keywords_any": ["投票", "選舉", "討論", "陳情", "公聽會", "連署", "民間團體", "志工"], "prompt": "民主社會中，人民可以如何參與公共事務？請寫出兩種方式。", "explain": "可答投票、選舉、理性討論、陳情、連署、參加公聽會、加入民間團體、擔任志工等。"},
    {"id": "q18", "type": "text", "score": 4, "keywords_any": ["尊重", "查證", "法律", "負責", "權利", "義務", "理性"], "prompt": "為什麼說民主社會中的自由也需要負責任？請用一句話說明。", "explain": "自由應建立在尊重他人、遵守法律、查證事實與承擔責任的基礎上。"},
    {"id": "q19", "type": "order", "score": 4, "answer": ["B", "C", "A", "D"], "prompt": "請將下列事件依時間先後排列：A解嚴後人民自由與政治參與逐漸擴大、B政府在臺灣實施戒嚴、C政府宣布解嚴、D臺灣民主制度持續發展，人民透過選舉與公共參與監督政府。", "explain": "先有戒嚴時期，後來宣布解嚴，再逐步擴大自由與政治參與，民主制度持續發展。"},
    {"id": "q20", "type": "text", "score": 4, "keywords_any": ["自由", "參與", "監督", "選舉", "民主", "權利", "政府", "社會"], "prompt": "請從上題選一個事件，說明它對臺灣社會的影響。", "explain": "答案需說出事件與影響，例如解嚴讓人民自由與政治參與空間擴大。"},
    {"id": "q21", "type": "text", "score": 7, "keywords_any": ["候選人", "政見", "投票", "公平", "討論", "尊重", "多數", "少數"], "prompt": "情境題：班上要選自治市長，有同學說：「只要我朋友多，就不用聽其他候選人的政見。」如果你是選務小組，會如何設計比較符合民主精神的選舉？", "explain": "可提到候選人發表政見、同學提問討論、公平投票、尊重多數決，也要尊重少數意見。"},
    {"id": "q22", "type": "text", "score": 7, "keywords_any": ["查證", "事實", "尊重", "法律", "責任", "謠言", "理性", "道歉"], "prompt": "情境題：小明在網路上看到未查證消息，就轉貼批評某位候選人。請說明這樣可能造成什麼問題，並提出一個負責任的做法。", "explain": "可答可能散播謠言、傷害他人或影響公共判斷；負責任做法是查證來源、停止轉傳、理性討論或更正道歉。"},
    {"id": "q23", "type": "text", "score": 7, "keywords_any": ["居民", "公聽會", "陳情", "投票", "討論", "資料", "政府", "公共利益"], "prompt": "情境題：社區要改建公園，有居民支持也有人擔心噪音與安全。請提出一個民主社會處理公共爭議的流程。", "explain": "可提到蒐集資料、召開公聽會、讓居民表達意見、政府說明方案、修改計畫或用公平程序決定。"},
    {"id": "q24", "type": "text", "score": 7, "keywords_any": ["投票", "監督", "政府", "代表", "公共", "權利", "責任", "參與"], "prompt": "情境題：有人說「政治和我無關，反正一票也沒差。」請用本單元觀念回應他。", "explain": "可說明投票是人民參與公共事務、選出代表、監督政府的重要權利與責任，每個人的選擇都會影響公共生活。"},
    {"id": "q25", "type": "text", "score": 4, "keywords_any": ["言論", "出版", "集會", "結社", "自由", "限制"], "prompt": "閱讀題：戒嚴時期，政府對社會秩序採取較嚴格管制，人民表達意見與組織活動較不自由。根據資料，戒嚴時期人民哪些自由可能較受限制？", "explain": "可答言論、出版、集會、結社或組織活動等自由較受限制。"},
    {"id": "q26", "type": "text", "score": 4, "keywords_any": ["解嚴", "自由", "開放", "民主", "參與", "權利"], "prompt": "閱讀題：解嚴後，社會逐漸開放，人民能更積極參與公共事務。根據資料，解嚴為什麼是民主化的重要轉折？", "explain": "解嚴使自由與政治參與空間逐漸擴大，讓社會更開放，是民主化的重要轉折。"},
    {"id": "q27", "type": "text", "score": 4, "keywords_any": ["服務", "人民", "監督", "選舉", "法律", "權利", "義務"], "prompt": "請說明民主社會中「政府」和「人民」應該是什麼關係。", "explain": "政府應依法為人民服務，人民透過選舉、討論與監督參與公共事務，也要履行公民義務。"},
    {"id": "q28", "type": "text", "score": 4, "keywords_any": ["戒嚴", "解嚴", "人民", "爭取", "政府", "改革", "選舉", "民主"], "prompt": "請用「原因 → 經過 → 影響」簡述臺灣走向民主的過程。", "explain": "可寫戒嚴時期自由受限，人民爭取權利與政府改革，解嚴後自由與選舉參與擴大，民主制度逐步發展。"},
    {"id": "q29", "type": "text", "score": 4, "keywords_any": ["尊重", "理性", "查證", "參與", "投票", "法律", "責任", "公共"], "prompt": "請舉出一個負責任公民的行動，並說明它如何幫助民主社會。", "explain": "可答投票、理性討論、查證資料、尊重不同意見、遵守法律、參與公共服務等，並說明能促進公共決策與社會信任。"},
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
        "翰林五下社會第三單元線上測驗",
        f"""<main class="wrap"><div class="top"><div><h1>翰林五下社會第三單元</h1><p class="muted">走向民主的中華民國｜線上施測、紀錄作答歷程、老師後台檢閱資料庫</p></div><a class="btn secondary" href="/teacher">老師後台</a></div><section class="grid"><div class="card qr"><h2>學生掃描作答</h2><img src="/qr.svg?data={quote(quiz_url)}" alt="quiz qrcode"><p class="muted">網址：<br><strong>{html.escape(quiz_url)}</strong></p><a class="btn" href="/quiz">直接作答</a></div><div class="card"><h2>使用提醒</h2><p>若部署到雲端，學生可用任何網路掃描 QR code 作答。學生送出後，資料會存入伺服器資料庫。</p><p>{teacher_note}</p><p class="muted small">公開上網時請務必設定 <code>ADMIN_PASSWORD</code>，並使用平台提供的 HTTPS 網址。</p></div></section></main>""",
    )


def quiz_html():
    data = json.dumps(QUESTIONS, ensure_ascii=False).replace("</", "<\\/")
    return response_page(
        "學生作答",
        f"""<main class="wrap"><div class="top"><div><h1>五下翰林社會第三單元測驗</h1><p class="muted">走向民主的中華民國｜滿分100分</p></div><span class="pill" id="timer">00:00</span></div><section class="card" id="studentBox"><div class="row"><div><label>班級</label><input id="className" placeholder="例：五年1班"></div><div><label>座號</label><input id="seat" placeholder="例：12"></div><div><label>姓名</label><input id="student" placeholder="請輸入姓名"></div></div><p><button id="startBtn">開始作答</button></p></section><form id="quizForm" hidden></form><section class="card" id="result" hidden></section></main><script type="application/json" id="qdata">{data}</script><script>const QUESTIONS=JSON.parse(document.getElementById('qdata').textContent);</script><script>{QUIZ_JS}</script>""",
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
