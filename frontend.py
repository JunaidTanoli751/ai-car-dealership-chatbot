# frontend.py
import os
import sqlite3
import json
from datetime import datetime

import requests
import streamlit as st
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# ---------- CONFIG ----------
st.set_page_config(
    page_title="🚗 Car Dealer Customer Support",
    page_icon="🚗",
    layout="wide"
)

# Read GEMINI key from environment or Streamlit secrets (if used)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or (st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else None)
GEMINI_URL = os.getenv("GEMINI_URL") or "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"
DB_PATH = os.getenv("DB_PATH", "car_dealership.db")

# ---------- DATABASE helpers ----------
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        role TEXT,
        text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        email TEXT,
        interested_in TEXT,
        budget TEXT,
        status TEXT DEFAULT 'new',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS cars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        make TEXT,
        model TEXT,
        year INTEGER,
        price REAL,
        mileage TEXT,
        fuel_type TEXT,
        transmission TEXT,
        features TEXT,
        status TEXT DEFAULT 'available',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS test_drives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT,
        phone TEXT,
        email TEXT,
        car_model TEXT,
        preferred_date TEXT,
        preferred_time TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS service_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT,
        phone TEXT,
        car_model TEXT,
        service_type TEXT,
        description TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()

    # Insert sample cars if empty
    c.execute("SELECT COUNT(*) FROM cars")
    if c.fetchone()[0] == 0:
        sample_cars = [
            ("Toyota", "Corolla", 2020, 3500000, "45,000 km", "Petrol", "Automatic", "ABS, Airbags, Power Steering, AC, Alloy Rims", "available"),
            ("Honda", "Civic", 2019, 3200000, "52,000 km", "Petrol", "CVT", "Cruise Control, Sunroof, Leather Seats, Navigation", "available"),
            ("Suzuki", "Alto", 2021, 1800000, "25,000 km", "Petrol", "Manual", "AC, Power Windows, Central Lock", "available"),
            ("Honda", "City", 2020, 2800000, "38,000 km", "Petrol", "Automatic", "ABS, Airbags, Alloy Rims, Multimedia", "available"),
            ("Toyota", "Yaris", 2022, 3900000, "15,000 km", "Petrol", "CVT", "Smart Entry, Push Start, Reverse Camera", "available"),
        ]
        c.executemany(
            "INSERT INTO cars (make, model, year, price, mileage, fuel_type, transmission, features, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            sample_cars
        )
        conn.commit()

    conn.close()

def save_message(session_id, role, text):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT INTO messages (session_id, role, text) VALUES (?, ?, ?)", (session_id, role, text))
    conn.commit()
    conn.close()

def get_session_messages(session_id, limit=50):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT role, text, created_at FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?", (session_id, limit))
    data = c.fetchall()
    conn.close()
    return data[::-1]

def get_all_user_sessions():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT DISTINCT session_id FROM messages ORDER BY id DESC")
    data = c.fetchall()
    conn.close()
    return [row[0] for row in data]

def get_user_history_summary(session_id):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM leads WHERE name IN (SELECT DISTINCT text FROM messages WHERE session_id = ?)", (session_id,))
    lead_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM test_drives")
    test_drive_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,))
    message_count = c.fetchone()[0]

    conn.close()
    return {
        "leads": lead_count,
        "test_drives": test_drive_count,
        "messages": message_count
    }

def save_lead(name, phone, email, interested_in, budget, notes=""):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT INTO leads (name, phone, email, interested_in, budget, notes) VALUES (?, ?, ?, ?, ?, ?)",
              (name.strip(), phone.strip(), (email or "").strip(), (interested_in or "").strip(), (budget or "").strip(), (notes or "").strip()))
    conn.commit()
    conn.close()

def save_test_drive(customer_name, phone, email, car_model, preferred_date, preferred_time):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT INTO test_drives (customer_name, phone, email, car_model, preferred_date, preferred_time) VALUES (?, ?, ?, ?, ?, ?)",
              (customer_name.strip(), phone.strip(), (email or "").strip(), car_model.strip(), preferred_date, preferred_time))
    conn.commit()
    conn.close()

def save_service_request(customer_name, phone, car_model, service_type, description):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT INTO service_requests (customer_name, phone, car_model, service_type, description) VALUES (?, ?, ?, ?, ?)",
              (customer_name.strip(), phone.strip(), car_model.strip(), service_type.strip(), (description or "").strip()))
    conn.commit()
    conn.close()

def get_all_cars():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM cars WHERE status = 'available' ORDER BY year DESC")
    data = c.fetchall()
    conn.close()
    return data

def search_cars(query):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    q = f"%{query}%"
    c.execute("""SELECT * FROM cars WHERE status = 'available' AND 
                 (make LIKE ? OR model LIKE ? OR features LIKE ?)""", (q, q, q))
    data = c.fetchall()
    conn.close()
    return data

# ---------- Knowledge base (same as backend) ----------
knowledge_base = {
    "financing": {
        "info": "We offer flexible financing options with 20-30% down payment and up to 5 years installment plans. Interest rates start from 12% per annum.",
        "keywords": ["finance", "loan", "installment", "payment plan", "emi", "down payment"]
    },
    "warranty": {
        "info": "All our cars come with a 3-month dealer warranty covering engine and transmission. Extended warranty packages available for up to 2 years.",
        "keywords": ["warranty", "guarantee", "coverage", "protection"]
    },
    "exchange": {
        "info": "We accept car exchange! Bring your old car and we'll evaluate it for the best exchange value. We handle all documentation.",
        "keywords": ["exchange", "trade-in", "old car", "swap"]
    },
    "service": {
        "info": "Our service center offers: Regular maintenance, Oil changes, Brake services, AC repair, Engine diagnostics, Body work and painting.",
        "keywords": ["service", "maintenance", "repair", "fix", "mechanic"]
    },
    "inspection": {
        "info": "Free pre-purchase inspection available for all cars. Our certified technicians check 150+ points before delivery.",
        "keywords": ["inspection", "check", "evaluate", "condition"]
    },
    "delivery": {
        "info": "Free home delivery within city limits. For outstation delivery, charges apply based on distance.",
        "keywords": ["delivery", "shipping", "transport"]
    },
    "documentation": {
        "info": "We handle all documentation including: Registration transfer, Token tax, Insurance, Number plate transfer. Processing time: 7-14 days.",
        "keywords": ["documents", "registration", "transfer", "paperwork", "token tax"]
    },
    "operating_hours": {
        "info": "We're open Monday to Saturday: 10:00 AM - 8:00 PM, Sunday: 11:00 AM - 6:00 PM. 24/7 support available via phone.",
        "keywords": ["hours", "timing", "open", "close", "schedule"]
    }
}

def search_knowledge_base(query):
    q = query.lower()
    matches = []
    for data in knowledge_base.values():
        for keyword in data["keywords"]:
            if keyword in q:
                matches.append(data["info"])
                break
    return matches

def get_car_details(query):
    cars = search_cars(query)
    if cars:
        details = []
        for car in cars[:3]:
            details.append(f"📌 {car[1]} {car[2]} {car[3]} - PKR {car[4]:,.0f}\n   Mileage: {car[5]} | Fuel: {car[6]} | Transmission: {car[7]}\n   Features: {car[8]}")
        return "\n\n".join(details)
    return None

# ---------- LLM call from frontend (kept for offline/demo usage) ----------
def ask_gemini(user_query, conversation_history=""):
    # prefer not to expose key publicly; this is for local demo only
    if not GEMINI_API_KEY:
        return "⚠️ AI key not configured in frontend. Please configure GEMINI_API_KEY in .env or Streamlit secrets."

    # build prompt
    cars = get_all_cars()
    car_list = "\n".join([f"- {car[1]} {car[2]} {car[3]} (PKR {car[4]:,.0f})" for car in cars[:10]])
    kb_info = "\n".join([f"- {data['info']}" for data in knowledge_base.values()])

    context = f"""You are an expert customer support assistant for a car dealership in Pakistan.

AVAILABLE INVENTORY:
{car_list}

SERVICES & POLICIES:
{kb_info}

YOUR ROLE:
- Help customers find the right car based on their needs and budget
- Answer questions about financing, warranties, services, and policies
- Guide customers to book test drives or schedule service appointments
- Capture lead information when customers show interest
- Be friendly, professional, and helpful
- Use PKR currency format

IMPORTANT:
- If customer asks about a specific car, provide detailed information
- If customer shows interest, encourage them to fill the lead form or book a test drive
- Keep responses concise but informative"""

    kb_matches = search_knowledge_base(user_query)
    car_details = get_car_details(user_query)
    additional_context = ""
    if kb_matches:
        additional_context += "\n\nRELEVANT INFORMATION:\n" + "\n".join(kb_matches)
    if car_details:
        additional_context += "\n\nMATCHING CARS:\n" + car_details

    full_prompt = f"""{context}

{additional_context}

CONVERSATION HISTORY:
{conversation_history}

CUSTOMER QUERY: {user_query}

Provide a helpful, natural response. If you mentioned cars or services, encourage the customer to take the next step (book test drive, fill lead form, etc.)"""

    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    data = {"contents": [{"parts": [{"text": full_prompt}]}]}

    try:
        res = requests.post(GEMINI_URL, headers=headers, params=params, json=data, timeout=12)
        res.raise_for_status()
        body = res.json()
        candidates = body.get("candidates") or []
        if candidates:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if parts:
                response = parts[0].get("text", "")
                if any(word in response.lower() for word in ["interested", "would you like", "shall i", "book", "schedule"]):
                    response += "\n\n💡 _Tip: Use the forms in the sidebar to book a test drive or save your details!_"
                return response
        return "⚠️ Couldn't parse AI response."
    except Exception as e:
        return f"⚠️ I'm having trouble connecting right now. Please try again or call us at: 0300-1234567\n\nError: {e}"

# ---------- Session and UI ----------
if "session_id" not in st.session_state:
    st.session_state.session_id = datetime.now().strftime("%Y%m%d%H%M%S")

if "messages" not in st.session_state:
    st.session_state.messages = []
    history_messages = get_session_messages(st.session_state.session_id, 50)
    for role, msg, *_ in history_messages:
        st.session_state.messages.append({"role": role, "content": msg})

    if not st.session_state.messages:
        welcome = "👋 Welcome to our Car Dealership! I'm your virtual assistant. How can I help you today?\n\n🚗 Browse cars\n💰 Learn about financing\n🔧 Service inquiries\n📅 Book test drive\n\nJust ask me anything!"
        st.session_state.messages.append({"role": "assistant", "content": welcome})

if "show_history_stats" not in st.session_state:
    st.session_state.show_history_stats = False

# Initialize DB locally for frontend (so tables exist if backend not used)
init_db()

# ------- Sidebar -------
with st.sidebar:
    st.header("📋 Quick Actions")

    with st.expander("📜 View Full History", expanded=False):
        all_sessions = get_all_user_sessions()
        st.write(f"**Total Sessions:** {len(all_sessions)}")

        selected_session = st.selectbox(
            "Select Session to View",
            options=[st.session_state.session_id] + [s for s in all_sessions if s != st.session_state.session_id],
            format_func=lambda x: "Current Session" if x == st.session_state.session_id else f"Session {x[:12]}..."
        )

        if st.button("📂 Load Selected Session"):
            if selected_session != st.session_state.session_id:
                st.session_state.session_id = selected_session
                st.session_state.messages = []
                for role, msg, *_ in get_session_messages(selected_session, 50):
                    st.session_state.messages.append({"role": role, "content": msg})
                st.experimental_rerun()

    st.divider()

    with st.expander("💼 Save Your Interest", expanded=False):
        with st.form("lead_form"):
            st.subheader("Lead Information")
            lead_name = st.text_input("Full Name*")
            lead_phone = st.text_input("Phone Number*")
            lead_email = st.text_input("Email Address")
            lead_interest = st.text_input("Interested In (Car Model)")
            lead_budget = st.selectbox("Budget Range", ["Below 2M", "2M - 3M", "3M - 4M", "4M - 5M", "Above 5M"])
            lead_notes = st.text_area("Additional Notes")

            if st.form_submit_button("💾 Save Lead"):
                if lead_name and lead_phone:
                    save_lead(lead_name, lead_phone, lead_email, lead_interest, lead_budget, lead_notes)
                    st.success("✅ Thank you! Our team will contact you soon.")
                else:
                    st.error("❌ Name and Phone are required")

    with st.expander("🚗 Book Test Drive", expanded=False):
        with st.form("test_drive_form"):
            st.subheader("Test Drive Booking")
            td_name = st.text_input("Your Name*")
            td_phone = st.text_input("Phone*")
            td_email = st.text_input("Email")
            td_car = st.text_input("Car Model*")
            td_date = st.date_input("Preferred Date")
            td_time = st.selectbox("Preferred Time", ["10:00 AM", "12:00 PM", "2:00 PM", "4:00 PM", "6:00 PM"])

            if st.form_submit_button("📅 Book Now"):
                if td_name and td_phone and td_car:
                    save_test_drive(td_name, td_phone, td_email, td_car, str(td_date), td_time)
                    st.success("✅ Test drive booked! We'll confirm via phone.")
                else:
                    st.error("❌ All fields with * are required")

    with st.expander("🔧 Request Service", expanded=False):
        with st.form("service_form"):
            st.subheader("Service Request")
            srv_name = st.text_input("Your Name*")
            srv_phone = st.text_input("Phone*")
            srv_car = st.text_input("Car Model*")
            srv_type = st.selectbox("Service Type", ["Regular Maintenance", "Oil Change", "Brake Service", "AC Repair", "Engine Check", "Body Work", "Other"])
            srv_desc = st.text_area("Description")

            if st.form_submit_button("📝 Submit Request"):
                if srv_name and srv_phone and srv_car:
                    save_service_request(srv_name, srv_phone, srv_car, srv_type, srv_desc)
                    st.success("✅ Service request submitted!")
                else:
                    st.error("❌ All fields with * are required")

    st.divider()
    st.info("💬 **Chat with our AI assistant for instant help!**")

    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.experimental_rerun()

# ------- Main -------
st.title("🚗 Car Dealership Customer Support")
st.caption("Ask me anything about our cars, services, financing, or book a test drive!")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat input
if user_input := st.chat_input("Type your question here..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    save_message(st.session_state.session_id, "user", user_input)

    # Build conversation history and ask Gemini (frontend-local)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in st.session_state.messages[-10:]])
            response = ask_gemini(user_input, history)
            st.write(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
    save_message(st.session_state.session_id, "assistant", response)

# Footer
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📞 Contact", "0300-1234567")
with col2:
    st.metric("📍 Location", "Karachi, Pakistan")
with col3:
    st.metric("⏰ Hours", "10 AM - 8 PM")