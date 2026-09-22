# OMNI: Operational Multi-agent Network Intelligence

Welcome to **OMNI**! This project is an intelligent, multi-agent network designed to automate and orchestrate operational workflows (such as inventory management and analysis) using state-of-the-art AI frameworks like LangGraph, FastMCP, and LangChain.

## Project Structure

- `agents/`: Contains the logic for intelligent AI agents (e.g., Inventory Agent) powered by LangGraph and FastMCP.
- `backend/`: Python backend powered by FastAPI, handling API routes and WebSocket connections.
- `database/`: Database configurations and scripts (MongoDB).
- `frontend/`: Frontend application (e.g., React + Vite).
- `knowledge/`: Documentation and knowledge base for the agents.

## Getting Started

### Prerequisites

- **Node.js** (v18+)
- **Python** (v3.10+)
- **MongoDB** (Local instance or Atlas Cluster)

---

### Backend Setup

1. **Navigate to the project root:**
   ```powershell
   cd OMNI---Operational-Multi-agent-Network-Intelligence
   ```

2. **Create a virtual environment:**
   ```powershell
   python -m venv venv
   ```

3. **Activate the virtual environment:**
   - **Windows:** `.\venv\Scripts\activate`
   - **Linux/macOS:** `source venv/bin/activate`

4. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

5. **Environment Variables:**
   Create a `.env` file in the `backend` directory (e.g., `backend/.env`) and add your required environment variables:
   ```env
   MONGO_URI="your_mongodb_connection_string"
   # Recommended for stable authentication tokens across deployments.
   AUTH_SECRET="generate-a-long-random-secret"
   AUTH_TOKEN_TTL_HOURS=12
   # Browser origin allowed to send cookie-authenticated requests
   FRONTEND_ORIGIN=http://localhost:5173
   # Set true when serving through HTTPS
   COOKIE_SECURE=false
   # Optional SMTP settings used for operational notifications
   BREVO_SMTP_HOST=smtp-relay.brevo.com
   BREVO_SMTP_PORT=587
   BREVO_SMTP_USER="..."
   BREVO_SMTP_PASS="..."
   SENDER_EMAIL="..."
   # Add your OpenAI API key or other LLM provider keys here if needed
   ```

   When `AUTH_SECRET` is omitted, OMNI creates a persistent signing secret in the MongoDB `system_config` collection. Set your own secret for production and keep it out of source control.

6. **Run the FastAPI server:**
   ```powershell
   # Run the server using uvicorn directly from the root
   uvicorn backend.main:app --reload
   ```
   *The backend will be available at `http://localhost:8000`*

7. **Build the local knowledge indexes (first setup or after changing source documents):**
   ```powershell
   python knowledge/build_index.py
   python knowledge/supply_chain/rag/chroma_setup.py
   ```
   The first command indexes production and market documents. The second indexes supplier contract PDFs used for compliance evidence. The readiness endpoint reports whether MongoDB, SQLite, Chroma, the LLM provider, and email are available.

---

### Frontend Setup

1. **Navigate to the frontend directory:**
   ```powershell
   cd frontend
   ```

2. **Install dependencies:**
   ```powershell
   npm install
   ```

3. **Run the development server:**
   ```powershell
   npm run dev
   ```
   *The frontend will be available at the local URL provided by Vite.*

### User accounts

Open the frontend and select **Create account**. Accounts are stored in the MongoDB `users` collection. Passwords are stored as salted PBKDF2 hashes; the original password is never stored. After signing in, the backend sets an HTTP-only session cookie and checks the browser origin on state-changing requests. The first account is a manager; later accounts start as viewers. Managers can change roles from the user-management endpoint. **Sign out** clears the session cookie and revokes the user's existing tokens.

### MCP architecture

The active top-level [Operations supervisor](docs/operations_supervisor.md)
uses a bounded LangGraph plan/act/observe/replan loop. It delegates specialist
evidence gathering through MCP and keeps procurement approvals in the existing
authenticated workflow.

OMNI uses LangGraph to route work and maintain workflow state. Agents access operational tools through three MCP servers:

- **Factory Operations MCP:** inventory, demand forecasting, production planning, and management reports backed by MongoDB.
- **ERP MCP:** supplier lookup and purchase-order operations backed by the local demonstration ERP database.
- **TMS MCP:** carrier, shipment booking, and tracking operations backed by the local demonstration TMS database.

The Factory Operations server uses FastMCP's in-memory transport when called by the local backend, so no additional process is required during normal startup. It can also run as a standalone stdio MCP server:

```powershell
python -m backend.mcp.factory_operations.server
```

See [`mcp_architecture.md`](mcp_architecture.md) for the tool boundaries and communication flow.

---

## Core Technologies

- **FastAPI**: High-performance backend API framework.
- **LangGraph & LangChain**: For building stateful, multi-actor AI agent workflows.
- **FastMCP**: Model Context Protocol integration.
- **WebSockets**: For real-time bi-directional communication between the agents and the frontend.
- **MongoDB**: NoSQL database for flexible data storage.
