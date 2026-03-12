"""Build news blocks from sentence units."""

from __future__ import annotations

import re

from .models import SentenceUnit


HARD_TRANSITION_MARKERS = (
    "接下来",
    "再说",
    "另外",
    "下面",
    "下一条",
    "最后",
)


def text_signature(text: str) -> set[str]:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", "", text)
    if len(cleaned) < 2:
        return {cleaned} if cleaned else set()
    return {cleaned[idx : idx + 2] for idx in range(len(cleaned) - 1)}


def similarity(left: str, right: str) -> float:
    left_sig = text_signature(left)
    right_sig = text_signature(right)
    if not left_sig or not right_sig:
        return 0.0
    intersection = len(left_sig & right_sig)
    union = len(left_sig | right_sig)
    return intersection / union if union else 0.0


def assign_blocks(sentence_units: list[SentenceUnit]) -> tuple[list[list[SentenceUnit]], set[str]]:
    blocks: list[list[SentenceUnit]] = []
    needs_review: set[str] = set()

    for sentence in sentence_units:
        if sentence.sentence_type == "noise":
            sentence.review_status = "skipped"
            continue

        if not blocks:
            blocks.append([sentence])
            continue

        current_block = blocks[-1]
        block_context = "".join(item.text for item in current_block[-4:])
        boundary_score = similarity(block_context, sentence.text)
        starts_new = should_start_new_block(current_block, sentence, boundary_score, block_context)

        if starts_new:
            blocks.append([sentence])
            if boundary_score < 0.12 and sentence.sentence_type != "transition":
                needs_review.add(sentence.sentence_id)
        else:
            current_block.append(sentence)

    return blocks, needs_review


def should_start_new_block(
    current_block: list[SentenceUnit],
    candidate: SentenceUnit,
    boundary_score: float,
    block_context: str,
) -> bool:
    if candidate.text.startswith(HARD_TRANSITION_MARKERS) and len(current_block) >= 3:
        return True

    block_topic = block_context or current_block[-1].topic_hint
    topic_shift = similarity(block_topic, candidate.topic_hint)
    time_gap = max(candidate.start - current_block[-1].end, 0.0)

    if time_gap > 20.0:
        return True

    return False
