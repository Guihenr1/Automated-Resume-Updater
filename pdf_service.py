import os
import json
import uuid
from html import escape
import requests

from services.metadata_service import _upload_file, _update_log, persist_resume_metadata

API_URL = "https://api.nutrient.io/build"

def _ensure_unique_local_path(path: str) -> str:
    if not os.path.exists(path):
        return path
    root, ext = os.path.splitext(path)
    return f"{root}-{uuid.uuid4().hex[:8]}{ext}"

def generate_resume_pdf(
    name: str,
    description: str,
    output_path: str,
    page_size: str = "A4"
) -> str:
    api_key = os.getenv("NUTRIENT_API_KEY")
    azure_container_sas_url = os.getenv("AZURE_CONTAINER_SAS_URLA")

    if not api_key:
        raise ValueError("Missing API key. Set NUTRIENT_API_KEY or pass api_key.")

    safe_name = escape(name)
    safe_desc = escape(description)

    html_doc = f"""<!doctype html>
                <html>
                  <head>
                    <meta charset="utf-8" />
                    <title>Resume</title>
                    <style>
                      body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 2rem; }}
                      h1 {{ margin-bottom: 0.25rem; }}
                      .subtitle {{ color: #555; margin-top: 0; }}
                      .section {{ margin-top: 1.5rem; }}
                      pre {{ white-space: pre-wrap; }}
                    </style>
                  </head>
                  <body>
                    <h1>{safe_name}</h1>
                    <p class="subtitle">Automated Resume</p>
                    <div class="section">
                      <h2>About</h2>
                      <pre>{safe_desc}</pre>
                    </div>
                  </body>
                </html>"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/pdf, application/zip",
    }

    instructions = {
        "parts": [
            {
                "html": "index.html"  # reference the uploaded file by name
            }
        ],
        "outputs": [
            {
                "type": "pdf",
                "name": "resume.pdf",
                "input": "index.html",
                "options": {"page": {"size": page_size}},
            }
        ],
    }

    files = {
        "index.html": ("index.html", html_doc.encode("utf-8"), "text/html; charset=utf-8"),
    }
    data = {
        "instructions": json.dumps(instructions),
    }

    upload_response = _upload_file(API_URL, headers=headers, data=data, files=files)

    if azure_container_sas_url:
        return _update_log(azure_container_sas_url, name, description, page_size, upload_response)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(upload_response.content)

    return output_path