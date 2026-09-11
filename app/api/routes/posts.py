"""
Post ingestion endpoint: POST /posts

Accepts either a URL or pasted Markdown, stores it as a Post, and returns
the stored record. This is the very first step of the pipeline — everything
generated later (Day 4+) reads from what gets saved here.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Post
from app.schemas.post import PostCreate, PostResponse, SourceType
from app.services.content_fetcher import fetch_and_extract_text, ContentFetchError

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(payload: PostCreate, db: Session = Depends(get_db)) -> Post:
    if payload.source_type == SourceType.URL:
        try:
            title, extracted_text = fetch_and_extract_text(payload.source_content)
        except ContentFetchError as exc:
            # Bad input from the client's perspective (an unreachable/unusable URL)
            # -> 422, not a 500. The server didn't fail; the request was bad.
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not process URL: {exc}",
            ) from exc

        post = Post(
            source_type=payload.source_type.value,
            source_content=extracted_text,
            title=title,
        )
    else:
        # Markdown: store exactly what was pasted. First line becomes the
        # title if it looks like a Markdown heading, otherwise left blank.
        first_line = payload.source_content.strip().splitlines()[0]
        title = first_line.lstrip("#").strip() if first_line.startswith("#") else None

        post = Post(
            source_type=payload.source_type.value,
            source_content=payload.source_content,
            title=title,
        )

    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.get("/{post_id}", response_model=PostResponse)
def get_post(post_id: uuid.UUID, db: Session = Depends(get_db)) -> Post:
    post = db.get(Post, post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post {post_id} not found",
        )
    return post


@router.get("", response_model=list[PostResponse])
def list_posts(db: Session = Depends(get_db)) -> list[Post]:
    return db.query(Post).order_by(Post.created_at.desc()).all()