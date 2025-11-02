import os
import re
import json
from datetime import date
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel, Field

import google.auth
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession
from google.api_core import exceptions as gax

from vertexai import init as vertex_init
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig

# ---------- ENV & APP ----------
load_dotenv()

PROJECT_ID = os.getenv("VERTEX_PROJECT", os.getenv("PROJECT_ID", "documind-474412"))
LOCATION = os.getenv("VERTEX_LOCATION", os.getenv("LOCATION", "us-central1"))
MODEL_NAME = os.getenv("VERTEX_MODEL", os.getenv("MODEL_NAME", "gemini-2.0-flash-001"))
GOOGLE_CREDENTIALS_JSON_CONTENT = os.getenv("GOOGLE_CREDENTIALS_JSON_CONTENT")
FRONTEND_URL = os.getenv("FRONTEND_URL")

app = FastAPI(title="DocuMind – Vertex AI Diagnostics (REST)")  # We can change this title later

# ---------- CORS MIDDLEWARE CONFIGURATION ----------
origins = [
    "http://localhost:5173",
]
if FRONTEND_URL:
    origins.append(FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------

# --- Unified Credentials Helper Function ---
def _get_credentials():
    """
    Get Google credentials.
    In production (Vercel), read from GOOGLE_CREDENTIALS_JSON_CONTENT.
    In development (local), use the GOOGLE_APPLICATION_CREDENTIALS file path.
    """
    if GOOGLE_CREDENTIALS_JSON_CONTENT:
        # Running in production (Vercel)
        try:
            creds_info = json.loads(GOOGLE_CREDENTIALS_JSON_CONTENT)
            return service_account.Credentials.from_service_account_info(creds_info)
        except Exception as e:
            print(f"Error loading credentials from env var: {e}")
            return None
    else:
        # Running locally
        try:
            creds, _ = google.auth.default()
            return creds
        except Exception as e:
            print(f"Error loading credentials from local ADC: {e}")
            return None


# ------------------------------------

# ---------- HELPERS ----------
# ... (All helper functions: _get_authorized_session, _safe_text, _first_json_object, etc.
# ... remain exactly the same) ...
def _get_authorized_session():
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    creds = _get_credentials()
    if creds and hasattr(creds, "with_scopes"):
        creds = creds.with_scopes(scopes)
    if not creds:
        raise HTTPException(status_code=500, detail="Could not load Google credentials")
    return AuthorizedSession(creds)


def _safe_text(resp):
    try:
        return resp.json()
    except Exception:
        try:
            return resp.text
        except Exception:
            return "<no-body>"


def _first_json_object(s: str) -> Optional[str]:
    if not s:
        return None
    t = s.strip()
    t = re.sub(r"^```json\s*|^```\s*|```$", "", t, flags=re.IGNORECASE | re.MULTILINE).strip()
    t = re.sub(r"^json\s*", "", t, flags=re.IGNORECASE)
    start = t.find("{")
    if start == -1:
        return None
    depth = 0
    for i, ch in enumerate(t[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return t[start: i + 1]
    return None


def _coerce_amount(v) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace(" ", "").replace("\u00A0", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _coerce_date_yyyy_mm_dd(s: Optional[str]) -> Optional[date]:
    if not s or not isinstance(s, str):
        return None
    t = s.strip()
    m = re.match(r"^(\d{2})[./-](\d{2})[./-](\d{4})$", t)
    if m:
        dd, mm, yyyy = m.groups()
        t = f"{yyyy}-{mm}-{dd}"
    m2 = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", t)
    if not m2:
        return None
    try:
        y, mth, d = map(int, m2.groups())
        return date(y, mth, d)
    except ValueError:
        return None


# ---------- SCHEMAS ----------
class InvoiceExtraction(BaseModel):
    vendor: Optional[str] = Field(None, description="Supplier or company name")
    invoice_date: Optional[date] = Field(None, description="YYYY-MM-DD")
    total_amount: Optional[float] = Field(None, description="Total amount")
    currency: Optional[str] = Field(None, description="ISO 4217 code")
    invoice_number: Optional[str] = Field(None, description="Invoice number")
    rawText: Optional[str] = Field(None, description="Raw model output if parsing failed")


# ---------- DIAGNOSTIC ENDPOINTS ----------
# ... (All diagnostic endpoints: /health, /whoami, /check-model, etc.
# ... remain exactly the same) ...
@app.get("/health")
def health():
    return {"project": PROJECT_ID, "location": LOCATION, "model": MODEL_NAME}


@app.get("/whoami")
def whoami():
    try:
        creds = _get_credentials()
        email = getattr(creds, "_service_account_email", None) or getattr(creds, "service_account_email", None)
        return {"adc_project": PROJECT_ID, "sa_email": email}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": type(e).__name__, "detail": str(e)})


@app.get("/check-model")
def check_model():
    session = _get_authorized_session()
    url = (
        f"https://{LOCATION}[-aiplatform.googleapis.com/v1/](https://-aiplatform.googleapis.com/v1/)"
        f"projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL_NAME}"
    )
    resp = session.get(url)
    if resp.status_code == 200:
        data = resp.json()
        return {"found": True, "display_name": data.get("displayName"), "name": data.get("name"), "raw": data}
    # ... (error handling 404, 403, 500 remains the same) ...
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "..."}, )
    if resp.status_code == 403:
        raise HTTPException(status_code=403, detail={"error": "PERMISSION_DENIED", "message": "..."}, )
    raise HTTPException(status_code=500, detail={"error": "UPSTREAM_ERROR", "status_code": resp.status_code, "url": url,
                                                 "response": _safe_text(resp)}, )


@app.get("/list-models")
def list_models(prefix: Optional[str] = Query("gemini")):
    # ... (function content remains the same) ...
    session = _get_authorized_session()
    base = (
        f"https://{LOCATION}[-aiplatform.googleapis.com/v1/projects/](https://-aiplatform.googleapis.com/v1/projects/){PROJECT_ID}/locations/{LOCATION}/publishers/google/models")
    page_token: Optional[str] = None
    seen: List[Dict[str, Any]] = []
    while True:
        url = base + (f"?pageToken={page_token}" if page_token else "")
        resp = session.get(url)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code,
                                detail={"error": "UPSTREAM_ERROR", "response": _safe_text(resp)})
        data = resp.json()
        for m in data.get("models", []):
            name = m.get("name", "")
            display = m.get("displayName", "")
            if not prefix or prefix.lower() in name.lower() or prefix.lower() in display.lower():
                seen.append({"name": name, "displayName": display})
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return {"project": PROJECT_ID, "location": LOCATION, "count": len(seen), "models": seen}


@app.get("/ping-model")
def ping_model():
    # ... (function content remains the same) ...
    try:
        creds = _get_credentials()
        if not creds:
            raise Exception("Could not load Google credentials for Vertex AI")
        vertex_init(project=PROJECT_ID, location=LOCATION, credentials=creds)
        model = GenerativeModel(MODEL_NAME)
        result = model.generate_content("Say 'pong' in one word.")
        return {"reply": getattr(result, "text", None)}
    except gax.NotFound as e:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "detail": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": type(e).__name__, "detail": str(e)})


# ---------- BUSINESS ENDPOINT ----------

# The "Whitelist" is now only for PDF.
SUPPORTED_MIME_TYPE = "application/pdf"


@app.post("/invoices/extract", response_model=InvoiceExtraction)
async def extract_invoice(file: UploadFile = File(...)):
    """Upload a PDF and extract invoice fields as JSON (robust parsing)."""

    mime = file.content_type
    print(f"--- Received file: {file.filename}, MIME Type: {mime} ---")

    # --- Strict PDF-only Validation Logic ---
    if not mime or mime != SUPPORTED_MIME_TYPE:
        raise HTTPException(
            status_code=415,  # 415 means "Unsupported Media Type"
            detail=f"Unsupported file type: {mime}. Only application/pdf is allowed."
        )
    # ------------------------------------

    content = await file.read()

    creds = _get_credentials()
    if not creds:
        raise HTTPException(status_code=500, detail="Could not load Google credentials for Vertex AI")
    vertex_init(project=PROJECT_ID, location=LOCATION, credentials=creds)

    model = GenerativeModel(MODEL_NAME)

    doc_part = Part.from_data(data=content, mime_type=mime)
    prompt = (
        "You are an information extraction system for invoices. "
        "Analyze the PDF document and return ONLY a JSON object with exactly these keys: "
        '{"vendor": string|null, "invoice_date": string (YYYY-MM-DD)|null, '
        '"total_amount": number|null, "currency": string|null, "invoice_number": string|null}.'
    )

    cfg = GenerationConfig(response_mime_type="application/json")

    text = ""  # Initialize text variable
    try:
        print("--- Attempting to call model.generate_content ---")
        try:
            resp = model.generate_content([prompt, doc_part], generation_config=cfg)
            text = getattr(resp, "text", "") or ""
            print(f"Raw response from Gemini: {text}")
        except Exception as e:
            print(f"!!! GEMINI CALL FAILED: {type(e).__name__} - {e}")
            raise

        # ... (The rest of the JSON parsing logic remains the same) ...
        data: Any
        try:
            data = json.loads(text)
        except Exception:
            obj = _first_json_object(text)
            if not obj:
                return InvoiceExtraction(rawText=text)
            data = json.loads(obj)

        if isinstance(data, list):
            data = data[0] if data else {}

        for k in ["vendor", "invoice_date", "total_amount", "currency", "invoice_number"]:
            data.setdefault(k, None)

        data["total_amount"] = _coerce_amount(data.get("total_amount"))
        data["invoice_date"] = _coerce_date_yyyy_mm_dd(data.get("invoice_date"))

        return InvoiceExtraction(**data)

    except Exception as e:
        print(f"--- Error during processing: {e} ---")
        try:
            return InvoiceExtraction(rawText=text)
        except Exception:
            return InvoiceExtraction(rawText=str(e))


# ---------- MAIN ----------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)