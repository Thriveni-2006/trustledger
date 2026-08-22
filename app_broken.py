import os
import json
import re
import base64
from datetime import datetime, date, timedelta
from io import BytesIO

import streamlit as st
from dotenv import load_dotenv

# ------------------------------------------------------------
# OPTIONAL SARVAM AI
# The app works even if Sarvam is unavailable.
# ------------------------------------------------------------

try:
    from sarvamai import SarvamAI
except Exception:
    SarvamAI = None

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "").strip()
DATA_FILE = "trustledger_data.json"

# ============================================================
# PAGE
# ============================================================

st.set_page_config(
page_title="TrustLedger",
page_icon="💎",
layout="wide",
)

# ============================================================
# STYLE
# ============================================================

st.markdown(
"""

<style> .stApp { background: radial-gradient(circle at 10% 0%, rgba(91,78,220,.22), transparent 30%), radial-gradient(circle at 90% 10%, rgba(0,170,170,.10), transparent 25%), #070a12; color: #f5f7ff; } .block-container { max-width: 1450px; padding-top: 1.5rem; padding-bottom: 3rem; } .hero { background: linear-gradient(135deg, #211e50, #0b0f1c); border: 1px solid rgba(255,255,255,.10); border-radius: 28px; padding: 38px; margin-bottom: 25px; } .brand { color: #a7a0ff; font-size: 13px; font-weight: 800; letter-spacing: 4px; } .hero-title { font-size: clamp(42px, 6vw, 72px); font-weight: 900; line-height: 1; letter-spacing: -4px; margin-top: 10px; } .hero-subtitle { font-size: 24px; font-weight: 700; color: #cbd0ff; margin-top: 18px; } .hero-description { color: #aab3c7; max-width: 850px; line-height: 1.7; margin-top: 12px; } .pill { display: inline-block; padding: 7px 12px; margin: 8px 6px 0 0; border-radius: 999px; background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.10); font-size: 11px; font-weight: 800; } .green { color: #5dffac; } .yellow { color: #ffd477; } .card { background: rgba(16,21,36,.90); border: 1px solid rgba(255,255,255,.08); border-radius: 20px; padding: 20px; } .metric { background: rgba(16,21,36,.90); border: 1px solid rgba(255,255,255,.08); border-radius: 17px; padding: 18px; } .metric-label { color: #7f8ba4; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; } .metric-value { font-size: 28px; font-weight: 900; margin-top: 5px; } .section-title { font-size: 25px; font-weight: 900; margin-top: 30px; margin-bottom: 5px; } .section-subtitle { color: #8591a9; font-size: 13px; margin-bottom: 15px; } .story { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 18px; background: rgba(255,255,255,.035); border: 1px solid rgba(255,255,255,.07); border-radius: 18px; } .story-step { background: rgba(100,90,255,.12); border: 1px solid rgba(110,100,255,.20); padding: 10px 13px; border-radius: 12px; font-size: 12px; font-weight: 800; } .arrow { color: #65718d; font-weight: 900; } .trust-card { text-align: center; padding: 30px; border-radius: 23px; background: radial-gradient(circle at 50% 0%, rgba(105,95,255,.22), transparent 60%), rgba(15,20,36,.95); border: 1px solid rgba(120,110,255,.20); } .trust-number { font-size: 64px; font-weight: 900; letter-spacing: -4px; } .trust-new { font-size: 43px; font-weight: 900; } .rural { background: rgba(50,140,230,.08); border: 1px solid rgba(70,150,240,.20); border-radius: 18px; padding: 18px; color: #b7d5ff; } .demo { background: rgba(255,190,50,.08); border: 1px solid rgba(255,190,50,.22); border-radius: 15px; padding: 14px 17px; color: #ffd77e; } .receipt { background: #101522; border: 1px dashed rgba(190,200,220,.35); border-radius: 20px; padding: 25px; } .copilot { background: linear-gradient(135deg, #15182c, #211735); border: 1px solid rgba(130,110,255,.20); border-radius: 20px; padding: 20px; } .muted { color: #7f8ca4; font-size: 12px; } div.stButton > button { border-radius: 12px; font-weight: 800; min-height: 44px; } [data-testid="stSidebar"] { background: #090c17; } </style>

""",
unsafe_allow_html=True,
)

# ============================================================
# DATA FUNCTIONS
# ============================================================

def empty_data():
return {
"transactions": [],
"last_receipt": None,
"demo_mode": False,
}

def load_data():
if not os.path.exists(DATA_FILE):
return empty_data()

try:
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        return empty_data()

    data.setdefault("transactions", [])
    data.setdefault("last_receipt", None)
    data.setdefault("demo_mode", False)

    return data
except Exception:
    return empty_data()

def save_data():
try:
with open(DATA_FILE, "w", encoding="utf-8") as file:
json.dump(
st.session_state.data,
file,
ensure_ascii=False,
indent=2,
)
return True
except Exception:
return False

if "data" not in st.session_state:
st.session_state.data = load_data()

if "pending_voice" not in st.session_state:
st.session_state.pending_voice = None

if "voice_text" not in st.session_state:
st.session_state.voice_text = ""

if "voice_error" not in st.session_state:
st.session_state.voice_error = ""

if "reminder_text" not in st.session_state:
st.session_state.reminder_text = ""

if "copilot_answer" not in st.session_state:
st.session_state.copilot_answer = ""

if "receipt_audio" not in st.session_state:
st.session_state.receipt_audio = None

# ============================================================
# GENERAL HELPERS
# ============================================================

def now_text():
return datetime.now().strftime("%d %b %Y, %I:%M %p")

def today_date():
return date.today()

def add_transaction(
customer,
amount,
transaction_type,
due_date="",
note="",
source="Manual",
):
transaction = {
"id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
"customer": customer.strip(),
"amount": float(amount),
"type": transaction_type,
"date": now_text(),
"date_iso": today_date().isoformat(),
"due_date": due_date,
"note": note,
"source": source,
"confirmed": True,
}

st.session_state.data["transactions"].append(transaction)
st.session_state.data["last_receipt"] = transaction
st.session_state.data["demo_mode"] = False

save_data()

return transaction

def summaries():
result = {}

for transaction in st.session_state.data["transactions"]:
    name = transaction.get("customer", "Unknown")
    amount = float(transaction.get("amount", 0))
    kind = transaction.get("type", "owes")

    if name not in result:
        result[name] = {
            "credit": 0.0,
            "paid": 0.0,
            "balance": 0.0,
            "transactions": 0,
            "due_date": "",
        }

    result[name]["transactions"] += 1

    if kind == "owes":
        result[name]["credit"] += amount

        if transaction.get("due_date"):
            result[name]["due_date"] = transaction["due_date"]
    else:
        result[name]["paid"] += amount

for name in result:
    result[name]["balance"] = max(
        0,
        result[name]["credit"] - result[name]["paid"],
    )

return result

def credit_total():
return sum(
float(t.get("amount", 0))
for t in st.session_state.data["transactions"]
if t.get("type") == "owes"
)

def paid_total():
return sum(
float(t.get("amount", 0))
for t in st.session_state.data["transactions"]
if t.get("type") == "paid"
)

def pending_total():
return sum(
item["balance"]
for item in summaries().values()
)

def repayment_rate():
credit = credit_total()

if credit <= 0:
    return 0

return min(
    100,
    round((paid_total() / credit) * 100),
)

def trust_score():
transactions = st.session_state.data["transactions"]

if not transactions:
    return None

credit = credit_total()

if credit <= 0:
    return 55

paid = paid_total()

repayment = min(
    1,
    paid / credit,
)

people = summaries()

settled = sum(
    1
    for item in people.values()
    if item["credit"] > 0 and item["balance"] <= 0
)

pending = sum(
    1
    for item in people.values()
    if item["balance"] > 0
)

overdue = 0

for item in people.values():
    due = item.get("due_date", "")

    if due and item["balance"] > 0:
        try:
            due_date = datetime.strptime(
                due,
                "%Y-%m-%d",
            ).date()

            if due_date < today_date():
                overdue += 1
        except Exception:
            pass

score = 35 + repayment * 55
score += min(8, settled * 2)
score -= min(12, pending * 1.5)
score -= min(20, overdue * 5)

return max(
    0,
    min(100, round(score)),
)

def trust_label(score):
if score is None:
return "New"

if score >= 75:
    return "High Trust"

if score >= 50:
    return "Medium Trust"

return "Low Trust"

def status_for(balance, due_date):
if balance <= 0:
return "🟢 Settled"

if due_date:
    try:
        due = datetime.strptime(
            due_date,
            "%Y-%m-%d",
        ).date()

        if due < today_date():
            return "🔴 Needs follow-up"
    except Exception:
        pass

if balance <= 500:
    return "🟡 Small balance"

return "🔴 Needs follow-up"

def priorities():
result = []

for name, item in summaries().items():
    if item["balance"] <= 0:
        continue

    status = status_for(
        item["balance"],
        item["due_date"],
    )

    priority = 3 if "Needs" in status else 2

    result.append(
        {
            "name": name,
            "balance": item["balance"],
            "due": item["due_date"],
            "status": status,
            "priority": priority,
        }
    )

result.sort(
    key=lambda x: (
        -x["priority"],
        -x["balance"],
    )
)

return result
# ============================================================
# JUDGE DEMO
# ============================================================

def load_demo():
d = today_date()

demo_transactions = [
    {
        "id": "demo1",
        "customer": "Ramesh",
        "amount": 500,
        "type": "owes",
        "date": "3 days ago",
        "date_iso": (d - timedelta(days=3)).isoformat(),
        "due_date": (d + timedelta(days=4)).isoformat(),
        "note": "Groceries",
        "source": "Judge Demo",
        "confirmed": True,
    },
    {
        "id": "demo2",
        "customer": "Sita",
        "amount": 250,
        "type": "owes",
        "date": "12 days ago",
        "date_iso": (d - timedelta(days=12)).isoformat(),
        "due_date": (d - timedelta(days=5)).isoformat(),
        "note": "Household items",
        "source": "Judge Demo",
        "confirmed": True,
    },
    {
        "id": "demo3",
        "customer": "Sita",
        "amount": 250,
        "type": "paid",
        "date": "5 days ago",
        "date_iso": (d - timedelta(days=5)).isoformat(),
        "due_date": "",
        "note": "Full repayment",
        "source": "Judge Demo",
        "repayment_days": 7,
        "confirmed": True,
    },
    {
        "id": "demo4",
        "customer": "Ravi",
        "amount": 1200,
        "type": "owes",
        "date": "16 days ago",
        "date_iso": (d - timedelta(days=16)).isoformat(),
        "due_date": (d - timedelta(days=2)).isoformat(),
        "note": "Farm supplies",
        "source": "Judge Demo",
        "confirmed": True,
    },
    {
        "id": "demo5",
        "customer": "Ravi",
        "amount": 300,
        "type": "paid",
        "date": "7 days ago",
        "date_iso": (d - timedelta(days=7)).isoformat(),
        "due_date": "",
        "note": "Partial repayment",
        "source": "Judge Demo",
        "repayment_days": 9,
        "confirmed": True,
    },
]

st.session_state.data["transactions"] = demo_transactions
st.session_state.data["last_receipt"] = None
st.session_state.data["demo_mode"] = True

save_data()

def clear_data():
st.session_state.data = empty_data()
st.session_state.pending_voice = None
st.session_state.voice_text = ""
st.session_state.voice_error = ""
st.session_state.reminder_text = ""
st.session_state.copilot_answer = ""
st.session_state.receipt_audio = None
save_data()

# ============================================================
SARVAM FUNCTIONS
# ============================================================

def create_sarvam():
if not SARVAM_API_KEY or SarvamAI is None:
return None

try:
    return SarvamAI(
        api_subscription_key=SARVAM_API_KEY
    )
except Exception:
    return None

SARVAM_CLIENT = create_sarvam()

def sarvam_transcribe(audio_bytes):
if SARVAM_CLIENT is None:
return None, "Sarvam AI is not available."

try:
    audio_file = BytesIO(audio_bytes)
    audio_file.name = "voice.wav"

    response = SARVAM_CLIENT.speech_to_text.transcribe(
        file=audio_file,
        model="saaras:v3",
    )

    text = getattr(
        response,
        "transcript",
        "",
    )

    if not text:
        return None, "No speech was detected."

    return text.strip(), ""

except Exception as error:
    return None, (
        "Sarvam voice processing failed. "
        "Manual entry is still available."
    )

def local_extract(text):
if not text:
return None

amount_match = re.search(
    r"(?:₹|rs\.?|rupees?)?\s*([0-9][0-9,]*)",
    text,
    re.IGNORECASE,
)

if not amount_match:
    return None

try:
    amount = float(
        amount_match.group(1).replace(",", "")
    )
except Exception:
    return None

lower = text.lower()

paid_words = [
    "paid",
    "repaid",
    "payment",
    "returned",
    "paid back",
    "చెల్లించాడు",
    "చెల్లించింది",
    "కట్టాడు",
    "కట్టింది",
    "ఇచ్చాడు",
    "ఇచ్చింది",
]

kind = "paid"

if not any(
    word in lower
    for word in paid_words
):
    kind = "owes"

name = ""

patterns = [
    r"([A-Za-z]+)\s+(?:took|borrowed)",
    r"([A-Za-z]+)\s+(?:paid|repaid)",
    r"([A-Za-z]+)\s+(?:₹|rs|rupees)",
    r"from\s+([A-Za-z]+)",
]

for pattern in patterns:
    match = re.search(
        pattern,
        text,
        re.IGNORECASE,
    )

    if match:
        name = match.group(1)
        break

if not name:
    words = re.findall(
        r"[A-Za-z]+",
        text,
    )

    ignored = {
        "took",
        "borrowed",
        "paid",
        "repaid",
        "rupees",
        "rs",
        "from",
        "on",
        "credit",
        "today",
        "gave",
    }

    for word in words:
        if word.lower() not in ignored:
            name = word
            break

if not name:
    return None

return {
    "customer": name.title(),
    "amount": amount,
    "type": kind,
    "due_date": "",
}

def telugu_audio(text):
if SARVAM_CLIENT is None:
return None

try:
    response = SARVAM_CLIENT.text_to_speech.convert(
        text=text[:2000],
        target_language_code="te-IN",
        speaker="kavitha",
    )

    audios = getattr(
        response,
        "audios",
        [],
    )

    if not audios:
        return None

    return base64.b64decode(audios[0])

except Exception:
    return None
# ============================================================
HERO
# ============================================================

if SARVAM_CLIENT is not None:
ai_text = "● AI ONLINE"
ai_class = "green"
else:
ai_text = "● AI OFFLINE"
ai_class = "yellow"

st.markdown(
f"""

<div class="hero"> <div class="brand"> TRUSTLEDGER </div> <div class="hero-title"> Turn Udhaar into Trust </div> <div class="hero-subtitle"> Paytm knows the payment.<br> TrustLedger knows the trust. </div> <div class="hero-description"> Voice-first, local-language, rural-friendly credit intelligence for small merchants. </div> <span class="pill"> TRUSTLAYER FOR MERCHANTS </span> <span class="pill {ai_class}"> {ai_text} </span> <span class="pill"> Proposed Paytm merchant integration concept • Hackathon prototype </span> </div> """, unsafe_allow_html=True, )
# ============================================================
SIDEBAR
# ============================================================

with st.sidebar:

st.markdown("## 💎 TrustLedger")

st.caption(
    "Informal credit → structured trust"
)

st.markdown("---")

if st.button(
    "🎬 LOAD JUDGE DEMO",
    key="load_demo",
    use_container_width=True,
):
    load_demo()
    st.success("Judge demo loaded!")
    st.rerun()

if st.button(
    "🗑️ Clear Demo Data",
    key="clear_demo",
    use_container_width=True,
):
    clear_data()
    st.success("Ledger cleared.")
    st.rerun()

st.markdown("---")

st.markdown("### 📶 RURAL-FIRST MODE")

st.markdown(
    """
<div class="rural"> <b>Record first. Sync later.</b> <br><br> Manual ledger records are stored locally. AI voice processing requires internet connectivity. </div> """, unsafe_allow_html=True, )
st.markdown("---")

st.markdown("### 💡 Business Value")

st.caption(
    "Paytm already knows digital payment activity. "
    "TrustLedger captures informal credit and repayment behaviour "
    "that can happen outside digital payments."
)

st.caption(
    "With merchant consent and responsible underwriting, "
    "structured repayment behaviour could potentially support "
    "future financial-product discovery."
)

st.caption(
    "Trust Score does not guarantee a loan and is not a loan approval."
)
# ============================================================
# DEMO BANNER
# ============================================================

if st.session_state.data.get("demo_mode"):

st.markdown(
    """
<div class="demo"> 🎬 <b>JUDGE DEMO MODE</b> <br> Ramesh — ₹500 Pending &nbsp; • &nbsp; Sita — ₹250 Settled &nbsp; • &nbsp; Ravi — ₹900 Outstanding </div> """, unsafe_allow_html=True, )

if SARVAM_CLIENT is None:

st.info(
    "Sarvam AI is unavailable. Manual Udhaar works normally. "
    "Voice AI activates when SARVAM_API_KEY is configured and internet is available."
)
# ============================================================
# METRICS
# ============================================================

score = trust_score()
rate = repayment_rate()
credit = credit_total()
pending = pending_total()

m1, m2, m3, m4 = st.columns(4)

with m1:

value = "New" if score is None else f"{score}/100"

st.markdown(
    f"""
<div class="metric"> <div class="metric-label">Trust Score</div> <div class="metric-value">{value}</div> </div> """, unsafe_allow_html=True, )

with m2:

st.markdown(
    f"""
<div class="metric"> <div class="metric-label">Repayment Rate</div> <div class="metric-value">{rate}%</div> </div> """, unsafe_allow_html=True, )

with m3:

st.markdown(
    f"""
<div class="metric"> <div class="metric-label">Credit Tracked</div> <div class="metric-value">₹{credit:,.0f}</div> </div> """, unsafe_allow_html=True, )

with m4:

st.markdown(
    f"""
<div class="metric"> <div class="metric-label">Pending Balance</div> <div class="metric-value">₹{pending:,.0f}</div> </div> """, unsafe_allow_html=True, )
# ============================================================
# TRUST JOURNEY
# ============================================================

st.markdown(
'<div class="section-title">The Trust Journey</div>',
unsafe_allow_html=True,
)

st.markdown(
'<div class="section-subtitle">From a simple Udhaar conversation to structured trust intelligence.</div>',
unsafe_allow_html=True,
)

st.markdown(
"""

<div class="story">

<span class="story-step">🎙️ Speak Udhaar</span>
<span class="arrow">→</span>
<span class="story-step">🧠 AI understands</span>
<span class="arrow">→</span>
<span class="story-step">✓ Confirm</span>
<span class="arrow">→</span>
<span class="story-step">🧾 Receipt</span>
<span class="arrow">→</span>
<span class="story-step">📒 Repayment</span>
<span class="arrow">→</span>
<span class="story-step">💎 Trust Score</span>
<span class="arrow">→</span>
<span class="story-step">🏦 Potential access</span>

</div> """, unsafe_allow_html=True, )
# ============================================================
# VOICE
# ============================================================

st.markdown(
'<div class="section-title">🎙️ Speak Udhaar</div>',
unsafe_allow_html=True,
)

st.markdown(
'<div class="section-subtitle">Example: "Rahul took 500 rupees on credit."</div>',
unsafe_allow_html=True,
)

voice_col1, voice_col2 = st.columns([1.2, .8])

with voice_col1:

audio = st.audio_input(
    "🎤 Record transaction",
    key="voice_input",
)

if audio is not None:

    if SARVAM_CLIENT is None:

        st.warning(
            "Sarvam AI is unavailable. Use Manual Udhaar below."
        )

    else:

        if st.button(
            "🧠 Understand with Sarvam AI",
            key="process_voice",
            type="primary",
            use_container_width=True,
        ):

            text, error = sarvam_transcribe(
                audio.getvalue()
            )

            if text:

                st.session_state.voice_text = text
                st.session_state.voice_error = ""

                extracted = local_extract(text)

                if extracted:

                    st.session_state.pending_voice = extracted

                else:

                    st.session_state.voice_error = (
                        "Speech was detected, but the customer "
                        "and amount could not be safely extracted."
                    )

            else:

                st.session_state.voice_error = error

with voice_col2:

st.markdown(
    """
<div class="card">

<b>Try saying:</b>

<br><br>

"Rahul took 500 rupees on credit."

<br><br>

"Ramesh paid 500 rupees."

<br><br>

<span class="muted"> Nothing is saved until the merchant confirms it. </span> </div> """, unsafe_allow_html=True, )

if st.session_state.voice_text:

st.markdown("#### 📝 Speech detected")

st.info(
    st.session_state.voice_text
)

if st.session_state.voice_error:

st.error(
    st.session_state.voice_error
)
# ============================================================
# VOICE CONFIRMATION
# ============================================================

if st.session_state.pending_voice:

item = st.session_state.pending_voice

st.markdown(
    "#### 🔎 Confirm AI Understanding"
)

c1, c2, c3 = st.columns(3)

with c1:
    st.metric(
        "Customer",
        item["customer"],
    )

with c2:
    st.metric(
        "Amount",
        f"₹{item['amount']:,.0f}",
    )

with c3:
    st.metric(
        "Type",
        "Udhaar" if item["type"] == "owes" else "Paid",
    )

confirm, cancel = st.columns(2)

with confirm:

    if st.button(
        "✅ AVUNU / CONFIRM",
        key="voice_confirm",
        type="primary",
        use_container_width=True,
    ):

        transaction = add_transaction(
            customer=item["customer"],
            amount=item["amount"],
            transaction_type=item["type"],
            source="Sarvam Voice",
        )

        receipt_sentence = (
            f"TrustLedger receipt. "
            f"{transaction['customer']} "
            f"{transaction['amount']:,.0f} rupees "
            "transaction has been recorded."
        )

        st.session_state.receipt_audio = telugu_audio(
            receipt_sentence
        )

        st.session_state.pending_voice = None
        st.session_state.voice_text = ""

        st.success(
            "Transaction confirmed and saved."
        )

        st.rerun()

with cancel:

    if st.button(
        "❌ KADU / CANCEL",
        key="voice_cancel",
        use_container_width=True,
    ):

        st.session_state.pending_voice = None
        st.info("Transaction cancelled.")
        st.rerun()
# ============================================================
# MANUAL ENTRY
# ============================================================

st.markdown(
'<div class="section-title">📝 Manual / Offline Udhaar</div>',
unsafe_allow_html=True,
)

st.markdown(
'<div class="section-subtitle">Works without the AI API. Record first, sync later.</div>',
unsafe_allow_html=True,
)

with st.form(
"manual_transaction_form",
clear_on_submit=True,
):

f1, f2 = st.columns(2)

with f1:

    customer = st.text_input(
        "Customer name",
        placeholder="Ramesh",
    )

    amount = st.number_input(
        "Amount ₹",
        min_value=1.0,
        value=500.0,
        step=50.0,
    )

with f2:

    kind = st.selectbox(
        "Transaction type",
        ["owes", "paid"],
        format_func=lambda value:
            "Customer owes / Udhaar"
            if value == "owes"
            else "Customer paid / Repayment",
    )

    due = st.date_input(
        "Due date",
        value=today_date() + timedelta(days=7),
    )

note = st.text_input(
    "Note",
    placeholder="Groceries / farm supplies / household items",
)

submitted = st.form_submit_button(
    "💾 SAVE TRANSACTION",
    type="primary",
    use_container_width=True,
)

if submitted:

    if not customer.strip():

        st.error(
            "Enter the customer name."
        )

    else:

        due_string = (
            due.isoformat()
            if kind == "owes"
            else ""
        )

        add_transaction(
            customer=customer,
            amount=amount,
            transaction_type=kind,
            due_date=due_string,
            note=note,
            source="Manual / Offline",
        )

        st.success(
            f"₹{amount:,.0f} saved for {customer}."
        )
# ============================================================
# UPLOAD
# ============================================================

st.markdown(
'<div class="section-title">📎 Upload Transaction / Receipt</div>',
unsafe_allow_html=True,
)

uploaded = st.file_uploader(
"Upload a receipt or transaction image",
type=["png", "jpg", "jpeg", "pdf"],
key="upload_receipt",
)

if uploaded:

st.success(
    f"Receipt uploaded: {uploaded.name}"
)

if uploaded.type.startswith("image/"):

    st.image(
        uploaded,
        caption="Uploaded receipt",
    )
# ============================================================
# TRUST SCORE
# ============================================================

st.markdown(
'<div class="section-title">💎 AI Trust Score</div>',
unsafe_allow_html=True,
)

st.markdown(
'<div class="section-subtitle">Calculated from actual ledger behaviour — not a permanently fixed demo number.</div>',
unsafe_allow_html=True,
)

score_col, explanation_col = st.columns([.8, 1.2])

with score_col:

if score is None:

    st.markdown(
        """
<div class="trust-card"> <div class="muted"> CURRENT TRUST </div> <div class="trust-new"> NEW </div> <div class="muted"> Record repayment behaviour to build a score. </div> </div> """, unsafe_allow_html=True, )
else:

    st.markdown(
        f"""
<div class="trust-card"> <div class="muted"> CURRENT TRUST </div> <div class="trust-number"> {score}<span style="font-size:20px;color:#77829a;">/100</span> </div> <div class="muted"> {trust_label(score)} </div> </div> """, unsafe_allow_html=True, )

with explanation_col:

st.markdown(
    """
<div class="card">

<b>Why this score?</b>

<br><br>

""",
unsafe_allow_html=True,
)

if score is None:

    st.write(
        "• No transaction history yet."
    )

else:

    st.write(
        f"• Repayment rate: {rate}%"
    )

    people = summaries()

    settled = sum(
        1
        for x in people.values()
        if x["credit"] > 0 and x["balance"] <= 0
    )

    pending_people = sum(
        1
        for x in people.values()
        if x["balance"] > 0
    )

    st.write(
        f"• Settled customers: {settled}"
    )

    st.write(
        f"• Customers with pending balance: {pending_people}"
    )

    st.write(
        "• Higher repayment behaviour increases the score."
    )

st.markdown(
    "</div>",
    unsafe_allow_html=True,
)
# ============================================================
# TRUST CAPITAL
# ============================================================

st.markdown(
'<div class="section-title">💠 VERIFIED TRUST CAPITAL</div>',
unsafe_allow_html=True,
)

st.markdown(
f"""

<div class="card"> <div style="font-size:34px;font-weight:900;"> ₹{paid_total():,.0f} </div> <div class="muted"> Verified repaid credit </div> <br> <div class="muted" style="line-height:1.7;"> This is a behavioural indicator based on tracked and repaid credit. It is <b>NOT</b> a bank balance, loan amount, or loan approval. </div> </div> """, unsafe_allow_html=True, )
# ============================================================
# COLLECTION PRIORITIES
# ============================================================

st.markdown(
'<div class="section-title">🎯 Collection Priorities</div>',
unsafe_allow_html=True,
)

st.markdown(
'<div class="section-subtitle">The most important pending customers appear first.</div>',
unsafe_allow_html=True,
)

priority_rows = priorities()

if not priority_rows:

st.success(
    "No pending collection priorities."
)

else:

for index, row in enumerate(priority_rows):

    p1, p2, p3, p4 = st.columns(
        [2, 1, 2, 1]
    )

    with p1:

        st.markdown(
            f"**{index + 1}. {row['name']}**"
        )

    with p2:

        st.markdown(
            f"**₹{row['balance']:,.0f}**"
        )

    with p3:

        st.markdown(
            row["status"]
        )

    with p4:

        if st.button(
            "Reminder",
            key=f"make_reminder_{index}",
        ):

            reminder = (
                f"నమస్కారం {row['name']} గారు. "
                f"మీ ఖాతాలో ఇంకా ₹{row['balance']:,.0f} బాకీ ఉంది. "
                "మీకు వీలైనప్పుడు దయచేసి చెల్లించండి. "
                "ధన్యవాదాలు."
            )

            st.session_state.reminder_text = reminder
# ============================================================
# REMINDER
# ============================================================

if st.session_state.reminder_text:

st.markdown(
    '<div class="section-title">📢 Telugu Repayment Reminder</div>',
    unsafe_allow_html=True,
)

st.text_area(
    "Polite Telugu reminder",
    value=st.session_state.reminder_text,
    height=120,
    key="reminder_display",
)

if st.button(
    "🔊 Generate Telugu Audio",
    key="generate_reminder_audio",
):

    audio_bytes = telugu_audio(
        st.session_state.reminder_text
    )

    if audio_bytes:

        st.audio(
            audio_bytes,
            format="audio/wav",
        )

    else:

        st.info(
            "Telugu audio requires Sarvam AI connectivity."
        )
# ============================================================
# RECENT UDHAR
# ============================================================

st.markdown(
'<div class="section-title">📒 Recent Udhaar</div>',
unsafe_allow_html=True,
)

transactions = st.session_state.data["transactions"]

if not transactions:

st.info(
    "No transactions yet. Click LOAD JUDGE DEMO to see the complete story."
)

else:

for transaction in reversed(
    transactions[-10:]
):

    kind = transaction.get(
        "type",
        "owes",
    )

    label = (
        "Repayment"
        if kind == "paid"
        else "Udhaar"
    )

    status = (
        "🟢 PAID"
        if kind == "paid"
        else "🟡 CREDIT"
    )

    st.markdown(
        f"""
<div class="card" style="margin-bottom:10px;"> <div style="display:flex;justify-content:space-between;gap:15px;flex-wrap:wrap;"> <div> <b>{transaction.get("customer","Unknown")}</b> <br> <span class="muted"> {label} • {transaction.get("date","")} </span> </div> <div> <b style="font-size:20px;"> ₹{float(transaction.get("amount",0)):,.0f} </b> </div> <div> {status} </div> </div> </div> """, unsafe_allow_html=True, )
# ============================================================
# CUSTOMER LEDGER
# ============================================================

st.markdown(
'<div class="section-title">👥 Customer Ledger</div>',
unsafe_allow_html=True,
)

customer_data = summaries()

if not customer_data:

st.info(
    "Customer balances will appear here after transactions are recorded."
)

else:

for name, item in sorted(
    customer_data.items(),
    key=lambda x: -x[1]["balance"],
):

    status = status_for(
        item["balance"],
        item["due_date"],
    )

    st.markdown(
        f"""
<div class="card" style="margin-bottom:10px;"> <div style="display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;"> <div> <b style="font-size:18px;">{name}</b> <br> <span class="muted"> Credit ₹{item["credit"]:,.0f} &nbsp; • &nbsp; Paid ₹{item["paid"]:,.0f} &nbsp; • &nbsp; {item["transactions"]} transactions </span> </div> <div> <b style="font-size:21px;"> ₹{item["balance"]:,.0f} </b> <br> <span class="muted">Outstanding</span> </div> <div> {status} </div> </div> </div> """, unsafe_allow_html=True, )
# ============================================================
# RECEIPT
# ============================================================

receipt = st.session_state.data.get(
"last_receipt"
)

if receipt:

st.markdown(
    '<div class="section-title">🧾 Verified Receipt</div>',
    unsafe_allow_html=True,
)

if receipt.get("type") == "owes":
    transaction_label = "Udhaar / Credit Given"
else:
    transaction_label = "Repayment Received"

st.markdown(
    f"""
<div class="receipt"> <div style="font-size:22px;font-weight:900;"> 💎 TRUSTLEDGER </div> <div class="muted"> Verified Merchant Receipt </div> <br> <div style="padding:9px 0;border-bottom:1px solid rgba(255,255,255,.06);"> Customer: <b>{receipt.get("customer")}</b> </div> <div style="padding:9px 0;border-bottom:1px solid rgba(255,255,255,.06);"> Amount: <b>₹{float(receipt.get("amount",0)):,.0f}</b> </div> <div style="padding:9px 0;border-bottom:1px solid rgba(255,255,255,.06);"> Transaction: <b>{transaction_label}</b> </div> <div style="padding:9px 0;border-bottom:1px solid rgba(255,255,255,.06);"> Date: <b>{receipt.get("date")}</b> </div> <div style="padding:9px 0;border-bottom:1px solid rgba(255,255,255,.06);"> Source: <b>{receipt.get("source")}</b> </div> <div style="padding:12px 0;"> <b>✓ VERIFIED</b> </div> </div> """, unsafe_allow_html=True, )
receipt_text = (
    "TRUSTLEDGER\n"
    "Verified Merchant Receipt\n\n"
    f"Customer: {receipt.get('customer')}\n"
    f"Amount: ₹{float(receipt.get('amount',0)):,.0f}\n"
    f"Transaction: {transaction_label}\n"
    f"Date: {receipt.get('date')}\n"
    f"Source: {receipt.get('source')}\n"
    "Status: VERIFIED\n"
)

st.download_button(
    "🧾 Download Receipt",
    data=receipt_text,
    file_name="trustledger_receipt.txt",
    mime="text/plain",
    key="download_receipt_file",
)

if st.button(
    "🔊 Generate Telugu Receipt Audio",
    key="receipt_audio_button",
):

    audio_bytes = telugu_audio(
        f"TrustLedger receipt. "
        f"{receipt.get('customer')} గారి "
        f"{receipt.get('amount'):,.0f} రూపాయల "
        "లావాదేవీ నమోదు చేయబడింది."
    )

    if audio_bytes:

        st.session_state.receipt_audio = audio_bytes

    else:

        st.warning(
            "Telugu audio requires Sarvam AI connectivity."
        )

if st.session_state.receipt_audio:

    st.audio(
        st.session_state.receipt_audio,
        format="audio/wav",
    )
# ============================================================
# COPILOT
# ============================================================

st.markdown(
'<div class="section-title">🤖 TrustLedger Copilot</div>',
unsafe_allow_html=True,
)

st.markdown(
'<div class="section-subtitle">A domain-bounded merchant assistant.</div>',
unsafe_allow_html=True,
)

q1, q2 = st.columns([1.3, .7])

with q1:

question = st.text_input(
    "Ask Copilot",
    placeholder="Who owes me the most?",
    key="copilot_input",
)

with q2:

st.markdown("<br>", unsafe_allow_html=True)

ask_copilot = st.button(
    "🤖 Ask Copilot",
    key="ask_copilot",
    type="primary",
    use_container_width=True,
)

if ask_copilot:

q = question.lower().strip()

allowed_words = [
    "udhaar",
    "credit",
    "owe",
    "owes",
    "owing",
    "repayment",
    "repay",
    "paid",
    "balance",
    "customer",
    "customers",
    "receipt",
    "collection",
    "collect",
    "reminder",
    "trust",
    "score",
    "pending",
    "due",
    "ledger",
    "money",
]

if not any(
    word in q
    for word in allowed_words
):

    st.session_state.copilot_answer = (
        "I’m TrustLedger Copilot. I can only help with Udhaar, "
        "repayments, receipts, collections and merchant trust insights."
    )

elif not transactions:

    st.session_state.copilot_answer = (
        "Your ledger is empty. Record your first Udhaar transaction."
    )

elif (
    "who" in q
    and (
        "owe" in q
        or "owing" in q
    )
):

    people = [
        (
            name,
            item["balance"],
        )
        for name, item in summaries().items()
        if item["balance"] > 0
    ]

    people.sort(
        key=lambda x: -x[1]
    )

    if people:

        lines = [
            f"• {name}: ₹{balance:,.0f}"
            for name, balance in people[:5]
        ]

        st.session_state.copilot_answer = (
            "Customers with pending Udhaar:\n\n"
            + "\n".join(lines)
        )

    else:

        st.session_state.copilot_answer = (
            "No customer currently has an outstanding balance."
        )

elif "score" in q:

    if score is None:

        st.session_state.copilot_answer = (
            "Trust Score: New. "
            "Track repayments to build behavioural history."
        )

    else:

        st.session_state.copilot_answer = (
            f"Trust Score: {score}/100 ({trust_label(score)}). "
            f"Repayment rate: {rate}%."
        )

elif (
    "pending" in q
    or "balance" in q
    or "collection" in q
):

    st.session_state.copilot_answer = (
        f"Total outstanding Udhaar: ₹{pending:,.0f}. "
        f"{len(priority_rows)} customer(s) need attention."
    )

elif "receipt" in q:

    if receipt:

        st.session_state.copilot_answer = (
            f"Latest receipt: {receipt.get('customer')} "
            f"— ₹{float(receipt.get('amount',0)):,.0f}."
        )

    else:

        st.session_state.copilot_answer = (
            "No receipt has been generated yet."
        )

elif (
    "repay" in q
    or "paid" in q
):

    st.session_state.copilot_answer = (
        f"Tracked credit: ₹{credit:,.0f}. "
        f"Recorded repayments: ₹{paid_total():,.0f}. "
        f"Repayment rate: {rate}%."
    )

else:

    st.session_state.copilot_answer = (
        "I can help with Udhaar, repayments, pending balances, "
        "customers who owe money, receipts, collection reminders "
        "and Trust Score insights."
    )

if st.session_state.copilot_answer:

safe_answer = (
    st.session_state.copilot_answer
    .replace("&", "&amp;")
    .replace("<", "&lt;")
    .replace(">", "&gt;")
    .replace("\n", "<br>")
)

st.markdown(
    f"""
<div class="copilot">

<b>🤖 TrustLedger Copilot</b>

<br><br>

{safe_answer}

</div> """, unsafe_allow_html=True, )
# ============================================================
# WHY IT MATTERS
# ============================================================

st.markdown(
'<div class="section-title">🚀 Why TrustLedger Matters</div>',
unsafe_allow_html=True,
)

v1, v2, v3 = st.columns(3)

with v1:

st.markdown(
    """
<div class="card"> <h3>01 · Capture</h3>

Informal Udhaar that normally lives in memory,
notebooks or verbal promises becomes structured.

</div> """, unsafe_allow_html=True, )

with v2:

st.markdown(
    """
<div class="card"> <h3>02 · Understand</h3>

Repayment behaviour becomes visible through balances,
collection priorities and a transparent Trust Score.

</div> """, unsafe_allow_html=True, )

with v3:

st.markdown(
    """
<div class="card"> <h3>03 · Future Value</h3>

With consent and responsible underwriting,
structured behaviour could potentially support
future financial-product discovery.

</div> """, unsafe_allow_html=True, )
# ============================================================
# FOOTER
# ============================================================

st.markdown(
"""

<div style=" margin-top:45px; padding:25px; text-align:center; border-top:1px solid rgba(255,255,255,.06); color:#69758c; "> <b style="color:#aab4d0;"> TRUSTLEDGER </b>

<br><br>

Paytm knows the payment. TrustLedger knows the trust.

<br><br>

<span style="font-size:11px;"> Proposed Paytm merchant integration concept • Hackathon prototype <br> Trust Score is a behavioural indicator, not a loan approval or guarantee. </span> </div> """, unsafe_allow_html=True, )
