# BFF Architecture Demo

This project demonstrates a Backend For Frontend (BFF) architecture pattern with:

- Backend: FastAPI service handling core business logic
- BFF: FastAPI service handling authentication and proxying requests to the backend
- Frontend: Next.js application with authentication flow

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│             │     │             │     │             │
│  Frontend   │────▶│     BFF     │────▶│   Backend   │
│  (Next.js)  │     │  (FastAPI)  │     │  (FastAPI)  │
│             │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
```

The BFF pattern provides several benefits:
- Handles authentication in a layer between the frontend and backend
- Provides API tailored to the frontend's needs
- Shields backend complexity from the client
- Allows backends to focus on core business logic without authentication concerns

## Setup Instructions

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The backend server will start on http://localhost:8000

### BFF (Backend For Frontend)

```bash
cd bff
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

The BFF server will start on http://localhost:8001

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend server will start on http://localhost:3000

## Usage

1. Open http://localhost:3000 in your browser
2. Click on the Login link
3. Enter any username and password (authentication is mocked for demo)
4. After login, you'll be redirected to the dashboard
5. The dashboard displays the authenticated user info and items fetched from the backend via the BFF

## Implementation Details

- The backend provides a simple API for items without authentication
- The BFF handles authentication using cookies and an in-memory store (Redis would be used in production)
- The BFF proxies requests to the backend after authentication
- The frontend provides a login flow and displays authenticated data

## Authentication Flow

1. User submits credentials to BFF's `/auth/login` endpoint
2. BFF validates credentials (mocked for this demo)
3. BFF creates a session and stores it in memory (would be Redis in production)
4. BFF returns a session cookie to the frontend
5. Frontend includes this cookie in subsequent requests
6. BFF validates the session cookie before proxying requests to the backend

## Production Considerations

For a production environment, consider:

- Using Redis or another distributed store for session data
- Adding HTTPS for all services
- Implementing proper authentication with JWT or OAuth
- Adding rate limiting and additional security measures
- Using Docker for containerization
- Setting up proper monitoring and logging 