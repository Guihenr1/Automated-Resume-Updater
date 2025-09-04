import os
import json
from html import escape
import requests

API_URL = "https://api.nutrient.io/build"

def generate_resume_pdf(
    name: str,
    description: str,
    output_path: str,
    page_size: str = "A4"
) -> str:
    api_key = os.getenv("NUTRIENT_API_KEY")
    azure_container_sas_url = os.getenv("AZURE_CONTAINER_SAS_URL")

    if not api_key:
        raise ValueError("Missing API key. Set NUTRIENT_API_KEY or pass api_key.")
    if not azure_container_sas_url:
        raise ValueError("Missing Azure Container SAS URL.")

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

    resp = requests.post(API_URL, headers=headers, data=data, files=files, timeout=60)
    try:
        resp.raise_for_status()
    except requests.HTTPError as ex:
        msg = getattr(resp, "text", "")
        raise requests.HTTPError(f"PDF generation failed: {ex}\nResponse text: {msg}") from ex

    pdf_bytes = resp.content

    if azure_container_sas_url:
        container_url = azure_container_sas_url.strip()

        if "?" in container_url:
            base_url, sas_query = container_url.split("?", 1)
        else:
            raise ValueError("azure_container_sas_url must include a SAS query string")

        import re
        base = re.sub(r"[^a-zA-Z0-9_-]+", "_", name).strip("_") or "resume"
        blob_name = f"{base}.pdf"

        blob_url = f"{base_url.rstrip('/')}/{blob_name}?{sas_query}"

        put_headers = {
            "x-ms-blob-type": "BlockBlob",
            "Content-Type": "application/pdf",
        }
        put_resp = requests.put(blob_url, headers=put_headers, data=pdf_bytes, timeout=60)
        try:
            put_resp.raise_for_status()
        except requests.HTTPError as ex:
            msg = getattr(put_resp, "text", "")
            raise requests.HTTPError(f"Azure blob upload failed: {ex}\nResponse text: {msg}") from ex

        return blob_url

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(resp.content)

    return output_path