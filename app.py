import io
import os
import json
from datetime import datetime, date, timedelta

import streamlit as st
from dotenv import load_dotenv

try:
    from sarvamai import SarvamAI
except Exception:
    SarvamAI = None

load_dotenv()

DATA_FILE = "trustledger_data.json"
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "").strip()

st.set_page_config(
    page_title="TrustLedger",
    page_icon="💎",
    layout="wide",
)

st.markdown("""
<style>
.stApp {
    background: radial-gradient(circle at 10% 0%, rgba(91,78,220,.22), transparent 30%),
                radial-gradient(circle at 90% 10%, rgba(0,170,170,.10), transparent 25%),
                #070a12;
    color: #f5f7ff;
}
.block-container {
    max-width: 1450px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}
.hero {
    background: linear-gradient(135deg, #211e50, #0b0f1c);
    border: 1px solid rgba(255,255,255,.10);
    border-radius: 28px;
    padding: 38px;
    margin-bottom: 25px;
}
.brand {
    color: #a7a0ff;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 4px;
}
.hero-title {
    font-size: 60px;
    font-weight: 900;
    line-height: 1;
    margin-top: 10px;
}
.hero-subtitle {
    font-size: 24px;
    font-weight: 700;
    color: #cbd0ff;
    margin-top: 18px;
}
.hero-description {
    color: #aab3c7;
    max-width: 850px;
    line-height: 1.7;
}
.card, .metric {
    background: rgba(16,21,36,.90);
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 20px;
    padding: 20px;
}
.metric-label {
    color: #7f8ba4;
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
}
.metric-value {
    font-size: 28px;
    font-weight: 900;
    margin-top: 5px;
}
.section-title {
    font-size: 25px;
    font-weight: 900;
    margin-top: 30px;
}
.section-subtitle {
    color: #8591a9;
    font-size: 13px;
    margin-bottom: 15px;
}
.trust-card {
    text-align: center;
    padding: 30px;
    border-radius: 23px;
    background: rgba(15,20,36,.95);
    border: 1px solid rgba(120,110,255,.20);
}
.trust-number {
    font-size: 64px;
    font-weight: 900;
}
.demo {
    background: rgba(255,190,50,.08);
    border: 1px solid rgba(255,190,50,.22);
    border-radius: 15px;
    padding: 14px 17px;
    color: #ffd77e;
}
.copilot {
    background: linear-gradient(135deg, #15182c, #211735);
    border: 1px solid rgba(130,110,255,.20);
    border-radius: 20px;
    padding: 20px;
}
</style>
""", unsafe_allow_html=True)


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
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

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
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(
                st.session_state.data,
                f,
                ensure_ascii=False,
                indent=2,
            )
        return True
    except Exception:
        return False


if "data" not in st.session_state:
    st.session_state.data = load_data()

if "reminder_text" not in st.session_state:
    st.session_state.reminder_text = ""

if "copilot_answer" not in st.session_state:
    st.session_state.copilot_answer = ""

if "voice_transcript" not in st.session_state:
    st.session_state.voice_transcript = ""

if "voice_customer" not in st.session_state:
    st.session_state.voice_customer = ""

if "voice_amount" not in st.session_state:
    st.session_state.voice_amount = 0.0

if "voice_type" not in st.session_state:
    st.session_state.voice_type = "owes"


def today_date():
    return date.today()


def now_text():
    return datetime.now().strftime("%d %b %Y, %I:%M %p")


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

    for t in st.session_state.data["transactions"]:
        name = t.get("customer", "Unknown")
        amount = float(t.get("amount", 0))
        kind = t.get("type", "owes")

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

            if t.get("due_date"):
                result[name]["due_date"] = t["due_date"]
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
        x["balance"]
        for x in summaries().values()
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

    repayment = min(1, paid_total() / credit)
    people = summaries()

    settled = sum(
        1
        for x in people.values()
        if x["credit"] > 0 and x["balance"] <= 0
    )

    pending = sum(
        1
        for x in people.values()
        if x["balance"] > 0
    )

    overdue = 0

    for x in people.values():
        due = x.get("due_date", "")

        if due and x["balance"] > 0:
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

    return max(0, min(100, round(score)))


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

        result.append({
            "name": name,
            "balance": item["balance"],
            "due": item["due_date"],
            "status": status,
            "priority": priority,
        })

    result.sort(
        key=lambda x: (
            -x["priority"],
            -x["balance"],
        )
    )

    return result


def load_demo():
    d = today_date()

    st.session_state.data["transactions"] = [
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
            "date": "6 days ago",
            "date_iso": (d - timedelta(days=6)).isoformat(),
            "due_date": "",
            "note": "Partial repayment",
            "source": "Judge Demo",
            "confirmed": True,
        },
    ]

    st.session_state.data["last_receipt"] = None
    st.session_state.data["demo_mode"] = True
    save_data()


# HERO

st.markdown("""
<div class="hero">
<div class="brand">TRUSTLEDGER</div>
<div class="hero-title">💎 TrustLedger</div>
<div class="hero-subtitle">
Paytm knows the payment. TrustLedger knows the trust.
</div>
<div class="hero-description">
A merchant-first Udhaar ledger that converts informal credit
into structured repayment behaviour and transparent trust insights.
</div>
</div>
""", unsafe_allow_html=True)


# DEMO BUTTONS

b1, b2 = st.columns(2)

with b1:
    if st.button(
        "🎬 LOAD JUDGE DEMO",
        type="primary",
        use_container_width=True,
    ):
        load_demo()
        st.rerun()

with b2:
    if st.button(
        "🗑️ CLEAR LEDGER",
        use_container_width=True,
    ):
        st.session_state.data = empty_data()
        save_data()
        st.rerun()


if st.session_state.data.get("demo_mode"):
    st.markdown("""
    <div class="demo">
    🎬 <b>JUDGE DEMO MODE</b><br>
    Ramesh — ₹500 Pending &nbsp; • &nbsp;
    Sita — ₹250 Settled &nbsp; • &nbsp;
    Ravi — ₹900 Outstanding
    </div>
    """, unsafe_allow_html=True)


# METRICS

score = trust_score()
rate = repayment_rate()
credit = credit_total()
pending = pending_total()

m1, m2, m3, m4 = st.columns(4)

with m1:
    value = "New" if score is None else f"{score}/100"
    st.markdown(
        f'<div class="metric"><div class="metric-label">Trust Score</div>'
        f'<div class="metric-value">{value}</div></div>',
        unsafe_allow_html=True,
    )

with m2:
    st.markdown(
        f'<div class="metric"><div class="metric-label">Repayment Rate</div>'
        f'<div class="metric-value">{rate}%</div></div>',
        unsafe_allow_html=True,
    )

with m3:
    st.markdown(
        f'<div class="metric"><div class="metric-label">Credit Tracked</div>'
        f'<div class="metric-value">₹{credit:,.0f}</div></div>',
        unsafe_allow_html=True,
    )

with m4:
    st.markdown(
        f'<div class="metric"><div class="metric-label">Pending Balance</div>'
        f'<div class="metric-value">₹{pending:,.0f}</div></div>',
        unsafe_allow_html=True,
    )


# TRUST JOURNEY

st.markdown(
    '<div class="section-title">The Trust Journey</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="card">
    🎙️ Speak Udhaar → 🧠 AI understands → ✓ Confirm →
    🧾 Receipt → 📒 Repayment → 💎 Trust Score → 🏦 Potential access
    </div>
    """,
    unsafe_allow_html=True,
)

# VOICE INPUT

st.markdown(
    '<div class="section-title">🎤 Voice Udhaar</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="card">
    <b>Speak instead of typing.</b><br>
    Say something like:
    <b>"Ramesh took 500 rupees on credit."</b><br>
    You can speak in Telugu, Hindi, English or other supported Indian languages.
    </div>
    """,
    unsafe_allow_html=True,
)

if SarvamAI is None:
    st.warning(
        "Sarvam AI SDK is not installed. Run: pip install -U sarvamai"
    )
elif not SARVAM_API_KEY:
    st.warning(
        "Voice input needs SARVAM_API_KEY in your .env file."
    )
else:
    voice_audio = st.audio_input(
        "🎤 Tap to record your Udhaar transaction",
        key="trustledger_voice",
    )

    if voice_audio is not None:
        try:
            client = SarvamAI(
                api_subscription_key=SARVAM_API_KEY
            )

            audio_bytes = voice_audio.getvalue()
            wav_file = io.BytesIO(audio_bytes)
            wav_file.name = "voice.wav"

            response = client.speech_to_text.transcribe(
                file=wav_file,
                model="saaras:v3",
                language_code="unknown",
                mode="transcribe",
            )

            transcript = getattr(
                response,
                "transcript",
                "",
            )

            if transcript:
                st.session_state.voice_transcript = transcript
                st.success("✅ Voice understood!")

            else:
                st.error(
                    "I could not understand the recording. Please try again."
                )

        except Exception as e:
            st.error(
                f"Voice transcription failed: {str(e)}"
            )

if st.session_state.voice_transcript:
    st.markdown("### 🧠 What TrustLedger understood")

    st.info(
        st.session_state.voice_transcript
    )

    st.markdown(
        "Please confirm the details before saving."
    )

    vf1, vf2 = st.columns(2)

    with vf1:
        voice_customer = st.text_input(
            "Customer name",
            value=st.session_state.voice_customer,
            key="voice_customer_input",
        )

        voice_amount = st.number_input(
            "Amount ₹",
            min_value=1.0,
            value=(
                st.session_state.voice_amount
                if st.session_state.voice_amount > 0
                else 500.0
            ),
            step=50.0,
            key="voice_amount_input",
        )

    with vf2:
        voice_type = st.selectbox(
            "Transaction type",
            ["owes", "paid"],
            index=(
                0
                if st.session_state.voice_type == "owes"
                else 1
            ),
            format_func=lambda x:
            "Customer owes / Udhaar"
            if x == "owes"
            else "Customer paid / Repayment",
            key="voice_type_input",
        )

    vc1, vc2 = st.columns(2)

    with vc1:
        if st.button(
            "✅ CONFIRM & SAVE VOICE TRANSACTION",
            type="primary",
            use_container_width=True,
        ):
            if not voice_customer.strip():
                st.error("Please enter the customer name.")
            else:
                add_transaction(
                    customer=voice_customer,
                    amount=voice_amount,
                    transaction_type=voice_type,
                    due_date=(
                        (
                            today_date()
                            + timedelta(days=7)
                        ).isoformat()
                        if voice_type == "owes"
                        else ""
                    ),
                    note="Voice transaction",
                    source="Voice / Sarvam AI",
                )

                st.session_state.voice_transcript = ""
                st.session_state.voice_customer = ""
                st.session_state.voice_amount = 0.0
                st.session_state.voice_type = "owes"

                st.success(
                    "🎉 Voice transaction saved successfully!"
                )

                st.rerun()

    with vc2:
        if st.button(
            "🔄 CLEAR VOICE",
            use_container_width=True,
        ):
            st.session_state.voice_transcript = ""
            st.session_state.voice_customer = ""
            st.session_state.voice_amount = 0.0
            st.session_state.voice_type = "owes"

            st.rerun()


# MANUAL ENTRY

st.markdown(
    '<div class="section-title">📝 Manual / Offline Udhaar</div>',
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
            format_func=lambda x:
            "Customer owes / Udhaar"
            if x == "owes"
            else "Customer paid / Repayment",
        )

        due = st.date_input(
            "Due date",
            value=today_date() + timedelta(days=7),
        )

    note = st.text_input(
        "Note",
        placeholder="Groceries / farm supplies",
    )

    submitted = st.form_submit_button(
        "💾 SAVE TRANSACTION",
        type="primary",
        use_container_width=True,
    )

    if submitted:
        if not customer.strip():
            st.error("Enter the customer name.")
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


# TRUST SCORE

st.markdown(
    '<div class="section-title">💎 AI Trust Score</div>',
    unsafe_allow_html=True,
)

c1, c2 = st.columns([1, 2])

with c1:
    if score is None:
        st.markdown(
            """
            <div class="trust-card">
            <div> CURRENT TRUST </div>
            <div class="trust-number">NEW</div>
            <div>Record repayments to build history.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="trust-card">
            <div> CURRENT TRUST </div>
            <div class="trust-number">{score}/100</div>
            <div>{trust_label(score)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with c2:
    st.markdown(
        f"""
        <div class="card">
        <b>Why this score?</b><br><br>
        • Repayment rate: {rate}%<br>
        • Tracked credit: ₹{credit:,.0f}<br>
        • Pending balance: ₹{pending:,.0f}<br>
        • Higher repayment behaviour improves trust.
        </div>
        """,
        unsafe_allow_html=True,
    )


# COLLECTION PRIORITIES

st.markdown(
    '<div class="section-title">🎯 Collection Priorities</div>',
    unsafe_allow_html=True,
)

priority_rows = priorities()

if not priority_rows:
    st.success("No pending collection priorities.")
else:
    for index, row in enumerate(priority_rows):
        p1, p2, p3, p4 = st.columns([2, 1, 2, 1])

        with p1:
            st.markdown(
                f"**{index + 1}. {row['name']}**"
            )

        with p2:
            st.markdown(
                f"**₹{row['balance']:,.0f}**"
            )

        with p3:
            st.markdown(row["status"])

        with p4:
            if st.button(
                "Reminder",
                key=f"reminder_{index}",
            ):
                st.session_state.reminder_text = (
                    f"నమస్కారం {row['name']} గారు. "
                    f"మీ ఖాతాలో ఇంకా ₹{row['balance']:,.0f} బాకీ ఉంది. "
                    "మీకు వీలైనప్పుడు దయచేసి చెల్లించండి. ధన్యవాదాలు."
                )


# REMINDER

if st.session_state.reminder_text:
    st.markdown(
        '<div class="section-title">📢 Telugu Repayment Reminder</div>',
        unsafe_allow_html=True,
    )

    st.text_area(
        "Polite Telugu reminder",
        value=st.session_state.reminder_text,
        height=120,
    )


# RECENT TRANSACTIONS

st.markdown(
    '<div class="section-title">📒 Recent Udhaar</div>',
    unsafe_allow_html=True,
)

transactions = st.session_state.data["transactions"]

if not transactions:
    st.info("No transactions yet.")
else:
    for t in reversed(transactions[-10:]):
        label = (
            "Repayment"
            if t.get("type") == "paid"
            else "Udhaar"
        )

        status = (
            "🟢 PAID"
            if t.get("type") == "paid"
            else "🟡 CREDIT"
        )

        st.markdown(
            f"""
            <div class="card" style="margin-bottom:10px;">
            <b>{t.get("customer", "Unknown")}</b><br>
            {label} • {t.get("date", "")}
            <span style="float:right;">
            <b>₹{float(t.get("amount", 0)):,.0f}</b>
            &nbsp; {status}
            </span>
            </div>
            """,
            unsafe_allow_html=True,
        )


# CUSTOMER LEDGER

st.markdown(
    '<div class="section-title">👥 Customer Ledger</div>',
    unsafe_allow_html=True,
)

customer_data = summaries()

if not customer_data:
    st.info("Customer balances will appear here.")
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
            <div class="card" style="margin-bottom:10px;">
            <b style="font-size:18px;">{name}</b><br>
            Credit ₹{item["credit"]:,.0f}
            • Paid ₹{item["paid"]:,.0f}
            • {item["transactions"]} transactions
            <span style="float:right;">
            <b>₹{item["balance"]:,.0f}</b><br>
            {status}
            </span>
            </div>
            """,
            unsafe_allow_html=True,
        )


# RECEIPT

receipt = st.session_state.data.get("last_receipt")

if receipt:
    st.markdown(
        '<div class="section-title">🧾 Verified Receipt</div>',
        unsafe_allow_html=True,
    )

    label = (
        "Udhaar / Credit Given"
        if receipt.get("type") == "owes"
        else "Repayment Received"
    )

    receipt_text = (
        "TRUSTLEDGER\n"
        "Verified Merchant Receipt\n\n"
        f"Customer: {receipt.get('customer')}\n"
        f"Amount: ₹{float(receipt.get('amount', 0)):,.0f}\n"
        f"Transaction: {label}\n"
        f"Date: {receipt.get('date')}\n"
        f"Source: {receipt.get('source')}\n"
        "Status: VERIFIED\n"
    )

    st.markdown(
        f"""
        <div class="card">
        💎 <b>TRUSTLEDGER</b><br><br>
        Customer: <b>{receipt.get("customer")}</b><br>
        Amount: <b>₹{float(receipt.get("amount", 0)):,.0f}</b><br>
        Transaction: <b>{label}</b><br>
        Date: <b>{receipt.get("date")}</b><br>
        ✓ VERIFIED
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.download_button(
        "🧾 Download Receipt",
        data=receipt_text,
        file_name="trustledger_receipt.txt",
        mime="text/plain",
    )


# COPILOT

st.markdown(
    '<div class="section-title">🤖 TrustLedger Copilot</div>',
    unsafe_allow_html=True,
)

question = st.text_input(
    "Ask Copilot",
    placeholder="Who owes me the most?",
)

if st.button(
    "🤖 Ask Copilot",
    type="primary",
):
    q = question.lower().strip()

    if not transactions:
        st.session_state.copilot_answer = (
            "Your ledger is empty. Record your first transaction."
        )

    elif "who" in q and (
        "owe" in q or "owing" in q
    ):
        people = [
            (name, item["balance"])
            for name, item in summaries().items()
            if item["balance"] > 0
        ]

        people.sort(
            key=lambda x: -x[1]
        )

        if people:
            st.session_state.copilot_answer = (
                "Customers with pending Udhaar:\n\n"
                + "\n".join(
                    f"• {name}: ₹{balance:,.0f}"
                    for name, balance in people[:5]
                )
            )
        else:
            st.session_state.copilot_answer = (
                "No customer currently owes money."
            )

    elif "score" in q:
        st.session_state.copilot_answer = (
            f"Trust Score: "
            f"{'New' if score is None else f'{score}/100'}."
            f" Repayment rate: {rate}%."
        )

    elif (
        "pending" in q
        or "balance" in q
        or "collection" in q
    ):
        st.session_state.copilot_answer = (
            f"Total outstanding Udhaar: ₹{pending:,.0f}."
        )

    elif "receipt" in q:
        if receipt:
            st.session_state.copilot_answer = (
                f"Latest receipt: "
                f"{receipt.get('customer')} — "
                f"₹{float(receipt.get('amount', 0)):,.0f}."
            )
        else:
            st.session_state.copilot_answer = (
                "No receipt has been generated yet."
            )

    elif "repay" in q or "paid" in q:
        st.session_state.copilot_answer = (
            f"Tracked credit: ₹{credit:,.0f}. "
            f"Recorded repayments: ₹{paid_total():,.0f}. "
            f"Repayment rate: {rate}%."
        )

    else:
        st.session_state.copilot_answer = (
            "I can help with Udhaar, repayments, "
            "balances, receipts, collections and Trust Score."
        )

if st.session_state.copilot_answer:
    st.markdown(
        f"""
        <div class="copilot">
        <b>🤖 TrustLedger Copilot</b><br><br>
        {st.session_state.copilot_answer.replace(chr(10), "<br>")}
        </div>
        """,
        unsafe_allow_html=True,
    )


# FOOTER

st.markdown(
    """
    <div style="margin-top:45px;padding:25px;text-align:center;
    border-top:1px solid rgba(255,255,255,.06);">
    <b>TRUSTLEDGER</b><br><br>
    Paytm knows the payment. TrustLedger knows the trust.
    <br><br>
    <small>
    Hackathon prototype • Trust Score is a behavioural indicator,
    not a loan approval or guarantee.
    </small>
    </div>
    """,
    unsafe_allow_html=True,
)


