import os
import json
from html import escape

import requests
from datetime import datetime, timezone
from utils.identifiers import slugify

def persist_resume_metadata(
    original_name: str,
    code: str,
    blob_url: str,
    page_size: str,
    description: str,
) -> None:
    created_at = datetime.now(timezone.utc).isoformat()
    name_slug = slugify(original_name)

    entity = {
        "PartitionKey": "by-code",
        "RowKey": code,
        "OriginalName": original_name,
        "NameSlug": name_slug,
        "Code": code,
        "BlobUrl": blob_url,
        "PageSize": page_size,
        "CreatedAt": created_at,
        "Description": description,
    }

    table_sas_url = os.getenv("AZURE_TABLE_SAS_URL")
    table_name = os.getenv("AZURE_TABLE_NAME")
    if table_sas_url and table_name:
        _insert_table_entity(table_sas_url.strip(), table_name.strip(), entity)

    logs_container_sas_url = os.getenv("AZURE_LOGS_CONTAINER_SAS_URL")
    if logs_container_sas_url:
        _upload_metadata_json_to_logs(logs_container_sas_url.strip(), code, entity)

def _insert_table_entity(table_account_sas_url: str, table_name: str, entity: dict) -> None:
    if "?" not in table_account_sas_url:
        raise ValueError("AZURE_TABLE_SAS_URL must include a SAS query string")

    if not entity.get("PartitionKey") or not entity.get("RowKey"):
        raise ValueError("Entity must include non-empty 'PartitionKey' and 'RowKey'")

    base_url, sas_query = table_account_sas_url.split("?", 1)

    from urllib.parse import urlparse
    parsed = urlparse(base_url)
    path = parsed.path.rstrip("/")
    table_segment = f"/{table_name}"

    if path.endswith(table_segment) or path.endswith(f"{table_segment}()"):
        table_url = base_url.rstrip("/")
    else:
        if not table_name:
            raise ValueError("table_name is required when AZURE_TABLE_SAS_URL is account-level")
        table_url = f"{base_url.rstrip('/')}{table_segment}"

    if table_url.endswith("()"):
        table_url = table_url[:-2]

    url = f"{table_url}?{sas_query}"

    headers = {
        "Accept": "application/json;odata=nometadata",
        "Content-Type": "application/json;odata=nometadata",
        "Prefer": "return-no-content",
        # These headers improve compatibility with the Table service
        "DataServiceVersion": "3.0;NetFx",
        "MaxDataServiceVersion": "3.0;NetFx",
        "x-ms-version": "2019-02-02",
    }

    import requests, json
    resp = requests.post(url, headers=headers, data=json.dumps(entity), timeout=30)
    try:
        resp.raise_for_status()
    except requests.HTTPError as ex:
        raise requests.HTTPError(f"Table insert failed: {ex}\nResponse text: {getattr(resp, 'text', '')}") from ex

def _upload_metadata_json_to_logs(logs_container_sas_url: str, code: str, entity: dict) -> None:
    if "?" not in logs_container_sas_url:
        raise ValueError("AZURE_LOGS_CONTAINER_SAS_URL must include a SAS query string")

    base_url, sas_query = logs_container_sas_url.split("?", 1)
    blob_name = f"{code}.json"
    url = f"{base_url.rstrip('/')}/{blob_name}?{sas_query}"

    headers = {
        "x-ms-blob-type": "BlockBlob",
        "Content-Type": "application/json; charset=utf-8",
        "If-None-Match": "*",
    }
    body = json.dumps(entity, ensure_ascii=False).encode("utf-8")
    resp = requests.put(url, headers=headers, data=body, timeout=30)
    resp.raise_for_status()

def _upload_file(
        api_url: str,
        headers: dict[str, str],
        data: dict[str, str] | None = None,
        files: dict[str, object] | None = None,
        timeout: int = 30
) -> requests.Response:
    resp = requests.post(api_url, headers=headers, data=data, files=files, timeout=timeout)

    try:
        resp.raise_for_status()
    except requests.HTTPError as ex:
        msg = getattr(resp, "text", "")
        raise requests.HTTPError(f"PDF generation failed: {ex}\nResponse text: {msg}") from ex

    return resp

def _update_log(
        api_url: str,
        name: str,
        description: str,
        page_size: str,
        upload: requests.Response,
        timeout: int = 30
) -> str | None:
    from utils.identifiers import slugify, generate_resume_code
    container_url = api_url.strip()

    if "?" in container_url:
        base_url, sas_query = container_url.split("?", 1)
    else:
        raise ValueError("azure_container_sas_url must include a SAS query string")

    name_slug = slugify(name)
    code = generate_resume_code()
    blob_name = f"{name_slug}-{code}.pdf"

    blob_url = f"{base_url.rstrip('/')}/{blob_name}?{sas_query}"

    put_headers = {
        "x-ms-blob-type": "BlockBlob",
        "Content-Type": "application/pdf",
        "If-None-Match": "*",
    }
    put_resp = requests.put(blob_url, headers=put_headers, data=upload.content, timeout=timeout)
    try:
        put_resp.raise_for_status()
    except requests.HTTPError as ex:
        msg = getattr(put_resp, "text", "")
        raise requests.HTTPError(f"Azure blob upload failed: {ex}\nResponse text: {msg}") from ex

    try:
        persist_resume_metadata(
            original_name=name,
            code=code,
            blob_url=blob_url,
            page_size=page_size,
            description=description,
        )
    except Exception as meta_ex:
        print(f"Warning: failed to persist metadata: {meta_ex}")

    return blob_url

def get_all_resumes(page_size: int = 1000, max_pages: int | None = None) -> list[dict]:
    table_sas_url = os.getenv("AZURE_TABLE_SAS_URL")
    table_name = os.getenv("AZURE_TABLE_NAME")
    if not table_sas_url or not table_name:
        return []

    if "?" not in table_sas_url:
        raise ValueError("AZURE_TABLE_SAS_URL must include a SAS query string")

    base_url, sas_query = table_sas_url.split("?", 1)

    from urllib.parse import urlparse, quote
    parsed = urlparse(base_url)
    path = parsed.path.rstrip("/")
    table_segment = f"/{table_name}"

    if path.endswith(table_segment) or path.endswith(f"{table_segment}()"):
        table_url = base_url.rstrip("/")
    else:
        table_url = f"{base_url.rstrip('/')}{table_segment}"

    if table_url.endswith("()"):
        table_url = table_url[:-2]

    base_query_url = f"{table_url}?{sas_query}"

    headers = {
        "Accept": "application/json;odata=nometadata",
        "DataServiceVersion": "3.0;NetFx",
        "MaxDataServiceVersion": "3.0;NetFx",
        "x-ms-version": "2019-02-02",
    }

    resumes: list[dict] = []
    next_pk: str | None = None
    next_rk: str | None = None
    pages_fetched = 0

    while True:
        query_parts = [
            "$filter=PartitionKey eq 'by-code'",
            f"$top={page_size}",
        ]
        if next_pk and next_rk:
            query_parts.append(f"NextPartitionKey={quote(next_pk)}")
            query_parts.append(f"NextRowKey={quote(next_rk)}")

        url = f"{base_query_url}&{'&'.join(query_parts)}"

        resp = requests.get(url, headers=headers, timeout=30)
        try:
            resp.raise_for_status()
        except requests.HTTPError as ex:
            msg = getattr(resp, "text", "")
            raise requests.HTTPError(f"Table query failed: {ex}\nResponse text: {msg}") from ex

        payload = resp.json() if resp.content else {}
        values = payload.get("value", [])
        for e in values:
            resumes.append({
                "code": e.get("Code") or e.get("RowKey"),
                "name": e.get("OriginalName") or e.get("NameSlug"),
                "description": e.get("Description"),
                "page_size": e.get("PageSize"),
                "created_at": e.get("CreatedAt"),
                "blob_url": e.get("BlobUrl"),
            })

        next_pk = resp.headers.get("x-ms-continuation-NextPartitionKey")
        next_rk = resp.headers.get("x-ms-continuation-NextRowKey")

        pages_fetched += 1
        if not next_pk or not next_rk:
            break
        if max_pages is not None and pages_fetched >= max_pages:
            break

    return resumes

def delete_resume_blob(blob_url: str, timeout: int = 30) -> None:
    if not blob_url:
        raise ValueError("blob_url is required to delete a resume blob")

    headers = {
        "x-ms-version": "2019-12-12",
        "x-ms-delete-snapshots": "include",
    }
    resp = requests.delete(blob_url, headers=headers, timeout=timeout)
    try:
        resp.raise_for_status()
    except requests.HTTPError as ex:
        msg = getattr(resp, "text", "")
        raise requests.HTTPError(f"Failed to delete resume blob: {ex}\nResponse text: {msg}") from ex

def improve_text_with_openai(
    text: str,
    property: list[str] | str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.3,
    max_tokens: int = 600
) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Missing OpenAI API key. Set OPENAI_API_KEY in the environment.")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    messages = [
        {
            "role": "system",
            "content": (
                "You are an assistant that rewrites user-provided text for clarity, grammar, and concision. "
                "Preserve all factual details and specific accomplishments. Avoid adding new facts. "
                "Return ONLY the improved text, with no markdown or additional commentary."
            ),
        },
        {
            "role": "user",
            "content": f"Improve the following resume {property}:\n\n{text}",
        },
    ]
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to contact OpenAI API: {e}") from e

    if resp.status_code != 200:
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        raise RuntimeError(f"OpenAI API error ({resp.status_code}): {err}")

    data = resp.json()
    try:
        improved = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected OpenAI response format: {data}") from e

    return improved.strip()

def render_section(title: str, content) -> str:
    if content is None:
        return ""
    html = []
    html.append(f'<div class="section"><h2>{escape(title)}</h2>')
    if isinstance(content, str):
        if content.strip():
            html.append(f"<p>{escape(content.strip())}</p>")
    elif isinstance(content, dict):
        if content:
            html.append("<dl>")
            for k, v in content.items():
                k_s = escape(str(k))
                if isinstance(v, str):
                    v_s = escape(v)
                    html.append(f"<dt>{k_s}</dt><dd>{v_s}</dd>")
                else:
                    v_s = escape(json.dumps(v, ensure_ascii=False))
                    html.append(f"<dt>{k_s}</dt><dd><pre>{v_s}</pre></dd>")
            html.append("</dl>")
    elif isinstance(content, (list, tuple)):
        if content:
            if all(isinstance(item, dict) for item in content):
                for item in content:
                    html.append('<div class="item">')
                    heading = []
                    for key in ("role", "title", "position"):
                        if key in item and item[key]:
                            heading.append(str(item[key]))
                            break
                    for key in ("company", "organization", "institution"):
                        if key in item and item[key]:
                            heading.append(str(item[key]))
                            break
                    sub = []
                    for key in ("period", "dates", "duration", "location"):
                        if key in item and item[key]:
                            sub.append(str(item[key]))
                    if heading:
                        html.append(f"<h3>{escape(' — '.join(heading))}</h3>")
                    if sub:
                        html.append(f"<p class=\"meta\">{escape(' · '.join(sub))}</p>")
                    for key in ("bullets", "highlights", "responsibilities"):
                        if key in item and isinstance(item[key], (list, tuple)) and item[key]:
                            html.append("<ul>")
                            for bullet in item[key]:
                                html.append(f"<li>{escape(str(bullet))}</li>")
                            html.append("</ul>")
                    remaining = {k: v for k, v in item.items() if k not in {"role","title","position","company","organization","institution","period","dates","duration","location","bullets","highlights","responsibilities"}}
                    if remaining:
                        html.append("<dl>")
                        for k, v in remaining.items():
                            html.append(f"<dt>{escape(str(k))}</dt><dd>{escape(str(v))}</dd>")
                        html.append("</dl>")
                    html.append("</div>")
            else:
                html.append("<ul>")
                for item in content:
                    html.append(f"<li>{escape(str(item))}</li>")
                html.append("</ul>")
    html.append("</div>")
    return "".join(html)
