#!/usr/bin/env python3
"""
FaultMaven Knowledge Base Manager

A CLI tool for managing the FaultMaven knowledge base.

Usage:
    python kb_manager.py <command> [options]

Commands:
    upload <file>      Upload a document to the knowledge base
    search <query>     Search the knowledge base
    list               List all documents
    delete <doc_id>    Delete a document
    status <doc_id>    Check document processing status
    bulk-upload <dir>  Upload all documents from a directory
    export             Export knowledge base metadata

Examples:
    python kb_manager.py upload runbook.md --title "Database Runbook"
    python kb_manager.py search "database timeout"
    python kb_manager.py bulk-upload ./docs --type playbook
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.error
import urllib.parse


class FaultMavenClient:
    """Client for FaultMaven API."""

    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None,
        files: Optional[dict] = None,
    ) -> dict:
        """Make an API request."""
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            if files:
                # Multipart form upload
                return self._upload_file(url, files, data or {})

            if data:
                body = json.dumps(data).encode("utf-8")
            else:
                body = None

            req = urllib.request.Request(url, data=body, headers=headers, method=method)

            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            try:
                return {"error": json.loads(error_body)}
            except json.JSONDecodeError:
                return {"error": {"message": error_body, "code": e.code}}
        except urllib.error.URLError as e:
            return {"error": {"message": str(e), "code": "CONNECTION_ERROR"}}

    def _upload_file(self, url: str, files: dict, data: dict) -> dict:
        """Upload a file using multipart form data."""
        import mimetypes
        from uuid import uuid4

        boundary = f"----WebKitFormBoundary{uuid4().hex}"
        lines = []

        # Add form fields
        for key, value in data.items():
            lines.append(f"--{boundary}")
            lines.append(f'Content-Disposition: form-data; name="{key}"')
            lines.append("")
            lines.append(str(value))

        # Add file
        for key, filepath in files.items():
            filename = os.path.basename(filepath)
            mime_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"

            lines.append(f"--{boundary}")
            lines.append(
                f'Content-Disposition: form-data; name="{key}"; filename="{filename}"'
            )
            lines.append(f"Content-Type: {mime_type}")
            lines.append("")

            with open(filepath, "rb") as f:
                file_content = f.read()

        lines.append(f"--{boundary}--")
        lines.append("")

        # Build body
        body_parts = []
        for line in lines[:-2]:  # Everything except file content and final boundary
            body_parts.append(line.encode("utf-8"))
            body_parts.append(b"\r\n")

        body_parts.append(file_content)
        body_parts.append(b"\r\n")
        body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))

        body = b"".join(body_parts)

        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"error": {"message": e.read().decode("utf-8"), "code": e.code}}

    def login(self, email: str, password: str) -> bool:
        """Login and get access token."""
        result = self._request(
            "POST", "/v1/auth/login", {"email": email, "password": password}
        )
        if "access_token" in result:
            self.token = result["access_token"]
            return True
        return False

    def upload_document(
        self,
        filepath: str,
        title: Optional[str] = None,
        doc_type: str = "document",
        tags: str = "",
    ) -> dict:
        """Upload a document to the knowledge base."""
        data = {
            "title": title or os.path.basename(filepath),
            "document_type": doc_type,
            "tags": tags,
        }
        return self._request(
            "POST", "/v1/knowledge/documents", data=data, files={"file": filepath}
        )

    def search(self, query: str, limit: int = 10) -> dict:
        """Search the knowledge base."""
        return self._request(
            "POST", "/v1/knowledge/search", {"query": query, "limit": limit}
        )

    def list_documents(self, limit: int = 50, offset: int = 0) -> dict:
        """List all documents."""
        return self._request(
            "GET", f"/v1/knowledge/documents?limit={limit}&offset={offset}"
        )

    def get_document(self, doc_id: str) -> dict:
        """Get document details."""
        return self._request("GET", f"/v1/knowledge/documents/{doc_id}")

    def delete_document(self, doc_id: str) -> dict:
        """Delete a document."""
        return self._request("DELETE", f"/v1/knowledge/documents/{doc_id}")


def get_client(args) -> FaultMavenClient:
    """Create and authenticate client."""
    base_url = args.url or os.environ.get("FM_API_URL", "http://localhost:8000")
    client = FaultMavenClient(base_url)

    # Try to get token from args, env, or config file
    token = args.token or os.environ.get("FM_ACCESS_TOKEN")

    if not token:
        # Try to read from config file
        config_path = Path.home() / ".faultmaven" / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                token = config.get("access_token")

    if not token:
        # Try to login
        email = args.email or os.environ.get("FM_EMAIL")
        password = args.password or os.environ.get("FM_PASSWORD")

        if email and password:
            if client.login(email, password):
                print(f"Logged in as {email}")
            else:
                print("Login failed. Please check credentials.")
                sys.exit(1)
        else:
            print("No authentication provided.")
            print("Set FM_ACCESS_TOKEN, or FM_EMAIL/FM_PASSWORD environment variables.")
            sys.exit(1)
    else:
        client.token = token

    return client


def cmd_upload(args):
    """Upload a document."""
    client = get_client(args)

    filepath = args.file
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    print(f"Uploading: {filepath}")
    result = client.upload_document(
        filepath,
        title=args.title,
        doc_type=args.type or "document",
        tags=args.tags or "",
    )

    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Document uploaded successfully!")
        print(f"  Document ID: {result.get('document_id', 'N/A')}")
        print(f"  Status: {result.get('status', 'N/A')}")


def cmd_search(args):
    """Search the knowledge base."""
    client = get_client(args)

    print(f"Searching for: {args.query}")
    print("-" * 50)

    result = client.search(args.query, limit=args.limit or 10)

    if "error" in result:
        print(f"Error: {result['error']}")
        return

    results = result.get("results", [])
    if not results:
        print("No results found.")
        return

    print(f"Found {len(results)} results:\n")
    for i, doc in enumerate(results, 1):
        score = doc.get("relevance_score", 0)
        print(f"{i}. {doc.get('title', 'Untitled')} (score: {score:.2f})")
        print(f"   Type: {doc.get('document_type', 'unknown')}")
        print(f"   ID: {doc.get('document_id', 'N/A')}")
        if doc.get("snippet"):
            snippet = doc["snippet"][:150] + "..." if len(doc["snippet"]) > 150 else doc["snippet"]
            print(f"   Snippet: {snippet}")
        print()


def cmd_list(args):
    """List all documents."""
    client = get_client(args)

    result = client.list_documents(limit=args.limit or 50)

    if "error" in result:
        print(f"Error: {result['error']}")
        return

    documents = result.get("documents", [])
    total = result.get("total", len(documents))

    print(f"Documents ({len(documents)} of {total}):")
    print("-" * 60)
    print(f"{'ID':<15} {'Title':<30} {'Type':<12} {'Status'}")
    print("-" * 60)

    for doc in documents:
        doc_id = doc.get("document_id", "N/A")[:12]
        title = doc.get("title", "Untitled")[:28]
        doc_type = doc.get("document_type", "unknown")[:10]
        status = doc.get("status", "unknown")
        print(f"{doc_id:<15} {title:<30} {doc_type:<12} {status}")


def cmd_delete(args):
    """Delete a document."""
    client = get_client(args)

    if not args.force:
        confirm = input(f"Delete document {args.doc_id}? [y/N]: ")
        if confirm.lower() != "y":
            print("Cancelled.")
            return

    result = client.delete_document(args.doc_id)

    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Document {args.doc_id} deleted.")


def cmd_status(args):
    """Check document processing status."""
    client = get_client(args)

    result = client.get_document(args.doc_id)

    if "error" in result:
        print(f"Error: {result['error']}")
        return

    print(f"Document: {result.get('title', 'Untitled')}")
    print(f"  ID: {result.get('document_id', 'N/A')}")
    print(f"  Type: {result.get('document_type', 'unknown')}")
    print(f"  Status: {result.get('status', 'unknown')}")
    print(f"  Created: {result.get('created_at', 'N/A')}")
    print(f"  Chunks: {result.get('chunk_count', 'N/A')}")


def cmd_bulk_upload(args):
    """Upload all documents from a directory."""
    client = get_client(args)

    directory = Path(args.directory)
    if not directory.is_dir():
        print(f"Not a directory: {directory}")
        return

    # Supported file extensions
    extensions = {".md", ".txt", ".pdf", ".rst", ".html"}

    files = [f for f in directory.rglob("*") if f.suffix.lower() in extensions]

    if not files:
        print(f"No supported files found in {directory}")
        print(f"Supported extensions: {', '.join(extensions)}")
        return

    print(f"Found {len(files)} files to upload:")
    for f in files:
        print(f"  - {f.name}")

    if not args.yes:
        confirm = input("\nProceed with upload? [y/N]: ")
        if confirm.lower() != "y":
            print("Cancelled.")
            return

    print("\nUploading...")
    success = 0
    failed = 0

    for filepath in files:
        print(f"  Uploading {filepath.name}...", end=" ")
        result = client.upload_document(
            str(filepath),
            title=filepath.stem,
            doc_type=args.type or "document",
            tags=args.tags or "",
        )

        if "error" in result:
            print(f"FAILED: {result['error']}")
            failed += 1
        else:
            print("OK")
            success += 1

    print(f"\nComplete: {success} uploaded, {failed} failed")


def cmd_export(args):
    """Export knowledge base metadata."""
    client = get_client(args)

    # Get all documents
    all_docs = []
    offset = 0
    limit = 100

    while True:
        result = client.list_documents(limit=limit, offset=offset)
        if "error" in result:
            print(f"Error: {result['error']}")
            return

        docs = result.get("documents", [])
        all_docs.extend(docs)

        if len(docs) < limit:
            break
        offset += limit

    output = {"total": len(all_docs), "documents": all_docs}

    if args.output:
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2)
        print(f"Exported {len(all_docs)} documents to {args.output}")
    else:
        print(json.dumps(output, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="FaultMaven Knowledge Base Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Global options
    parser.add_argument("--url", help="API base URL")
    parser.add_argument("--token", help="Access token")
    parser.add_argument("--email", help="Login email")
    parser.add_argument("--password", help="Login password")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # upload command
    upload_p = subparsers.add_parser("upload", help="Upload a document")
    upload_p.add_argument("file", help="File to upload")
    upload_p.add_argument("--title", help="Document title")
    upload_p.add_argument("--type", help="Document type (playbook, runbook, doc)")
    upload_p.add_argument("--tags", help="Comma-separated tags")

    # search command
    search_p = subparsers.add_parser("search", help="Search knowledge base")
    search_p.add_argument("query", help="Search query")
    search_p.add_argument("--limit", type=int, help="Max results")

    # list command
    list_p = subparsers.add_parser("list", help="List documents")
    list_p.add_argument("--limit", type=int, help="Max documents")

    # delete command
    delete_p = subparsers.add_parser("delete", help="Delete a document")
    delete_p.add_argument("doc_id", help="Document ID")
    delete_p.add_argument("-f", "--force", action="store_true", help="Skip confirmation")

    # status command
    status_p = subparsers.add_parser("status", help="Check document status")
    status_p.add_argument("doc_id", help="Document ID")

    # bulk-upload command
    bulk_p = subparsers.add_parser("bulk-upload", help="Upload directory")
    bulk_p.add_argument("directory", help="Directory path")
    bulk_p.add_argument("--type", help="Document type for all files")
    bulk_p.add_argument("--tags", help="Tags for all files")
    bulk_p.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")

    # export command
    export_p = subparsers.add_parser("export", help="Export KB metadata")
    export_p.add_argument("-o", "--output", help="Output file (JSON)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        "upload": cmd_upload,
        "search": cmd_search,
        "list": cmd_list,
        "delete": cmd_delete,
        "status": cmd_status,
        "bulk-upload": cmd_bulk_upload,
        "export": cmd_export,
    }

    if args.command in commands:
        commands[args.command](args)


if __name__ == "__main__":
    main()
