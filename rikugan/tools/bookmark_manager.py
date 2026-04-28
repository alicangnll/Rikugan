"""Code bookmarking tool for Rikugan.

Allows users to bookmark functions, addresses, and code regions with
notes, categories, and tags for easy navigation and organization.
"""

from __future__ import annotations

from pathlib import Path

from ..core.bookmark import BookmarkCategory, BookmarkManager, BookmarkType
from ..tools.base import Tool, ToolDefinition


class BookmarkManagerTool(Tool):
    """Code bookmarking management tool."""

    name = "bookmark_manager"
    description = "Bookmark important code locations with notes and categories"
    parameters = {
        "action": {
            "description": "Action to perform: add, remove, update, list, search, stats",
            "type": "string",
            "default": "list",
            "enum": ["add", "remove", "update", "list", "search", "stats"],
        },
        "name": {
            "description": "Bookmark name (for add/update)",
            "type": "string",
            "required": False,
        },
        "bookmark_id": {
            "description": "Bookmark ID (for remove/update)",
            "type": "string",
            "required": False,
        },
        "address": {
            "description": "Function/address to bookmark (for add)",
            "type": "string",
            "required": False,
        },
        "category": {
            "description": "Bookmark category (for add/update)",
            "type": "string",
            "default": "interesting",
            "enum": [
                "interesting",
                "vulnerability",
                "critical",
                "algorithm",
                "obfuscated",
                "anti_debug",
                "anti_vm",
                "crypto",
                "network",
                "file_io",
                "string",
                "import",
                "export",
                "custom",
            ],
        },
        "notes": {
            "description": "Notes for the bookmark",
            "type": "string",
            "required": False,
        },
        "tags": {
            "description": "Comma-separated tags",
            "type": "string",
            "required": False,
        },
        "color": {
            "description": "Highlight color (hex code)",
            "type": "string",
            "default": "#FFFF00",
        },
        "query": {
            "description": "Search query (for search action)",
            "type": "string",
            "required": False,
        },
        "sort_by": {
            "description": "Sort field for list (created_at, modified_at, name, address)",
            "type": "string",
            "default": "created_at",
        },
    }

    def __init__(self, config_path: Path | None = None):
        super().__init__()
        self._manager = BookmarkManager(config_path)

    def execute(
        self,
        action: str = "list",
        name: str = "",
        bookmark_id: str = "",
        address: str = "",
        category: str = "interesting",
        notes: str = "",
        tags: str = "",
        color: str = "#FFFF00",
        query: str = "",
        sort_by: str = "created_at",
    ) -> str:
        """Execute bookmark management action.

        Args:
            action: Action to perform
            name: Bookmark name
            bookmark_id: Bookmark ID
            address: Address to bookmark
            category: Category
            notes: Notes
            tags: Tags (comma-separated)
            color: Highlight color
            query: Search query
            sort_by: Sort field

        Returns:
            Result message
        """
        if action == "add":
            return self._add_bookmark(name, address, category, notes, tags, color)
        elif action == "remove":
            return self._remove_bookmark(bookmark_id)
        elif action == "update":
            return self._update_bookmark(bookmark_id, name, category, notes, tags, color)
        elif action == "list":
            return self._list_bookmarks(sort_by)
        elif action == "search":
            return self._search_bookmarks(query)
        elif action == "stats":
            return self._show_stats()
        else:
            return f"Unknown action: {action}"

    def _add_bookmark(self, name: str, address: str, category: str, notes: str, tags: str, color: str) -> str:
        """Add a new bookmark."""
        if not name:
            return "Error: Bookmark name is required"

        if not address:
            return "Error: Address is required"

        # Parse address
        try:
            addr = int(address, 16) if address.startswith("0x") else int(address)
        except ValueError:
            return f"Error: Invalid address: {address}"

        # Parse tags
        tag_list = [t.strip() for t in tags.split(",")] if tags else []

        # Get function name if available
        func_name = self._get_function_name(addr)

        # Create bookmark
        bookmark = self._manager.add_bookmark(
            name=name,
            bookmark_type=BookmarkType.ADDRESS,
            category=BookmarkCategory(category),
            address=addr,
            function_name=func_name,
            notes=notes,
            tags=tag_list,
            color=color,
        )

        return f"✓ Added bookmark '{name}' at 0x{addr:x} (ID: {bookmark.id})"

    def _remove_bookmark(self, bookmark_id: str) -> str:
        """Remove a bookmark."""
        if not bookmark_id:
            return "Error: Bookmark ID is required"

        if self._manager.remove_bookmark(bookmark_id):
            return f"✓ Removed bookmark {bookmark_id}"
        else:
            return f"Error: Bookmark {bookmark_id} not found"

    def _update_bookmark(self, bookmark_id: str, name: str, category: str, notes: str, tags: str, color: str) -> str:
        """Update a bookmark."""
        if not bookmark_id:
            return "Error: Bookmark ID is required"

        # Parse tags
        tag_list = [t.strip() for t in tags.split(",")] if tags else None

        # Update
        success = self._manager.update_bookmark(
            bookmark_id=bookmark_id,
            name=name if name else None,
            category=BookmarkCategory(category) if category else None,
            notes=notes if notes else None,
            tags=tag_list,
            color=color if color else None,
        )

        if success:
            return f"✓ Updated bookmark {bookmark_id}"
        else:
            return f"Error: Bookmark {bookmark_id} not found"

    def _list_bookmarks(self, sort_by: str) -> str:
        """List all bookmarks."""
        bookmarks = self._manager.list_all_bookmarks(sort_by=sort_by)

        if not bookmarks:
            return "No bookmarks found"

        lines = []
        lines.append(f"=== Bookmarks ({len(bookmarks)}) ===")
        lines.append("")

        for bookmark in bookmarks:
            lines.append(f"[{bookmark.category.value}] {bookmark.name}")
            lines.append(f"  ID: {bookmark.id}")
            lines.append(f"  Address: 0x{bookmark.address:x}")
            if bookmark.function_name:
                lines.append(f"  Function: {bookmark.function_name}")
            if bookmark.notes:
                lines.append(f"  Notes: {bookmark.notes}")
            if bookmark.tags:
                lines.append(f"  Tags: {', '.join(bookmark.tags)}")
            lines.append(f"  Created: {bookmark.created_at}")
            lines.append("")

        return "\n".join(lines)

    def _search_bookmarks(self, query: str) -> str:
        """Search bookmarks."""
        if not query:
            return "Error: Search query is required"

        results = self._manager.search_bookmarks(query)

        if not results:
            return f"No results for query: {query}"

        lines = []
        lines.append(f"=== Search Results: '{query}' ({len(results)} found) ===")
        lines.append("")

        for bookmark in results:
            lines.append(f"[{bookmark.category.value}] {bookmark.name}")
            lines.append(f"  Address: 0x{bookmark.address:x}")
            if bookmark.notes:
                lines.append(f"  Notes: {bookmark.notes}")
            lines.append("")

        return "\n".join(lines)

    def _show_stats(self) -> str:
        """Show bookmark statistics."""
        lines = []
        lines.append("=== Bookmark Statistics ===")
        lines.append("")

        categories = self._manager.get_categories()
        lines.append(f"Total bookmarks: {sum(categories.values())}")
        lines.append("")
        lines.append("By Category:")

        for cat, count in categories.items():
            if count > 0:
                lines.append(f"  {cat.value}: {count}")

        tags = self._manager.get_tags()
        if tags:
            lines.append("")
            lines.append("Top Tags:")
            sorted_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)[:10]
            for tag, count in sorted_tags:
                lines.append(f"  {tag}: {count}")

        return "\n".join(lines)

    def _get_function_name(self, address: int) -> str:
        """Get function name at address (placeholder for host integration)."""
        # This would be implemented by host-specific code
        return ""


def get_tool_definition() -> ToolDefinition:
    """Return tool definition for Rikugan tool registry."""
    return ToolDefinition(
        name=BookmarkManagerTool.name,
        description=BookmarkManagerTool.description,
        parameters=BookmarkManagerTool.parameters,
        function=BookmarkManagerTool.execute,
    )
