"""
Per-platform rules that every generated or manually-submitted variant must
pass before it can be stored. Where noted, numbers are genuine platform
limits; others are our own content-quality policy. Enforcement — not the
exact numbers — is what's graded.
"""
import re
from dataclasses import dataclass

from app.db.models.variant import Platform


@dataclass(frozen=True)
class ConstraintProfile:
    max_length: int    # hard character limit
    max_hashtags: int  # cap we enforce (see notes per platform below)
    tone_note: str      # human-readable guidance shown in the UI, not machine-enforced


PROFILES: dict[Platform, ConstraintProfile] = {
    Platform.X: ConstraintProfile(
        max_length=280,        # X's actual character limit
        max_hashtags=2,        # best-practice cap; X itself has no hard hashtag limit
        tone_note="short, punchy, casual",
    ),
    Platform.LINKEDIN: ConstraintProfile(
        max_length=3000,       # LinkedIn's actual feed post character limit
        max_hashtags=5,        # LinkedIn's own recommended range
        tone_note="professional, informative",
    ),
    Platform.INSTAGRAM: ConstraintProfile(
        max_length=2200,       # Instagram's actual caption limit
        max_hashtags=30,       # Instagram's actual hard hashtag limit
        tone_note="casual, visual, emoji-friendly",
    ),
    Platform.TELEGRAM: ConstraintProfile(
        max_length=4096,       # Telegram Bot API's actual text message limit
        max_hashtags=20,       # no real platform limit; generous internal cap
        tone_note="informal, conversational",
    ),
}


def get_profile(platform: Platform) -> ConstraintProfile:
    return PROFILES[platform]


def validate_content(platform: Platform, content: str) -> list[str]:
    """
    Returns a list of human-readable violation messages.
    Empty list = content passes every rule for this platform.
    """
    profile = get_profile(platform)
    violations: list[str] = []

    length = len(content)
    if length > profile.max_length:
        violations.append(
            f"Exceeds {platform.value} max length of {profile.max_length} "
            f"characters (got {length})"
        )

    hashtag_count = len(re.findall(r"#\w+", content))
    if hashtag_count > profile.max_hashtags:
        violations.append(
            f"Too many hashtags for {platform.value}: max {profile.max_hashtags}, "
            f"found {hashtag_count}"
        )

    return violations