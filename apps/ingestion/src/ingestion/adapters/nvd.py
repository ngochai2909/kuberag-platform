"""NVD CVE API 2.0 adapter."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from ingestion.http import HttpClient
from ingestion.models import SourceDocument, document_checksum, normalize_whitespace

DEFAULT_API_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"
DETAIL_URL_TEMPLATE = "https://nvd.nist.gov/vuln/detail/{cve_id}"


class NvdAdapter:
    """Normalize NVD CVE API 2.0 payloads into SourceDocument records."""

    source = "nvd"

    def __init__(
        self,
        http: HttpClient,
        *,
        api_base: str = DEFAULT_API_BASE,
        results_per_page: int = 20,
    ) -> None:
        self._http = http
        self._api_base = api_base.rstrip("/")
        self._results_per_page = results_per_page

    def fetch_documents(
        self,
        *,
        pub_start: datetime | None = None,
        pub_end: datetime | None = None,
        start_index: int = 0,
        cve_id: str | None = None,
    ) -> list[SourceDocument]:
        params: dict[str, str | int] = {
            "resultsPerPage": self._results_per_page,
            "startIndex": start_index,
        }
        if cve_id:
            params["cveId"] = cve_id
        if pub_start is not None:
            params["pubStartDate"] = _format_nvd_timestamp(pub_start)
        if pub_end is not None:
            params["pubEndDate"] = _format_nvd_timestamp(pub_end)

        url = f"{self._api_base}?{urlencode(params)}"
        response = self._http.get(url)
        payload = json.loads(response.text)
        return self.parse_response(payload)

    def parse_response(self, payload: dict[str, Any]) -> list[SourceDocument]:
        vulnerabilities = payload.get("vulnerabilities")
        if not isinstance(vulnerabilities, list):
            msg = "NVD payload is missing vulnerabilities list"
            raise ValueError(msg)

        documents: list[SourceDocument] = []
        for entry in vulnerabilities:
            if not isinstance(entry, dict):
                continue
            cve = entry.get("cve")
            if not isinstance(cve, dict):
                continue
            documents.append(self._to_document(cve))
        return documents

    def _to_document(self, cve: dict[str, Any]) -> SourceDocument:
        cve_id = str(cve.get("id") or "").strip()
        if not cve_id:
            msg = "NVD CVE entry is missing id"
            raise ValueError(msg)

        description = select_description(cve.get("descriptions"))
        if not description:
            msg = f"NVD CVE {cve_id} is missing a usable description"
            raise ValueError(msg)

        title = f"{cve_id}: {description.split('.', maxsplit=1)[0].strip()}"
        title = normalize_whitespace(title)[:1000]
        text = normalize_whitespace(description)
        url = DETAIL_URL_TEMPLATE.format(cve_id=cve_id)
        metadata: dict[str, Any] = {
            "vuln_status": cve.get("vulnStatus"),
            "source_identifier": cve.get("sourceIdentifier"),
            "last_modified": cve.get("lastModified"),
            "api_version": "2.0",
        }
        severity = extract_primary_severity(cve.get("metrics"))
        if severity is not None:
            metadata["cvss_severity"] = severity["severity"]
            metadata["cvss_version"] = severity["version"]
            metadata["cvss_score"] = severity["score"]

        return SourceDocument(
            source=self.source,
            external_id=cve_id,
            title=title,
            url=url,
            published_at=_parse_iso_datetime(cve.get("published")),
            text=text,
            checksum=document_checksum(title=title, text=text),
            metadata={key: value for key, value in metadata.items() if value is not None},
        )


def select_description(descriptions: Any) -> str | None:
    if not isinstance(descriptions, list):
        return None
    english: str | None = None
    fallback: str | None = None
    for item in descriptions:
        if not isinstance(item, dict):
            continue
        value = item.get("value")
        if not isinstance(value, str) or not value.strip():
            continue
        lang = str(item.get("lang") or "").lower()
        if lang.startswith("en"):
            english = value
            break
        if fallback is None:
            fallback = value
    return english or fallback


def extract_primary_severity(metrics: Any) -> dict[str, Any] | None:
    if not isinstance(metrics, dict):
        return None
    for version, key in (
        ("3.1", "cvssMetricV31"),
        ("3.0", "cvssMetricV30"),
        ("2.0", "cvssMetricV2"),
    ):
        entries = metrics.get(key)
        if not isinstance(entries, list) or not entries:
            continue
        first = entries[0]
        if not isinstance(first, dict):
            continue
        cvss = first.get("cvssData")
        if not isinstance(cvss, dict):
            continue
        score = cvss.get("baseScore")
        severity = first.get("baseSeverity") or cvss.get("baseSeverity")
        if score is None and severity is None:
            continue
        return {
            "version": version,
            "score": score,
            "severity": severity,
        }
    return None


def _format_nvd_timestamp(value: datetime) -> str:
    # NVD expects ISO-8601 with timezone offset, e.g. 2024-01-01T00:00:00.000+00:00
    aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return aware.isoformat(timespec="milliseconds")


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
