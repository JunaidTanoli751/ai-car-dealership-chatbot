# backend.py
import os
import logging
from datetime import datetime
from typing import Optional, List

import requests
import sqlite3
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from requests.adapters import HTTPAdapter, Retry
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# ---------- CONFIG ----------
logger = logging.getLogger("car_dealership_api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="Car Dealership API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY")
GEMINI_URL = os.getenv("GEMINI_URL") or "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"

# ---------- Pydantic Models ----------
class Message(BaseModel):
    session_id: str
    role: str
    text: str

class ChatRequest(BaseModel):
    session_id: str
    user_message: str
    history: Optional[List[dict]] = []

class Lead(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    interested_in: Optional[str] = None
    budget: Optional[str] = None
    notes: Optional[str] = None

class TestDrive(BaseModel):
    customer_name: str
    phone: str
    email: Optional[str] = None
    car_model: str
    preferred_date: str
    preferred_time: str

class ServiceRequest(BaseModel):
    customer_name: str
    phone: str
    car_model: str
    service_type: str
    description: Optional[str] = None

class CarSearch(BaseModel):
    query: str

# ---------- Database helpers ----------
DB_PATH = os.getenv("DB_PATH", "car_dealership.db")

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
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

@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("Database initialized")

# ---------- Knowledge base ----------
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

def search_knowledge_base(query: str):
    query_lower = query.lower()
    matches = []
    for data in knowledge_base.values():
        for keyword in data["keywords"]:
            if keyword in query_lower:
                matches.append(data["info"])
                break
    return matches

# ---------- HTTP session with retries ----------
def get_requests_session():
    session = requests.Session()
    retries = Retry(total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

# ---------- API endpoints ----------
@app.get("/")
async def root():
    return {"message": "Car Dealership API is running!", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/messages/save")
async def save_message(message: Message):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO messages (session_id, role, text) VALUES (?, ?, ?)",
                  (message.session_id, message.role, message.text))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Message saved"}
    except Exception as e:
        logger.exception("Failed to save message")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/messages/{session_id}")
async def get_messages(session_id: str, limit: int = 50):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT role, text, created_at FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                  (session_id, limit))
        messages = [{"role": row[0], "text": row[1], "created_at": row[2]} for row in c.fetchall()]
        conn.close()
        return {"messages": messages[::-1]}
    except Exception as e:
        logger.exception("Failed to get messages")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions")
async def get_all_sessions():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT DISTINCT session_id FROM messages ORDER BY id DESC")
        sessions = [row[0] for row in c.fetchall()]
        conn.close()
        return {"sessions": sessions}
    except Exception as e:
        logger.exception("Failed to get sessions")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Process chat request: search KB, search cars, build prompt and call Gemini.
    """
    try:
        # Search knowledge base and cars while DB connection is open
        kb_matches = search_knowledge_base(request.user_message)

        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT * FROM cars WHERE status = 'available' AND 
                     (make LIKE ? OR model LIKE ? OR features LIKE ?)""",
                  (f'%{request.user_message}%', f'%{request.user_message}%', f'%{request.user_message}%'))
        cars = c.fetchall()

        # Also build inventory snapshot (limit 10)
        c.execute("SELECT * FROM cars WHERE status = 'available' ORDER BY year DESC LIMIT 10")
        all_cars = c.fetchall()
        conn.close()

        car_details = ""
        if cars:
            car_list = []
            for car in cars[:3]:
                car_list.append(f"📌 {car['make']} {car['model']} {car['year']} - PKR {car['price']:,.0f}\n   Mileage: {car['mileage']} | Fuel: {car['fuel_type']} | Transmission: {car['transmission']}\n   Features: {car['features']}")
            car_details = "\n\n".join(car_list)

        car_inventory = "\n".join([f"- {car['make']} {car['model']} {car['year']} (PKR {car['price']:,.0f})" for car in all_cars])

        kb_info = "\n".join([f"- {data['info']}" for data in knowledge_base.values()])

        context = f"""You are an expert customer support assistant for a car dealership in Pakistan.

AVAILABLE INVENTORY:
{car_inventory}

SERVICES & POLICIES:
{kb_info}

YOUR ROLE:
- Help customers find the right car based on their needs and budget
- Answer questions about financing, warranties, services, and policies
- Guide customers to book test drives or schedule service appointments
- Be friendly, professional, and helpful
- Use PKR currency format

IMPORTANT:
- Keep responses concise but informative
- If customer shows interest, encourage them to take action"""

        additional_context = ""
        if kb_matches:
            additional_context += "\n\nRELEVANT INFORMATION:\n" + "\n".join(kb_matches)
        if car_details:
            additional_context += "\n\nMATCHING CARS:\n" + car_details

        history_text = "\n".join([f"{msg.get('role')}: {msg.get('content')}" for msg in request.history[-10:]]) if request.history else ""

        full_prompt = f"""{context}

{additional_context}

CONVERSATION HISTORY:
{history_text}

CUSTOMER QUERY: {request.user_message}

Provide a helpful, natural response."""

        # Call Gemini API
        if not GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set")
            # Fallback generic message
            return {"response": "⚠️ AI service not configured. Please contact support at 0300-1234567."}

        session = get_requests_session()
        headers = {"Content-Type": "application/json"}
        params = {"key": GEMINI_API_KEY}
        data = {"contents": [{"parts": [{"text": full_prompt}]}]}

        try:
            res = session.post(GEMINI_URL, headers=headers, params=params, json=data, timeout=12)
            res.raise_for_status()
            body = res.json()
            # Safely extract response text
            response_text = ""
            candidates = body.get("candidates") or []
            if candidates and isinstance(candidates, list):
                candidate = candidates[0]
                content = candidate.get("content") or {}
                parts = content.get("parts") or []
                if parts and isinstance(parts, list):
                    part = parts[0]
                    response_text = part.get("text", "")
            if not response_text:
                # fallback
                response_text = "⚠️ Sorry, I couldn't generate a response. Please try again or call 0300-1234567."
        except Exception as e:
            logger.exception("Gemini API call failed")
            response_text = "⚠️ I'm having trouble right now. Please try again or call us at: 0300-1234567"

        # Suggest action if intent present
        if any(word in response_text.lower() for word in ["interested", "would you like", "book", "schedule", "test drive"]):
            response_text += "\n\n💡 _Use the forms in the sidebar to book or save your details!_"

        return {"response": response_text}

    except Exception as e:
        logger.exception("Chat endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error")

# ---------- Leads, Test Drives, Services, Cars, Stats ----------
@app.post("/leads")
async def create_lead(lead: Lead):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO leads (name, phone, email, interested_in, budget, notes) VALUES (?, ?, ?, ?, ?, ?)",
                  (lead.name.strip(), lead.phone.strip(), (lead.email or "").strip(), (lead.interested_in or "").strip(), (lead.budget or "").strip(), (lead.notes or "").strip()))
        conn.commit()
        lead_id = c.lastrowid
        conn.close()
        return {"status": "success", "message": "Lead created", "lead_id": lead_id}
    except Exception as e:
        logger.exception("Failed to create lead")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/leads")
async def get_leads():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM leads ORDER BY id DESC")
        leads = [dict(row) for row in c.fetchall()]
        conn.close()
        return {"leads": leads}
    except Exception as e:
        logger.exception("Failed to get leads")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test-drives")
async def create_test_drive(test_drive: TestDrive):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO test_drives (customer_name, phone, email, car_model, preferred_date, preferred_time) VALUES (?, ?, ?, ?, ?, ?)",
                  (test_drive.customer_name.strip(), test_drive.phone.strip(), (test_drive.email or "").strip(), test_drive.car_model.strip(), test_drive.preferred_date.strip(), test_drive.preferred_time.strip()))
        conn.commit()
        td_id = c.lastrowid
        conn.close()
        return {"status": "success", "message": "Test drive booked", "test_drive_id": td_id}
    except Exception as e:
        logger.exception("Failed to create test drive")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test-drives")
async def get_test_drives():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM test_drives ORDER BY id DESC")
        test_drives = [dict(row) for row in c.fetchall()]
        conn.close()
        return {"test_drives": test_drives}
    except Exception as e:
        logger.exception("Failed to get test drives")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/service-requests")
async def create_service_request(service: ServiceRequest):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO service_requests (customer_name, phone, car_model, service_type, description) VALUES (?, ?, ?, ?, ?)",
                  (service.customer_name.strip(), service.phone.strip(), service.car_model.strip(), service.service_type.strip(), (service.description or "").strip()))
        conn.commit()
        sr_id = c.lastrowid
        conn.close()
        return {"status": "success", "message": "Service request created", "service_request_id": sr_id}
    except Exception as e:
        logger.exception("Failed to create service request")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/service-requests")
async def get_service_requests():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM service_requests ORDER BY id DESC")
        services = [dict(row) for row in c.fetchall()]
        conn.close()
        return {"service_requests": services}
    except Exception as e:
        logger.exception("Failed to get service requests")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cars")
async def get_all_cars():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM cars WHERE status = 'available' ORDER BY year DESC")
        cars = [dict(row) for row in c.fetchall()]
        conn.close()
        return {"cars": cars}
    except Exception as e:
        logger.exception("Failed to get cars")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cars/search")
async def search_cars(search: CarSearch):
    try:
        conn = get_db()
        c = conn.cursor()
        q = f"%{search.query}%"
        c.execute("""SELECT * FROM cars WHERE status = 'available' AND 
                     (make LIKE ? OR model LIKE ? OR features LIKE ?)""", (q, q, q))
        cars = [dict(row) for row in c.fetchall()]
        conn.close()
        return {"cars": cars}
    except Exception as e:
        logger.exception("Failed to search cars")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats/{session_id}")
async def get_stats(session_id: str):
    try:
        conn = get_db()
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,))
        message_count = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM test_drives")
        test_drive_count = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM leads")
        lead_count = c.fetchone()[0]

        conn.close()

        return {
            "messages": message_count,
            "test_drives": test_drive_count,
            "leads": lead_count
        }
    except Exception as e:
        logger.exception("Failed to get stats")
        raise HTTPException(status_code=500, detail=str(e))

# Run server
if __name__ == "__main__":
    uvicorn.run("backend:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
