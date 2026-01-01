# ai-car-dealership-chatbot
# 🚗 AI Car Dealership Chatbot

An intelligent customer support system for car dealerships powered by Google Gemini 2.0. This system provides 24/7 automated assistance, lead management, test drive booking, and service scheduling.



## 🌟 Features

### 🤖 AI-Powered Chat Assistant
- Natural conversation using Google Gemini 2.0 Flash
- Context-aware responses based on conversation history
- Knowledge base integration for instant answers
- Dynamic car inventory search and recommendations

### 📊 Lead Management
- Automatic lead capture from conversations
- Customer information storage (name, phone, email, budget)
- Interest tracking and notes
- Status management system

### 🚗 Test Drive Booking
- Easy scheduling interface
- Date and time selection
- Email and SMS confirmation ready
- Status tracking (pending/confirmed/completed)

### 🔧 Service Request Management
- Multiple service types (maintenance, repairs, diagnostics)
- Customer and vehicle information capture
- Description and notes field
- Request status tracking

### 💾 Session Management
- Multi-session conversation history
- Session switching capability
- Message persistence across sessions
- Full conversation retrieval

### 📈 Analytics Dashboard
- Real-time statistics
- Lead conversion tracking
- Test drive bookings count
- Message volume metrics

## 🛠️ Tech Stack

### Backend
- **FastAPI** - High-performance REST API framework
- **SQLite** - Lightweight relational database
- **Google Gemini 2.0** - AI language model
- **Python 3.8+** - Core programming language
- **Uvicorn** - ASGI server

### Frontend
- **Streamlit** - Interactive web interface
- **Python Requests** - HTTP client library

### Database Schema
- `messages` - Chat history storage
- `leads` - Customer leads management
- `cars` - Inventory management
- `test_drives` - Booking records
- `service_requests` - Service scheduling

## 📋 Prerequisites

- Python 3.8 or higher
- Google Gemini API key ([Get it here](https://makersuite.google.com/app/apikey))
- pip (Python package manager)

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/ai-car-dealership-chatbot.git
cd ai-car-dealership-chatbot
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_URL=https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent
DB_PATH=car_dealership.db
PORT=8000
```

### 5. Initialize Database
The database will be automatically created on first run with sample car inventory.

## 🎯 Usage

### Option 1: Run Frontend Only (Streamlit)
```bash
streamlit run frontend.py
```
Access at: `http://localhost:8501`

### Option 2: Run Backend API (FastAPI)
```bash
python backend.py
```
API Docs at: `http://localhost:8000/docs`

### Option 3: Run Both (Recommended for Production)
```bash
# Terminal 1 - Backend
python backend.py

# Terminal 2 - Frontend
streamlit run frontend.py
```

## 📡 API Endpoints

### Chat & Messages
- `POST /chat` - Process chat message with AI
- `POST /messages/save` - Save chat message
- `GET /messages/{session_id}` - Get session messages
- `GET /sessions` - Get all sessions

### Lead Management
- `POST /leads` - Create new lead
- `GET /leads` - Get all leads

### Test Drives
- `POST /test-drives` - Book test drive
- `GET /test-drives` - Get all bookings

### Service Requests
- `POST /service-requests` - Create service request
- `GET /service-requests` - Get all requests

### Inventory
- `GET /cars` - Get all available cars
- `POST /cars/search` - Search cars by query

### Analytics
- `GET /stats/{session_id}` - Get session statistics
- `GET /health` - Health check endpoint

## 📁 Project Structure

```
ai-car-dealership-chatbot/
│
├── backend.py              # FastAPI backend server
├── frontend.py             # Streamlit frontend interface
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create this)
├── .env.example           # Example environment file
├── car_dealership.db      # SQLite database (auto-generated)
│
├── README.md              # This file
├── LICENSE                # MIT License
│
└── .gitignore            # Git ignore file
```

## 🎨 Features Showcase

### Knowledge Base Topics
- **Financing** - Payment plans, EMI, down payments
- **Warranty** - Coverage details, extended warranties
- **Exchange** - Trade-in values, documentation
- **Service** - Maintenance, repairs, diagnostics
- **Inspection** - Pre-purchase checks
- **Delivery** - Home delivery options
- **Documentation** - Registration, token tax, insurance
- **Operating Hours** - Showroom timings, contact info

### Sample Car Inventory
The system comes with pre-loaded sample cars:
- Toyota Corolla 2020 - PKR 3,500,000
- Honda Civic 2019 - PKR 3,200,000
- Suzuki Alto 2021 - PKR 1,800,000
- Honda City 2020 - PKR 2,800,000
- Toyota Yaris 2022 - PKR 3,900,000

## 🔐 Security Notes

- **API Keys**: Never commit `.env` file to version control
- **CORS**: Update `allow_origins` in production
- **Database**: Use PostgreSQL for production environments
- **Authentication**: Implement JWT for production APIs
- **Rate Limiting**: Add rate limiting for API endpoints

## 🌍 Localization

Currently supports:
- Pakistani market (PKR currency)
- English language interface
- Local terminology (token tax, registration, etc.)

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 TODO / Roadmap

- [ ] Add user authentication
- [ ] Implement WhatsApp integration
- [ ] Add SMS notifications
- [ ] Create admin dashboard
- [ ] Add payment gateway integration
- [ ] Multi-language support (Urdu, English)
- [ ] Advanced analytics and reporting
- [ ] Mobile app (React Native)
- [ ] Voice assistant integration
- [ ] CRM system integration

## 🐛 Known Issues

- Frontend API key exposure (use backend API in production)
- Limited error handling for network failures
- No user authentication system
- Session management could be improved

#

## 👨‍💻 Author

JUNAID TANOLI



## 📞 Support

For support, email your junaidtanoli751.com or open an issue on GitHub.

---

⭐ If you find this project useful, please consider giving it a star!

**Made with ❤️ for the automotive industry**
