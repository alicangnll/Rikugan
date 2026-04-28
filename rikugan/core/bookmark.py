"""Code bookmarking system for marking important locations.

Allows users to bookmark functions, addresses, and code regions with
notes, categories, and tags for easy navigation and organization.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class BookmarkCategory(str, Enum):
    """Categories for bookmarks."""

    INTERESTING = "interesting"
    VULNERABILITY = "vulnerability"
    CRITICAL = "critical"
    ALGORITHM = "algorithm"
    OBFUSCATED = "obfuscated"
    ANTI_DEBUG = "anti_debug"
    ANTI_VM = "anti_vm"
    CRYPTO = "crypto"
    NETWORK = "network"
    FILE_IO = "file_io"
    STRING = "string"
    IMPORT = "import"
    EXPORT = "export"
    CUSTOM = "custom"


class BookmarkType(str, Enum):
    """Types of bookmarked locations."""

    FUNCTION = "function"
    ADDRESS = "address"
    RANGE = "range"
    STRING = "string"
    STRUCTURE = "structure"


@dataclass
class Bookmark:
    """A single bookmark."""

    id: str  # Unique ID
    name: str
    bookmark_type: BookmarkType
    category: BookmarkCategory
    address: int  # Primary address
    end_address: int | None = None  # For range bookmarks
    function_name: str = ""  # Associated function name
    notes: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    modified_at: str = ""
    color: str = "#FFFF00"  # Default yellow highlight

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.modified_at:
            self.modified_at = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert bookmark to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.bookmark_type.value,
            "category": self.category.value,
            "address": self.address,
            "end_address": self.end_address,
            "function_name": self.function_name,
            "notes": self.notes,
            "tags": self.tags,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "color": self.color,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Bookmark:
        """Create bookmark from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            bookmark_type=BookmarkType(data["type"]),
            category=BookmarkCategory(data["category"]),
            address=data["address"],
            end_address=data.get("end_address"),
            function_name=data.get("function_name", ""),
            notes=data.get("notes", ""),
            tags=data.get("tags", []),
            created_at=data.get("created_at", ""),
            modified_at=data.get("modified_at", ""),
            color=data.get("color", "#FFFF00"),
        )


class BookmarkManager:
    """Manages code bookmarks with persistence."""

    def __init__(self, config_path: Path | None = None):
        self._bookmarks: dict[str, Bookmark] = {}
        self._config_path = config_path
        self._address_index: dict[int, list[str]] = {}  # address -> bookmark IDs
        self._category_index: dict[BookmarkCategory, list[str]] = {}  # category -> bookmark IDs
        self._tag_index: dict[str, list[str]] = {}  # tag -> bookmark IDs

        if config_path and config_path.exists():
            self.load_from_file(config_path)

    def add_bookmark(
        self,
        name: str,
        bookmark_type: BookmarkType,
        category: BookmarkCategory,
        address: int,
        end_address: int | None = None,
        function_name: str = "",
        notes: str = "",
        tags: list[str] | None = None,
        color: str = "#FFFF00",
    ) -> Bookmark:
        """Add a new bookmark.

        Args:
            name: Bookmark name
            bookmark_type: Type of bookmark
            category: Bookmark category
            address: Primary address
            end_address: End address for ranges
            function_name: Associated function name
            notes: Notes
            tags: Tags
            color: Highlight color

        Returns:
            Created bookmark
        """
        bookmark_id = f"bm_{address:x}_{datetime.now().timestamp()}"

        bookmark = Bookmark(
            id=bookmark_id,
            name=name,
            bookmark_type=bookmark_type,
            category=category,
            address=address,
            end_address=end_address,
            function_name=function_name,
            notes=notes,
            tags=tags or [],
            color=color,
        )

        self._bookmarks[bookmark_id] = bookmark
        self._index_bookmark(bookmark)

        return bookmark

    def remove_bookmark(self, bookmark_id: str) -> bool:
        """Remove a bookmark by ID."""
        if bookmark_id not in self._bookmarks:
            return False

        bookmark = self._bookmarks[bookmark_id]
        self._unindex_bookmark(bookmark)
        del self._bookmarks[bookmark_id]

        return True

    def update_bookmark(
        self,
        bookmark_id: str,
        name: str | None = None,
        category: BookmarkCategory | None = None,
        notes: str | None = None,
        tags: list[str] | None = None,
        color: str | None = None,
    ) -> bool:
        """Update an existing bookmark.

        Args:
            bookmark_id: Bookmark ID
            name: New name
            category: New category
            notes: New notes
            tags: New tags
            color: New color

        Returns:
            True if updated, False if not found
        """
        bookmark = self._bookmarks.get(bookmark_id)
        if not bookmark:
            return False

        # Unindex before updating
        self._unindex_bookmark(bookmark)

        # Update fields
        if name is not None:
            bookmark.name = name
        if category is not None:
            bookmark.category = category
        if notes is not None:
            bookmark.notes = notes
        if tags is not None:
            bookmark.tags = tags
        if color is not None:
            bookmark.color = color

        bookmark.modified_at = datetime.now().isoformat()

        # Reindex
        self._index_bookmark(bookmark)

        return True

    def get_bookmark(self, bookmark_id: str) -> Bookmark | None:
        """Get a bookmark by ID."""
        return self._bookmarks.get(bookmark_id)

    def get_bookmarks_at_address(self, address: int) -> list[Bookmark]:
        """Get all bookmarks at a specific address."""
        bookmark_ids = self._address_index.get(address, [])
        return [self._bookmarks[bid] for bid in bookmark_ids if bid in self._bookmarks]

    def get_bookmarks_in_range(self, start: int, end: int) -> list[Bookmark]:
        """Get all bookmarks within an address range."""
        results = []
        for bookmark in self._bookmarks.values():
            if start <= bookmark.address <= end:
                results.append(bookmark)
            elif bookmark.end_address and start <= bookmark.end_address <= end:
                results.append(bookmark)
        return results

    def get_bookmarks_by_category(self, category: BookmarkCategory) -> list[Bookmark]:
        """Get all bookmarks in a category."""
        bookmark_ids = self._category_index.get(category, [])
        return [self._bookmarks[bid] for bid in bookmark_ids if bid in self._bookmarks]

    def get_bookmarks_by_tag(self, tag: str) -> list[Bookmark]:
        """Get all bookmarks with a specific tag."""
        bookmark_ids = self._tag_index.get(tag, [])
        return [self._bookmarks[bid] for bid in bookmark_ids if bid in self._bookmarks]

    def search_bookmarks(self, query: str) -> list[Bookmark]:
        """Search bookmarks by name, notes, or tags."""
        query_lower = query.lower()
        results = []

        for bookmark in self._bookmarks.values():
            if (
                query_lower in bookmark.name.lower()
                or query_lower in bookmark.notes.lower()
                or any(query_lower in tag.lower() for tag in bookmark.tags)
            ):
                results.append(bookmark)

        return results

    def list_all_bookmarks(self, sort_by: str = "created_at") -> list[Bookmark]:
        """List all bookmarks.

        Args:
            sort_by: Sort field (created_at, modified_at, name, address)
        """
        bookmarks = list(self._bookmarks.values())

        if sort_by == "created_at":
            bookmarks.sort(key=lambda b: b.created_at, reverse=True)
        elif sort_by == "modified_at":
            bookmarks.sort(key=lambda b: b.modified_at, reverse=True)
        elif sort_by == "name":
            bookmarks.sort(key=lambda b: b.name.lower())
        elif sort_by == "address":
            bookmarks.sort(key=lambda b: b.address)

        return bookmarks

    def get_categories(self) -> dict[BookmarkCategory, int]:
        """Get count of bookmarks per category."""
        counts = {cat: 0 for cat in BookmarkCategory}
        for bookmark in self._bookmarks.values():
            counts[bookmark.category] += 1
        return counts

    def get_tags(self) -> dict[str, int]:
        """Get count of bookmarks per tag."""
        counts: dict[str, int] = {}
        for bookmark in self._bookmarks.values():
            for tag in bookmark.tags:
                counts[tag] = counts.get(tag, 0) + 1
        return counts

    def save_to_file(self, path: Path) -> None:
        """Save bookmarks to a JSON file."""
        data = {"version": "1.0", "bookmarks": [bm.to_dict() for bm in self._bookmarks.values()]}

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load_from_file(self, path: Path) -> None:
        """Load bookmarks from a JSON file."""
        if not path.exists():
            return

        with open(path) as f:
            data = json.load(f)

        self._bookmarks.clear()
        self._address_index.clear()
        self._category_index.clear()
        self._tag_index.clear()

        for bm_data in data.get("bookmarks", []):
            bookmark = Bookmark.from_dict(bm_data)
            self._bookmarks[bookmark.id] = bookmark
            self._index_bookmark(bookmark)

    def _index_bookmark(self, bookmark: Bookmark) -> None:
        """Add bookmark to indices."""
        # Address index
        if bookmark.address not in self._address_index:
            self._address_index[bookmark.address] = []
        self._address_index[bookmark.address].append(bookmark.id)

        # Category index
        if bookmark.category not in self._category_index:
            self._category_index[bookmark.category] = []
        self._category_index[bookmark.category].append(bookmark.id)

        # Tag index
        for tag in bookmark.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            self._tag_index[tag].append(bookmark.id)

    def _unindex_bookmark(self, bookmark: Bookmark) -> None:
        """Remove bookmark from indices."""
        # Address index
        if bookmark.address in self._address_index:
            self._address_index[bookmark.address] = [
                bid for bid in self._address_index[bookmark.address] if bid != bookmark.id
            ]

        # Category index
        if bookmark.category in self._category_index:
            self._category_index[bookmark.category] = [
                bid for bid in self._category_index[bookmark.category] if bid != bookmark.id
            ]

        # Tag index
        for tag in bookmark.tags:
            if tag in self._tag_index:
                self._tag_index[tag] = [bid for bid in self._tag_index[tag] if bid != bookmark.id]
