"""
Deterministic, template-based variant generation — no AI call involved.
Produces a platform-appropriate draft from the stored Post.

Important: this module's job is only to produce a REASONABLE draft. It is
not responsible for guaranteeing the result passes validation — that's
constraint_profiles.validate_content()'s job, called separately by the API
route. Keeping these two concerns apart means the exact same validation
path is used whether a variant came from this generator or was typed by
a human via the manual-creation endpoint.
"""
import re

from app.db.models.post import Post
from app.db.models.variant import Platform
from app.services.constraint_profiles import get_profile


def _clean_source_text(raw: str) -> str:
    text = re.sub(r"^#+\s*", "", raw, flags=re.MULTILINE)  # strip markdown headings
    text = re.sub(r"[*_`]", "", text)                        # strip basic markdown emphasis
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _derive_hashtags(title: str | None, max_count: int) -> list[str]:
    if max_count <= 0:
        return []
    if not title:
        return ["#content"]
    words = re.findall(r"[A-Za-z]{4,}", title)
    tags = [f"#{w.capitalize()}" for w in words[:max_count]]
    return tags or ["#content"]


_TEMPLATES: dict[Platform, str] = {
    Platform.X: "{snippet} {hashtags}",
    Platform.LINKEDIN: "{snippet}\n\nWhat do you think? {hashtags}",
    Platform.INSTAGRAM: "{snippet} \u2728\n{hashtags}",
    Platform.TELEGRAM: "{snippet}\n\n{hashtags}",
}


def generate_variant_text(post: Post, platform: Platform) -> str:
    profile = get_profile(platform)
    cleaned = _clean_source_text(post.source_content)

    hashtags = _derive_hashtags(post.title, profile.max_hashtags)
    hashtag_str = " ".join(hashtags)

    template = _TEMPLATES[platform]
    # Reserve room for the template's fixed text + hashtags; give the rest to the snippet.
    fixed_overhead = len(template.format(snippet="", hashtags=hashtag_str))
    snippet_budget = max(profile.max_length - fixed_overhead, 20)

    if len(cleaned) > snippet_budget:
        snippet = cleaned[: snippet_budget - 1].rstrip() + "\u2026"
    else:
        snippet = cleaned

    return template.format(snippet=snippet, hashtags=hashtag_str).strip()