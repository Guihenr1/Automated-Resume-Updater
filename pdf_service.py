import os
import json
import uuid
from html import escape
import requests

from services.metadata_service import _upload_file, _update_log, persist_resume_metadata, improve_text_with_openai, \
    render_section

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
    page_size: str = "A4",
    objective: str | None = None,
    technical_skills: list[str] | str | None = None,
    experience: list[dict] | None = None,
    education: list[dict] | None = None,
    certification: list[str] | str | None = None,
    courses: list[str] | str | None = None,
    languages: list[str] | str | None = None,
    links: dict | list[dict] | list[str] | None = None,

) -> str:
    api_key = os.getenv("NUTRIENT_API_KEY")
    azure_container_sas_url = os.getenv("AZURE_CONTAINER_SAS_URL")

    if not api_key:
        raise ValueError("Missing API key. Set NUTRIENT_API_KEY or pass api_key.")

    safe_name = escape(name)
    safe_desc = escape(description)

    safe_desc = improve_text_with_openai(safe_desc)

    sections_html = []

    sections_html.append(f"""
                        <div class="section">
                          <h2>About</h2>
                          <pre>{safe_desc}</pre>
                        </div>""")
    sections_html.append(render_section("Objective", objective))
    sections_html.append(render_section("Technical Skills", technical_skills))
    sections_html.append(render_section("Experience", experience))
    sections_html.append(render_section("Education", education))
    sections_html.append(render_section("Certification", certification))
    sections_html.append(render_section("Courses", courses))
    sections_html.append(render_section("Languages", languages))

    links_html = ""
    if links:
        items = []
        if isinstance(links, dict):
            for label, url in links.items():
                label_s = escape(str(label))
                url_s = escape(str(url))
                items.append(f'<li><a href="{url_s}" target="_blank" rel="noopener">{label_s}</a></li>')
        elif isinstance(links, (list, tuple)):
            for entry in links:
                if isinstance(entry, dict) and "url" in entry:
                    label = entry.get("label") or entry.get("name") or entry["url"]
                    label_s = escape(str(label))
                    url_s = escape(str(entry["url"]))
                    items.append(f'<li><a href="{url_s}" target="_blank" rel="noopener">{label_s}</a></li>')
                else:
                    label_s = escape(str(entry))
                    items.append(f"<li>{label_s}</li>")
        if items:
            links_html = f"""
                        <div class="section">
                          <h2>Links</h2>
                          <ul>
                            {''.join(items)}
                          </ul>
                        </div>"""
    if links_html:
        sections_html.append(links_html)

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
                          .meta {{ color: #666; font-size: 0.95rem; margin-top: 0; }}
                          .item h3 {{ margin-bottom: 0.25rem; }}
                          pre {{ white-space: pre-wrap; }}
                          ul {{ margin: 0.5rem 0 0 1.25rem; }}
                          dl {{ margin: 0.5rem 0 0 0; }}
                          dt {{ font-weight: 600; }}
                          dd {{ margin: 0 0 0.5rem 0; }}
                          a {{ color: #1a73e8; text-decoration: none; }}
                          a:hover {{ text-decoration: underline; }}
                        </style>
                      </head>
                      <body>
                        <h1>{safe_name}</h1>
                        <p class="subtitle">Automated Resume</p>
                        {''.join(sections_html)}
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