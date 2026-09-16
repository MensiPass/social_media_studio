"""
Smoke test for the adapter pattern: interface enforcement, both mock
adapters, and the registry that maps platforms to publishers.

Run with:
    python scripts/smoke_test_adapters.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.adapters.base import SocialPublisher
from app.adapters.mock_x_adapter import MockXPublisher
from app.adapters.mock_instagram_adapter import MockInstagramPublisher
from app.adapters.telegram_adapter import TelegramPublisher
from app.adapters.linkedin_adapter import LinkedInPublisher
from app.adapters import registry
from app.db.models.variant import Platform


def publish_via_registry(platform: Platform, content: str):
    """
    This function is the whole point of today's work: it has ZERO
    knowledge of which platforms exist or how they differ. It just asks
    the registry for whatever publisher is configured, and calls the one
    method every publisher promises to have. Adding Telegram/LinkedIn
    later, or swapping a mock for a real adapter, never touches this
    function.
    """
    publisher = registry.get_publisher(platform)
    return publisher.publish(content)


def main() -> None:
    print("1) Confirming SocialPublisher can't be instantiated directly (it's abstract)...")
    try:
        SocialPublisher()
        print("    Should have raised TypeError!")
    except TypeError as e:
        print(f"    Correctly refused: {e}\n")

    print("2) Testing MockXPublisher directly...")
    x_publisher = MockXPublisher()
    result = x_publisher.publish("Foxes are clever animals. #wildlife")
    assert result.success is True
    assert result.external_post_id.startswith("mock-x-")
    assert len(x_publisher.sent_posts) == 1
    print(f"    Published successfully: {result.detail}")
    print(f"    Recorded in sent_posts: {x_publisher.sent_posts[0]['external_post_id']}\n")

    print("3) Testing MockInstagramPublisher directly...")
    ig_publisher = MockInstagramPublisher()
    result = ig_publisher.publish("Foxes are clever animals. #wildlife")
    assert result.success is True
    assert result.external_post_id.startswith("mock-ig-")
    print(f"    Published successfully: {result.detail}\n")

    print("4) Using the registry to publish to X and Instagram with the SAME calling code...")
    result_x = publish_via_registry(Platform.X, "Test post via registry")
    result_ig = publish_via_registry(Platform.INSTAGRAM, "Test post via registry")
    assert result_x.success and result_ig.success
    print(f"    X via registry:         {result_x.external_post_id}")
    print(f"    Instagram via registry: {result_ig.external_post_id}")
    print("    Same function, same call, correctly routed to two different adapters.\n")

    print("5) Confirming Telegram and LinkedIn are now BOTH real, registered publishers...")
    telegram_publisher = registry.get_publisher(Platform.TELEGRAM)
    linkedin_publisher = registry.get_publisher(Platform.LINKEDIN)
    assert isinstance(telegram_publisher, TelegramPublisher)
    assert isinstance(linkedin_publisher, LinkedInPublisher)
    print("    Telegram returns a real TelegramPublisher instance.")
    print("    LinkedIn returns a real LinkedInPublisher instance.")
    print("   (Actual message-sending is tested separately in the live test scripts)\n")

    print("SMOKE TEST PASSED — adapter interface, mocks, and registry all work correctly.")


if __name__ == "__main__":
    main()