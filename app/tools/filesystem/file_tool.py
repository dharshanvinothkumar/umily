"""
Umily — Filesystem Tools

Provides safe filesystem manipulation tools: read, write, list, search, delete.
"""

import glob
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from loguru import logger


class FilesystemTool:
    """Handles file and directory operations."""

    def read_file(self, path: str) -> Dict[str, Any]:
        """Read text contents from a file."""
        file_path = Path(path).resolve()
        if not file_path.exists():
            return {"success": False, "error": f"File not found: {path}"}
        if not file_path.is_file():
            return {"success": False, "error": f"Path is not a file: {path}"}

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            return {
                "success": True,
                "message": f"Successfully read file: {path}",
                "content": content,
                "size_bytes": file_path.stat().st_size,
            }
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            return {"success": False, "error": str(e)}

    def write_file(self, path: str, content: str, append: bool = False) -> Dict[str, Any]:
        """Write text content to a file. Creates parent directories if missing."""
        file_path = Path(path).resolve()
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append else "w"
            with open(file_path, mode, encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "message": f"Successfully {'appended to' if append else 'wrote to'} file: {path}",
                "path": str(file_path),
            }
        except Exception as e:
            logger.error(f"Error writing to file {path}: {e}")
            return {"success": False, "error": str(e)}

    def list_directory(self, path: str = ".") -> Dict[str, Any]:
        """List files and subdirectories in a directory."""
        dir_path = Path(path).resolve()
        if not dir_path.exists():
            return {"success": False, "error": f"Directory not found: {path}"}
        if not dir_path.is_dir():
            return {"success": False, "error": f"Path is not a directory: {path}"}

        try:
            items = []
            for item in dir_path.iterdir():
                items.append({
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "size_bytes": item.stat().st_size if item.is_file() else 0,
                })
            return {
                "success": True,
                "message": f"Listed {len(items)} item(s) in {path}",
                "items": items,
                "count": len(items),
            }
        except Exception as e:
            logger.error(f"Error listing directory {path}: {e}")
            return {"success": False, "error": str(e)}

    def search_files(self, path: str, pattern: str = "*") -> Dict[str, Any]:
        """Search for files matching glob pattern inside path."""
        dir_path = Path(path).resolve()
        if not dir_path.exists():
            return {"success": False, "error": f"Directory not found: {path}"}

        try:
            search_glob = str(dir_path / "**" / pattern)
            matches = glob.glob(search_glob, recursive=True)
            results = [str(Path(m).resolve()) for m in matches[:100]]  # Cap at 100
            return {
                "success": True,
                "message": f"Found {len(results)} match(es) for pattern '{pattern}' in {path}",
                "matches": results,
                "count": len(results),
            }
        except Exception as e:
            logger.error(f"Error searching files in {path}: {e}")
            return {"success": False, "error": str(e)}

    def delete_file(self, path: str) -> Dict[str, Any]:
        """Delete a file safely."""
        file_path = Path(path).resolve()
        if not file_path.exists():
            return {"success": False, "error": f"File not found: {path}"}
        if file_path.is_dir():
            return {"success": False, "error": f"Path is a directory, not a file: {path}"}

        try:
            file_path.unlink()
            return {
                "success": True,
                "message": f"Successfully deleted file: {path}",
            }
        except Exception as e:
            logger.error(f"Error deleting file {path}: {e}")
            return {"success": False, "error": str(e)}
