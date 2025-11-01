# DocuMind - Backend API

![Python](https://img.shields.io/badge/Python-3.11.9-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.118.1-green?style=flat-square)
![Vertex AI](https://img.shields.io/badge/Vertex_AI-1.71.1-orange?style=flat-square)
![Vercel](https://img.shields.io/badge/Deployed%20with-Vercel-black?style=flat-square)

An intelligent API for extracting structured data from invoices (PDF/Image) using Google's Gemini AI. Built with FastAPI and ready for serverless deployment on Vercel.

## ► Key Features

* **AI-Powered Extraction:** Uses Google Cloud Vertex AI (Gemini) to analyze the visual content of PDF and image documents.
* **Structured Data Output:** Converts unstructured documents into a clean, predictable JSON response validated by Pydantic.
* **Robust Data Cleansing:** Includes helper functions to automatically normalize common formats (e.g., `dd.mm.yyyy` dates and `,`-based currency).
* **Dual-Environment Credentials:** Securely handles Google Cloud credentials for both local development (using a file path) and Vercel production (using an environment variable).
* **Serverless Ready:** Configured with a `vercel.json` for easy deployment as a Vercel Function.

## ► Tech Stack

* **Backend:** Python 3.11, FastAPI
* **AI:** Google Cloud Vertex AI (Gemini)
* **Data Validation:** Pydantic
* **Deployment:** Vercel

## ► Local Development

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
This project requires a .env file for local development.
Create a file named .env in the root of the project.

Add the following variables (replace with your values):
## Full path to your Google Cloud credentials file 
## This path is used by google.auth.default()
GOOGLE_APPLICATION_CREDENTIALS="C:/path/to/your/credentials.json"

## Your Google Cloud project details
VERTEX_PROJECT="documind-474412"
VERTEX_LOCATION="us-central1"
VERTEX_MODEL="gemini-2.0-flash-001"

### 4. Run the Application
```bash
uvicorn main:app --reload
```

The application will start on http://localhost:8000.

## ► API Endpoint
The API exposes a single endpoint for invoice extraction.

URL: POST /invoices/extract
Body: multipart/form-data

Key: file

Value: The (PDF, JPG, PNG) file to be analyzed.  
Success Response (200 OK)

```json
{
  "vendor": "Telenor Norge AS",
  "invoice_date": "2025-09-30",
  "total_amount": 49.0,
  "currency": "NOK",
  "invoice_number": "99166894",
  "rawText": null
}
```

► Deployment (Vercel)
This project is configured for deployment on Vercel.
Fork this repository.

Create a new project on Vercel and connect it to your forked repository. Vercel will automatically detect the vercel.json file and deploy the FastAPI app.
In the Vercel project settings, navigate to Environment Variables and add the following:

VERTEX_PROJECT: documind-474412  
VERTEX_LOCATION: us-central1  
VERTEX_MODEL: gemini-2.0-flash-001  
GOOGLE_CREDENTIALS_JSON_CONTENT: (Crucial) Open your credentials.json file, copy its entire content (the full JSON object), and paste it as the value for this variable.

Finally, add your frontend's Vercel URL (e.g., https://documind-frontend.vercel.app) to the origins list in main.py and redeploy.

👤 Author
Claudio Rodriguez