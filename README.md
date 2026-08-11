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
   # Add your OpenAI API key or other LLM provider keys here if needed
   ```

6. **Run the FastAPI server:**
   ```powershell
   # Run the server using uvicorn directly from the root
   uvicorn backend.main:app --reload
   ```
   *The backend will be available at `http://localhost:8000`*

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

---

## Core Technologies

- **FastAPI**: High-performance backend API framework.
- **LangGraph & LangChain**: For building stateful, multi-actor AI agent workflows.
- **FastMCP**: Model Context Protocol integration.
- **WebSockets**: For real-time bi-directional communication between the agents and the frontend.
- **MongoDB**: NoSQL database for flexible data storage.
