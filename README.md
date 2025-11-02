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

## ► Configuration

This project requires environment variables to run.

### 1. Common Variables
The following variables are required for **both** local development and production deployment.

| Variable | Description | Example Value |
| :--- | :--- | :--- |
| `VERTEX_PROJECT` | The Google Cloud project ID. | `documind-474412` |
| `VERTEX_LOCATION` | The region for the Vertex AI model. | `us-central1` |
| `VERTEX_MODEL` | The name of the Gemini model to use. | `gemini-2.0-flash-001` |

### 2. Environment-Specific Variables

You must provide the correct variables based on where the app is running.

**For Local Development (in a `.env` file):**
```env
# A placeholder path to the local Google Cloud credentials file.
# This path is used by google.auth.default()
GOOGLE_APPLICATION_CREDENTIALS="C:/path/to/credentials.json"
```

### For Production Deployment (in Vercel):

GOOGLE_CREDENTIALS_JSON_CONTENT: (Crucial) Open the credentials.json file, copy its entire content (the full JSON object), and paste it as the value for this variable.

FRONTEND_URL: (Required) The public URL of the deployed frontend (e.g., https://your-frontend-app.vercel.app).

## ► Local Development
**1. Prerequisites:**  
Python 3.11+  
A Google Cloud project with the Vertex AI API enabled.  
A Google Cloud Service Account credentials.json file (see Configuration above).


**2. Clone and Install Dependencies**
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
**3. Create .env file**  
Create a file named .env in the root of the project and add the variables listed in the "Configuration > For Local Development" section above.
```bash
uvicorn main:app --reload
```

The application will start on http://localhost:8000.

## ► API Endpoint
The API exposes a single endpoint for invoice extraction.

URL: POST /invoices/extract  
Body: multipart/form-data  
Key: file  
Value: The (PDF) file to be analyzed.  
Note: The API is configured to only accept application/pdf file types.

```json
{
  "vendor": "Telenor AS",
  "invoice_date": "2025-09-30",
  "total_amount": 500.0,
  "currency": "NOK",
  "invoice_number": "991986894",
  "rawText": null
}
```
## ► Deployment (Vercel)
This project is configured for deployment on Vercel.

Fork this repository.

Create a new project on Vercel and connect it to your forked repository. Vercel will automatically detect the vercel.json file.

In the Vercel project settings, navigate to Settings > Environment Variables and add all the variables listed in the "Configuration > For Production Deployment" section above.

Deploy the project.

👤 Author
Claudio Rodriguez