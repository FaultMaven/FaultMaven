"""Local filesystem storage provider for Core profile."""

from pathlib import Path
from typing import Optional
import aiofiles
import aiofiles.os

from faultmaven.providers.interfaces import FileProvider


class LocalFileProvider(FileProvider):
    """
    Local filesystem implementation of FileProvider.

    Stores files in a local directory structure.
    """

    def __init__(self, base_path: str | Path):
        """
        Initialize local file provider.

        Args:
            base_path: Base directory for file storage
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, key: str) -> Path:
        """Get full file path from key."""
        # Ensure key doesn't escape base_path
        safe_key = key.lstrip("/").replace("..", "")
        return self.base_path / safe_key

    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str,
        metadata: Optional[dict[str, str]] = None,
    ) -> str:
        """Upload file to local storage."""
        file_path = self._get_file_path(key)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(data)

        # Store metadata in a sidecar file if provided
        if metadata:
            metadata_path = file_path.with_suffix(file_path.suffix + ".meta")
            async with aiofiles.open(metadata_path, "w") as f:
                import json
                await f.write(json.dumps(metadata))

        return str(file_path)

    async def download(self, key: str) -> bytes:
        """Download file from local storage."""
        file_path = self._get_file_path(key)

        if not await self.exists(key):
            raise FileNotFoundError(f"File not found: {key}")

        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()

    async def delete(self, key: str) -> bool:
        """Delete file from local storage."""
        file_path = self._get_file_path(key)

        if not file_path.exists():
            return False

        await aiofiles.os.remove(file_path)

        # Also delete metadata file if exists
        metadata_path = file_path.with_suffix(file_path.suffix + ".meta")
        if metadata_path.exists():
            await aiofiles.os.remove(metadata_path)

        return True

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Get URL for local file.

        For local storage, this returns a file:// URL.
        In a real deployment, you'd serve these through the API.
        """
        file_path = self._get_file_path(key)
        return f"file://{file_path.absolute()}"

    async def exists(self, key: str) -> bool:
        """Check if file exists."""
        file_path = self._get_file_path(key)
        return file_path.exists()
