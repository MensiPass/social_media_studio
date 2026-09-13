"""
The SocialPublisher interface. Every platform-specific publisher — real or
mock — implements this one contract. Business logic (the Day 9 scheduler)
only ever calls .publish() on whatever object it's handed; it never knows
or cares whether that's a real Telegram bot or a mock recording to memory.

This is the Adapter pattern: swapping implementations never touches the
code that calls them.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PublishResult:
    success: bool
    external_post_id: str | None
    detail: str


class SocialPublisher(ABC):
    @abstractmethod
    def publish(self, content: str) -> PublishResult:
        """
        Attempt to publish `content`. Must never raise for EXPECTED failure
        cases (network errors, platform rejections, etc.) — return
        PublishResult(success=False, ...) instead, so the caller can record
        a PublishAttempt without crashing. Only let truly unexpected
        programmer errors (bugs) propagate as exceptions.
        """
        raise NotImplementedError