import os
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv


# ============================================================
# PROJECT PATH
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

# Make project root available so we can import agents/
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


# ============================================================
# ENVIRONMENT
# ============================================================

ENV_PATH = os.path.join(
    BASE_DIR,
    "backend",
    ".env"
)

load_dotenv(ENV_PATH)


# ============================================================
# AGENT IMPORTS
# ============================================================

from agents.operations_agent import process_request

from agents.inventory_agent import (
    check_inventory,
    get_low_stock,
    get_material,
    get_total_stock,
)

# Supply chain pipeline router (Dinuja's component)
from backend.supply_chain.router import supply_chain_router


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="OMNI Operations API",
    description="Operational Multi-Agent Network Intelligence API",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)

# Mount supply chain router under /supply-chain prefix
app.include_router(supply_chain_router, prefix="/supply-chain", tags=["Supply Chain"])


# ============================================================
# REQUEST MODELS
# ============================================================

class AskRequest(BaseModel):
    message: str


class MaterialRequest(BaseModel):
    material_name: str | None = None
    material_code: str | None = None


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "system": "OMNI",
        "message": "OMNI backend is running!",
        "status": "online"
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "system": "OMNI",
        "message": "System healthy",
        "status": "online"
    }


# ============================================================
# OPERATIONS AGENT
# ============================================================

@app.post("/ask")
def ask_agent(request: AskRequest):

    if not request.message.strip():

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty."
        )

    try:

        result = process_request(
            request.message
        )

        return result

    except Exception as error:

        print(
            f"Operations Agent error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Operations Agent failed to process the request."
        )


# ============================================================
# INVENTORY — ALL ITEMS
# ============================================================

@app.get("/inventory")
def inventory():

    try:

        return check_inventory()

    except Exception as error:

        print(
            f"Inventory error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve inventory."
        )


# ============================================================
# INVENTORY — LOW STOCK
# ============================================================

@app.get("/inventory/low-stock")
def low_stock():

    try:

        return get_low_stock()

    except Exception as error:

        print(
            f"Low stock error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve low-stock materials."
        )


# ============================================================
# INVENTORY — SPECIFIC MATERIAL
# ============================================================

@app.post("/inventory/material")
def material(request: MaterialRequest):

    if not request.material_name and not request.material_code:

        raise HTTPException(
            status_code=400,
            detail="Provide material_name or material_code."
        )

    try:

        result = get_material(
            material_name=request.material_name,
            material_code=request.material_code
        )

        if result is None:

            raise HTTPException(
                status_code=404,
                detail="Material not found."
            )

        return result

    except HTTPException:

        raise

    except Exception as error:

        print(
            f"Material lookup error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve material."
        )


# ============================================================
# INVENTORY — TOTAL STOCK
# ============================================================

@app.get("/inventory/total")
def total_stock():

    try:

        return get_total_stock()

    except Exception as error:

        print(
            f"Total stock error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to calculate total stock."
        )