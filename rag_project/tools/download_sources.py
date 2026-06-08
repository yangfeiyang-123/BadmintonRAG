import argparse
import csv
import json
import mimetypes
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CodexRAGDownloader/1.0"


def safe_name(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", value or "").strip("_")
    return (safe or "untitled")[:96]


def build_opener(proxy: str | None):
    handlers = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    return urllib.request.build_opener(*handlers)


def fetch(opener, url: str, timeout: int):
    request = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    with opener.open(request, timeout=timeout) as response:
        data = response.read()
        content_type = response.headers.get("content-type", "")
        return {
            "status": getattr(response, "status", 200),
            "content_type": content_type,
            "data": data,
            "final_url": response.geturl(),
        }


def looks_like_pdf(url: str, content_type: str, data: bytes) -> bool:
    return data.lstrip()[:5] == b"%PDF-"


def decode_html(data: bytes, content_type: str) -> str:
    match = re.search(r"charset=([\w.-]+)", content_type or "", flags=re.I)
    encodings = []
    if match:
        encodings.append(match.group(1))
    encodings.extend(["utf-8", "gb18030", "latin-1"])
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def resolve_link(base_url: str, href: str) -> str | None:
    if not href:
        return None
    href = href.strip()
    if href.startswith("#") or href.lower().startswith(("javascript:", "mailto:")):
        return None
    return urllib.parse.urljoin(base_url, href)


def pdf_candidates(url: str, html: str) -> list[str]:
    candidates: list[str] = []

    if "arxiv.org/abs/" in url:
        candidates.append(url.replace("/abs/", "/pdf/"))

    patterns = [
        r"""(?is)(?:href|src)\s*=\s*["']([^"']+?\.pdf(?:\?[^"']*)?)["']""",
        r"""(?is)(?:href|src)\s*=\s*["']([^"']*article/download/[^"']+)["']""",
        r"""(?is)(?:href|src)\s*=\s*["']([^"']*/pdf/[^"']+)["']""",
        r"""(?is)(?:href|src)\s*=\s*["']([^"']*download[^"']*)["']""",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, html):
            candidate = resolve_link(url, match.group(1))
            if candidate and candidate not in candidates:
                candidates.append(candidate)

    return candidates


def write_csv(path: Path, rows: list[dict]):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="rag_project/manifests/badminton_sources.csv")
    parser.add_argument("--output-root", default="rag_project/sources/raw")
    parser.add_argument("--proxy", default=os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY"))
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--max-pdf-links-per-page", type=int, default=4)
    parser.add_argument("--sleep", type=float, default=0.3)
    args = parser.parse_args()

    manifest = Path(args.manifest)
    output_root = Path(args.output_root)
    pdf_dir = output_root / "pdf"
    html_dir = output_root / "html"
    metadata_dir = output_root / "metadata"
    for directory in [pdf_dir, html_dir, metadata_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    opener = build_opener(args.proxy)

    rows = list(csv.DictReader(manifest.open("r", encoding="utf-8-sig")))
    results = []

    for row in rows:
        source_id = safe_name(row["id"])
        downloaded: list[str] = []
        candidates: list[str] = []
        notes: list[str] = []
        status = "started"
        primary_status_code = ""
        primary_content_type = ""

        try:
            primary = fetch(opener, row["url"].strip(), args.timeout)
            primary_status_code = str(primary["status"])
            primary_content_type = primary["content_type"]

            if looks_like_pdf(primary["final_url"], primary["content_type"], primary["data"]):
                pdf_path = pdf_dir / f"{source_id}.pdf"
                pdf_path.write_bytes(primary["data"])
                downloaded.append(str(pdf_path))
                status = "downloaded_pdf"
            else:
                html = decode_html(primary["data"], primary["content_type"])
                html_path = html_dir / f"{source_id}.html"
                html_path.write_text(html, encoding="utf-8")
                downloaded.append(str(html_path))
                status = "downloaded_html"

                candidates = pdf_candidates(primary["final_url"], html)
                saved_pdf_count = 0
                for candidate in candidates[: args.max_pdf_links_per_page]:
                    try:
                        time.sleep(args.sleep)
                        pdf_response = fetch(opener, candidate, args.timeout)
                        if looks_like_pdf(pdf_response["final_url"], pdf_response["content_type"], pdf_response["data"]):
                            saved_pdf_count += 1
                            suffix = "" if saved_pdf_count == 1 else f"_{saved_pdf_count}"
                            pdf_path = pdf_dir / f"{source_id}{suffix}.pdf"
                            pdf_path.write_bytes(pdf_response["data"])
                            downloaded.append(str(pdf_path))
                            status = "downloaded_html_and_pdf"
                        else:
                            notes.append(
                                f"PDF candidate not saved: {candidate} content_type={pdf_response['content_type']}"
                            )
                    except Exception as exc:
                        notes.append(f"PDF candidate failed: {candidate} error={exc}")
        except urllib.error.HTTPError as exc:
            status = "http_error"
            primary_status_code = str(exc.code)
            primary_content_type = exc.headers.get("content-type", "")
            notes.append(str(exc))
        except Exception as exc:
            status = "failed"
            notes.append(str(exc))

        results.append(
            {
                "id": row["id"],
                "category": row["category"],
                "title": row["title"],
                "year": row["year"],
                "url": row["url"],
                "expected_access": row["expected_access"],
                "status": status,
                "primary_status_code": primary_status_code,
                "primary_content_type": primary_content_type,
                "downloaded_files": ";".join(downloaded),
                "pdf_candidates": ";".join(candidates),
                "notes": " | ".join(notes),
            }
        )
        csv_out = metadata_dir / "download_results.csv"
        json_out = metadata_dir / "download_results.json"
        write_csv(csv_out, results)
        json_out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{row['id']}: {status}")
        time.sleep(args.sleep)

    csv_out = metadata_dir / "download_results.csv"
    json_out = metadata_dir / "download_results.json"
    write_csv(csv_out, results)
    json_out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    summary: dict[str, int] = {}
    for result in results:
        summary[result["status"]] = summary.get(result["status"], 0) + 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Results CSV: {csv_out}")
    print(f"Results JSON: {json_out}")


if __name__ == "__main__":
    main()
