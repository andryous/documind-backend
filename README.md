# DocuMind - Backend API

![Python](https://img.shields.io/badge/Python-3.11.9-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.118.1-green?style=flat-square)
![Vertex AI](https://img.shields.io/badge/Vertex_AI-1.71.1-orange?style=flat-square)

An intelligent API for extracting structured data from invoices (PDF/Image) using Google's Gemini AI.

## ► Key Features

* **AI-Powered Extraction:** Uses Google Cloud Vertex AI (Gemini) to analyze the visual content of PDF and image documents.
* **Structured Data Output:** Converts unstructured documents into a clean, predictable JSON response.
* **Robust Data Cleansing:** Includes helper functions to automatically normalize common formats (e.g., `dd.mm.yyyy` dates and `,`-based currency).
* **Diagnostic Tools:** Built with endpoints (`/health`, `/ping-model`) to verify system health and cloud connectivity.

## ► Tech Stack

* **Backend:** Python 3.11, FastAPI
* **AI:** Google Cloud Vertex AI (Gemini)
* **Data Validation:** Pydantic
* **Server:** Uvicorn

## ► Getting Started

### 1. Prerequisites

* Python 3.11+
* A Google Cloud project with the Vertex AI API enabled.
* A Google Cloud Service Account `credentials.json` file.

### 2. Clone & Install Dependencies

```bash
# Clone the repository
git clone [https://github.com/andryous/documind-backend.git](https://github.com/andryous/documind-backend.git)
cd documind-backend

# (Recommended) Create and activate a virtual environment
python -m venv .venv
# On Windows
.\.venv\Scripts\activate

# Install dependencies from the clean requirements file
pip install -r requirements.txt
```

### 3. Environment Configuration
This project requires a .env file for secure connection to Google Cloud.
Create a file named .env in the root of the project.
Add the following variables:

## Full path to your Google Cloud credentials file
GOOGLE_APPLICATION_CREDENTIALS="C:/path/to/your/credentials.json" 

## Your Google Cloud project details
VERTEX_PROJECT="documind-474412"
VERTEX_LOCATION="us-central1"
VERTEX_MODEL="gemini-2.0-flash-001"