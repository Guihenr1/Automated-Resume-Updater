import os
import json
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
