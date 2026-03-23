import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.session import get_db
from app.db.models import ContentItem, ContentVersion, User
from app.dependencies import require_owner
from app.tools.content import UpdateContentTool

router = APIRouter()
logger = logging.getLogger(__name__)
_update_tool = UpdateContentTool()


class ContentCreate(BaseModel):
    slug: str
    type: str
    title: str | None = None
    body: dict
    published: bool = False


class ContentUpdate(BaseModel):
    body: dict
    title: str | None = None
    publish: bool = False
    confirm: bool = False


@router.get("")
async def list_content(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner),
):
    result = await db.execute(
        select(ContentItem).order_by(desc(ContentItem.updated_at))
    )
    items = result.scalars().all()
    return [
        {
            "id": str(i.id),
            "slug": i.slug,
            "type": i.type,
            "title": i.title,
            "published": i.published,
            "updated_at": i.updated_at.isoformat() if i.updated_at else None,
        }
        for i in items
    ]


@router.get("/{slug}")
async def get_content(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner),
):
    result = await db.execute(select(ContentItem).where(ContentItem.slug == slug))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    return {
        "id": str(item.id),
        "slug": item.slug,
        "type": item.type,
        "title": item.title,
        "body": item.body,
        "published": item.published,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


@router.post("", status_code=201)
async def create_content(
    body: ContentCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner),
):
    slug = body.slug.strip().lower()
    existing = await db.execute(select(ContentItem).where(ContentItem.slug == slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Slug `{slug}` already exists.")

    valid_types = {"project", "post", "bio", "skill"}
    if body.type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid type. Must be one of: {valid_types}")

    item = ContentItem(
        slug=slug,
        type=body.type,
        title=body.title,
        body=body.body,
        published=body.published,
    )
    db.add(item)
    await db.flush()

    return {"id": str(item.id), "slug": item.slug, "type": item.type}


@router.patch("/{slug}")
async def update_content(
    slug: str,
    body: ContentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    result = await _update_tool.run(
        inputs={
            "slug": slug,
            "body": body.body,
            "title": body.title,
            "publish": body.publish,
            "confirm": body.confirm,
        },
        db=db,
        user_id=str(current_user.id),
    )
    if result.requires_confirmation:
        return {"requires_confirmation": True, "message": result.confirmation_message}
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.data


@router.delete("/{slug}")
async def delete_content(
    slug: str,
    confirm: bool = False,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner),
):
    if not confirm:
        return {
            "requires_confirmation": True,
            "message": f"Deleting `{slug}` is irreversible. Resend with ?confirm=true.",
        }

    result = await db.execute(select(ContentItem).where(ContentItem.slug == slug))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    # Soft delete: unpublish rather than hard delete
    item.published = False
    item.slug = f"__deleted__{item.slug}"
    await db.flush()

    logger.warning(f"Content soft-deleted: original_slug={slug}")
    return {"deleted": True, "slug": slug}


@router.get("/{slug}/versions")
async def get_versions(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner),
):
    result = await db.execute(select(ContentItem).where(ContentItem.slug == slug))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    versions_result = await db.execute(
        select(ContentVersion)
        .where(ContentVersion.content_id == item.id)
        .order_by(desc(ContentVersion.version))
    )
    versions = versions_result.scalars().all()
    return [
        {
            "version": v.version,
            "published": v.published,
            "created_at": v.created_at.isoformat(),
            "body_preview": str(v.body)[:200],
        }
        for v in versions
    ]


@router.post("/{slug}/restore/{version_num}")
async def restore_version(
    slug: str,
    version_num: int,
    confirm: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    if not confirm:
        return {
            "requires_confirmation": True,
            "message": f"Restoring version {version_num} of `{slug}` will overwrite current content. Add ?confirm=true.",
        }

    item_result = await db.execute(select(ContentItem).where(ContentItem.slug == slug))
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    ver_result = await db.execute(
        select(ContentVersion).where(
            ContentVersion.content_id == item.id,
            ContentVersion.version == version_num,
        )
    )
    version = ver_result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail=f"Version {version_num} not found")

    # Snapshot current state as a new version before restoring
    from sqlalchemy import func
    count_result = await db.execute(
        select(func.count()).where(ContentVersion.content_id == item.id)
    )
    new_version_num = (count_result.scalar() or 0) + 1
    snapshot = ContentVersion(
        content_id=item.id,
        version=new_version_num,
        body=item.body,
        published=item.published,
        created_by=str(current_user.id),
    )
    db.add(snapshot)

    item.body = version.body
    if version.published is not None:
        item.published = version.published
    await db.flush()

    return {"restored_version": version_num, "new_version": new_version_num, "slug": slug}