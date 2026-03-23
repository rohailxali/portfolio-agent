import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.tools.base import BaseTool, ToolResult
from app.db.models import ContentItem, ContentVersion

logger = logging.getLogger(__name__)


class UpdateContentTool(BaseTool):
    name = "update_content"
    description = (
        "Update a portfolio content item (project, bio, post, skill). "
        "Creates a versioned snapshot before overwriting. "
        "Publishing requires explicit confirmation."
    )
    requires_confirmation = False  # Handled dynamically for publish

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "slug": {
                    "type": "string",
                    "description": "Unique slug of the content item to update.",
                },
                "body": {
                    "type": "object",
                    "description": "Full content body as a JSON object.",
                },
                "title": {"type": "string"},
                "publish": {
                    "type": "boolean",
                    "default": False,
                    "description": "Set to true to publish. Requires confirm=true.",
                },
                "confirm": {
                    "type": "boolean",
                    "default": False,
                },
            },
            "required": ["slug", "body"],
        }

    async def _execute(self, inputs: dict, db: AsyncSession, user_id: str) -> ToolResult:
        slug = inputs["slug"].strip().lower()
        publish = inputs.get("publish", False)
        confirm = inputs.get("confirm", False)

        # Publishing is a destructive action — require confirmation
        if publish and not confirm:
            return ToolResult(
                success=False,
                requires_confirmation=True,
                confirmation_message=(
                    f"Publishing `{slug}` will make it live on the site. "
                    f"Re-send with confirm=true to proceed."
                ),
            )

        result = await db.execute(
            select(ContentItem).where(ContentItem.slug == slug)
        )
        item = result.scalar_one_or_none()

        if not item:
            return ToolResult(success=False, error=f"Content item `{slug}` not found.")

        # Snapshot current version before overwriting
        version_count_result = await db.execute(
            select(func.count()).where(ContentVersion.content_id == item.id)
        )
        current_version_num = (version_count_result.scalar() or 0) + 1

        snapshot = ContentVersion(
            content_id=item.id,
            version=current_version_num,
            body=item.body,
            published=item.published,
            created_by=user_id,
        )
        db.add(snapshot)

        # Apply update
        item.body = inputs["body"]
        if "title" in inputs:
            item.title = inputs["title"]
        if publish:
            item.published = True

        await db.flush()
        logger.info(f"Content updated: slug={slug} version={current_version_num} published={item.published}")

        return ToolResult(
            success=True,
            data={
                "content_id": str(item.id),
                "slug": item.slug,
                "version": current_version_num,
                "published": item.published,
            },
        )