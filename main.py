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
from google.auth.transport.requests import AuthorizedSession
from google.api_core import exceptions as gax

from vertexai import init as vertex_init
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig

# ---------- ENV & APP ----------
load_dotenv()

PROJECT_ID = os.getenv("VERTEX_PROJECT", os.getenv("PROJECT_ID", "documind-474412"))
LOCATION = os.getenv("VERTEX_LOCATION", os.getenv("LOCATION", "us-central1"))
MODEL_NAME = os.getenv("VERTEX_MODEL", os.getenv("MODEL_NAME", "gemini-2.0-flash-001"))

app = FastAPI(title="DocuMind – Vertex AI Diagnostics (REST)")

# ---------- CORS MIDDLEWARE CONFIGURATION ----------
# This is the "guest list" that allows the frontend to make requests.
origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, etc.)
    allow_headers=["*"], # Allows all headers.
)
# ----------------------------------------------------

# ---------- HELPERS ----------
def _get_authorized_session():
    """Create an AuthorizedSession using ADC (respects GOOGLE_APPLICATION_CREDENTIALS)."""
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    creds, _ = google.auth.default(scopes=scopes)
    return AuthorizedSession(creds)

def _safe_text(resp):
    """Return JSON body if possible, otherwise raw text."""
    try:
        return resp.json()
    except Exception:
        try:
            return resp.text
        except Exception:
            return "<no-body>"

def _first_json_object(s: str) -> Optional[str]:
    """Extract first top-level {...} JSON object; tolerates ```json fences or 'json' prefix."""
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
                return t[start : i + 1]
    return None

def _coerce_amount(v) -> Optional[float]:
    """Normalize numbers like '49,00' → 49.0."""
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
    """Accept 'dd.mm.yyyy' or 'yyyy-mm-dd' and return date."""
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
@app.get("/health")
def health():
    return {"project": PROJECT_ID, "location": LOCATION, "model": MODEL_NAME}

@app.get("/whoami")
def whoami():
    try:
        creds, proj = google.auth.default()
        email = getattr(creds, "_service_account_email", None) or getattr(creds, "service_account_email", None)
        return {"adc_project": proj, "sa_email": email}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": type(e).__name__, "detail": str(e)})

@app.get("/check-model")
def check_model():
    session = _get_authorized_session()
    url = (
        f"https://{LOCATION}-aiplatform.googleapis.com/v1/"
        f"projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL_NAME}"
    )
    resp = session.get(url)
    if resp.status_code == 200:
        data = resp.json()
        return {"found": True, "display_name": data.get("displayName"), "name": data.get("name"), "raw": data}
    if resp.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "NOT_FOUND",
                "message": "Publisher model not found or project lacks access in this region.",
                "url": url,
                "response": _safe_text(resp),
            },
        )
    if resp.status_code == 403:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "PERMISSION_DENIED",
                "message": "Permission denied. Ensure roles/aiplatform.user on the Service Account.",
                "url": url,
                "response": _safe_text(resp),
            },
        )
    raise HTTPException(
        status_code=500,
        detail={"error": "UPSTREAM_ERROR", "status_code": resp.status_code, "url": url, "response": _safe_text(resp)},
    )

@app.get("/list-models")
def list_models(prefix: Optional[str] = Query("gemini", description="Filter by name/displayName prefix")):
    session = _get_authorized_session()
    base = (
        f"https://{LOCATION}-aiplatform.googleapis.com/v1/"
        f"projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models"
    )
    page_token: Optional[str] = None
    seen: List[Dict[str, Any]] = []
    while True:
        url = base + (f"?pageToken={page_token}" if page_token else "")
        resp = session.get(url)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail={"error": "UPSTREAM_ERROR", "response": _safe_text(resp)})
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
    try:
        vertex_init(project=PROJECT_ID, location=LOCATION)
        model = GenerativeModel(MODEL_NAME)
        result = model.generate_content("Say 'pong' in one word.")
        return {"reply": getattr(result, "text", None)}
    except gax.NotFound as e:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "detail": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": type(e).__name__, "detail": str(e)})

# ---------- BUSINESS ENDPOINT ----------
@app.post("/invoices/extract", response_model=InvoiceExtraction)
async def extract_invoice(file: UploadFile = File(...)):
    """Upload a PDF/image and extract invoice fields as JSON (robust parsing)."""
    content = await file.read()
    mime = file.content_type or "application/pdf"

    vertex_init(project=PROJECT_ID, location=LOCATION)
    model = GenerativeModel(MODEL_NAME)

    doc_part = Part.from_data(data=content, mime_type=mime)
    prompt = (
        "You are an information extraction system for invoices. "
        "Return ONLY a JSON object with exactly these keys: "
        '{"vendor": string|null, "invoice_date": string (YYYY-MM-DD)|null, '
        '"total_amount": number|null, "currency": string|null, "invoice_number": string|null}.'
    )
    cfg = GenerationConfig(response_mime_type="application/json")

    try:
        resp = model.generate_content([prompt, doc_part], generation_config=cfg)
        text = getattr(resp, "text", "") or ""

        # Try direct JSON
        data: Any
        try:
            data = json.loads(text)
        except Exception:
            obj = _first_json_object(text)
            if not obj:
                return InvoiceExtraction(rawText=text)
            data = json.loads(obj)

        # If model returned a list, take the first dict
        if isinstance(data, list):
            data = data[0] if data else {}

        # Ensure all keys exist
        for k in ["vendor", "invoice_date", "total_amount", "currency", "invoice_number"]:
            data.setdefault(k, None)

        # Coerce fields
        data["total_amount"] = _coerce_amount(data.get("total_amount"))
        data["invoice_date"] = _coerce_date_yyyy_mm_dd(data.get("invoice_date"))

        return InvoiceExtraction(**data)

    except Exception as e:
        # Return raw text or error string to help debugging
        try:
            return InvoiceExtraction(rawText=text)  # type: ignore[name-defined]
        except Exception:
            return InvoiceExtraction(rawText=str(e))

# ---------- MAIN ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
