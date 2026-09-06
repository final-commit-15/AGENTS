"""PDF / Image / Audio media tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agentforge_agents.schemas.tools import ToolParameter, ToolResult
from agentforge_agents.tools.base import BaseTool


class PDFTool(BaseTool):
    """Extract text and page counts from PDF files."""

    name = "pdf"
    description = "Read PDF text (per page) and report page count and metadata."
    category = "documents"
    timeout_seconds = 60.0
    tags = ["pdf", "documents"]

    parameters = [
        ToolParameter(
            name="path", type="string", required=True, description="Path to the PDF file."
        ),
        ToolParameter(name="page_from", type="integer", required=False, default=1),
        ToolParameter(name="page_to", type="integer", required=False),
        ToolParameter(
            name="mode", type="string", required=False, enum=["text", "metadata"], default="text"
        ),
    ]

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        path = Path(str(arguments.get("path", "")))
        if not path.is_file():
            return ["pdf file not found"]
        return []

    async def execute(self, arguments: dict[str, Any] | None = None) -> ToolResult:
        arguments = arguments or {}
        path = Path(str(arguments["path"]))
        try:
            import pypdf
        except ImportError:
            return self.err("pypdf is required for PDF reading; install the pdf extra")
        try:
            reader = pypdf.PdfReader(str(path))
            total = len(reader.pages)
            if arguments.get("mode") == "metadata":
                return self.ok(
                    {
                        "pages": total,
                        "metadata": reader.metadata
                        and {k: str(v) for k, v in reader.metadata.items()},
                    }
                )
            page_from = max(1, int(arguments.get("page_from") or 1))
            page_to = int(arguments.get("page_to") or total)
            sections = []
            for index in range(min(page_from, total + 1), min(page_to, total) + 1):
                text = reader.pages[index - 1].extract_text() or ""
                sections.append({"page": index, "text": text[:8000]})
            return self.ok({"pages": total, "sections": sections, "extracted_pages": len(sections)})
        except pypdf.PdfReadError as exc:
            return self.err(f"pdf read failed: {exc}")


class ImageTool(BaseTool):
    """Report image dimensions, format, and a base64 thumbnail of the first page."""

    name = "image"
    description = "Inspect image files (dimensions, format, size) and encode them as base64."
    category = "multimedia"
    timeout_seconds = 30.0
    tags = ["image"]

    parameters = [
        ToolParameter(name="path", type="string", required=True),
        ToolParameter(
            name="encoding",
            type="string",
            required=False,
            enum=["base64", "none"],
            default="base64",
        ),
        ToolParameter(name="max_bytes", type="integer", required=False, default=2 * 1024 * 1024),
    ]

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        path = Path(str(arguments.get("path", "")))
        if not path.is_file():
            return ["image file not found"]
        return []

    async def execute(self, arguments: dict[str, Any] | None = None) -> ToolResult:
        arguments = arguments or {}
        path = Path(str(arguments["path"]))
        data = path.read_bytes()
        if arguments.get("encoding") == "base64":
            from base64 import b64encode

            encoded = b64encode(data[: int(arguments.get("max_bytes") or 2 * 1024 * 1024)]).decode()
        else:
            encoded = None
        dimensions: dict[str, int] | None = None
        fmt: str | None = None
        try:
            from PIL import Image

            with Image.open(path) as image:
                dimensions = {"width": image.width, "height": image.height}
                fmt = image.format or path.suffix.lstrip(".")
        except ImportError:
            pass  # PIL optional - report size only
        except Exception:  # noqa: BLE001 - not an image
            fmt = path.suffix.lstrip(".")
        return self.ok(
            {
                "path": str(path),
                "bytes": len(data),
                "format": fmt,
                "dimensions": dimensions,
                "base64": encoded,
            }
        )


class AudioTool(BaseTool):
    """Inspect audio file metadata and extract basic signal characteristics."""

    name = "audio"
    description = "Report audio duration, channels, sample rate, and optional PCM characteristics."
    category = "multimedia"
    timeout_seconds = 30.0
    tags = ["audio"]

    parameters = [
        ToolParameter(name="path", type="string", required=True),
        ToolParameter(name="transcribe", type="boolean", required=False, default=False),
    ]

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        path = Path(str(arguments.get("path", "")))
        if not path.is_file():
            return ["audio file not found"]
        return []

    async def execute(self, arguments: dict[str, Any] | None = None) -> ToolResult:
        arguments = arguments or {}
        path = Path(str(arguments["path"]))
        suffix = path.suffix.lower()
        if suffix == ".wav":
            return await self._wav(path)
        return self.err(f"unsupported audio container: {suffix or 'unknown'}")

    async def _wav(self, path: Path) -> ToolResult:
        import struct

        with path.open("rb") as handle:
            riff = handle.read(12)
            if riff[:4] != b"RIFF":
                return self.err("not a RIFF/WAV file")
            fmt = handle.read(24)
            audio_format, channels, sample_rate, _, byte_rate, bits = (
                struct.unpack("<HHIIHH", fmt[:16]) if len(fmt) >= 16 else (0, 0, 0, 0, 0, 0)
            )
        data_size = path.stat().st_size - 44
        duration = data_size / (byte_rate or 1)
        return self.ok(
            {
                "format": audio_format,
                "channels": channels,
                "sample_rate": sample_rate,
                "bit_depth": bits,
                "data_bytes": data_size,
                "duration_seconds": round(duration, 3),
            }
        )


__all__ = ["AudioTool", "ImageTool", "PDFTool"]
