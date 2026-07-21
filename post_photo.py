#!/usr/bin/env python3
"""
Daily photo poster.

What it does, every time it runs:
1. Finds the oldest image in inbox/
2. Sends it to Claude to generate a caption
3. Posts it (image + caption) to every Buffer channel you've configured
4. Moves the image from inbox/ to posted/ so it won't be posted again

Run manually with:  python post_photo.py
Meant to be run on a schedule via .github/workflows/post.yml
"""

import base64
import mimetypes
import os
import subprocess
import sys
from pathlib import Path

import requests

# ---- Config (all pulled from environment variables / GitHub secrets) ----
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
BUFFER_API_KEY = os.environ["BUFFER_API_KEY"]
BUFFER_CHANNEL_IDS = [c.strip() for c in os.environ["BUFFER_CHANNEL_IDS"].split(",") if c.strip()]

# Set by GitHub Actions automatically. Falls back to sensible defaults for local runs.
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")  # e.g. "yourname/photo-poster"
GITHUB_BRANCH = os.environ.get("GITHUB_REF_NAME", "main")

INBOX_DIR = Path("inbox")
POSTED_DIR = Path("posted")

CLAUDE_MODEL = "claude-sonnet-5"
CAPTION_STYLE_PROMPT = (
    "You write short, evocative Instagram-style captions for photography posts. "
    "Look at this photo and write ONE caption for it: warm, specific, not cheesy, "
    "no hashtags, no emoji spam (at most one emoji if it truly fits), under 200 characters. "
    "Reply with ONLY the caption text, nothing else."
)


def pick_next_image() -> Path:
    images = sorted(
        p for p in INBOX_DIR.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )
    if not images:
        print("No images left in inbox/. Nothing to post today.")
        sys.exit(0)
    return images[0]


def generate_caption(image_path: Path) -> str:
    media_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
    image_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": CLAUDE_MODEL,
            "max_tokens": 200,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": media_type, "data": image_b64},
                        },
                        {"type": "text", "text": CAPTION_STYLE_PROMPT},
                    ],
                }
            ],
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    caption = "".join(block["text"] for block in data["content"] if block["type"] == "text").strip()
    return caption


def public_url_for(image_path: Path) -> str:
    if not GITHUB_REPOSITORY:
        raise RuntimeError(
            "GITHUB_REPOSITORY isn't set. This script expects to run inside GitHub Actions "
            "on a PUBLIC repo, since Buffer needs a publicly reachable image URL."
        )
    return f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/{GITHUB_BRANCH}/{image_path.as_posix()}"


def create_buffer_post(channel_id: str, caption: str, image_url: str) -> None:
    query = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post { id }
        }
        ... on MutationError {
          message
        }
      }
    }
    """
    variables = {
        "input": {
            "text": caption,
            "channelId": channel_id,
            "schedulingType": "automatic",
            "mode": "addToQueue",
            "assets": [{"image": {"url": image_url}}],
        }
    }
    resp = requests.post(
        "https://api.buffer.com",
        headers={
            "Authorization": f"Bearer {BUFFER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"query": query, "variables": variables},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("errors"):
        raise RuntimeError(f"Buffer API error for channel {channel_id}: {data['errors']}")

    result = data["data"]["createPost"]
    if "message" in result:
        raise RuntimeError(f"Buffer rejected the post for channel {channel_id}: {result['message']}")

    print(f"  -> Queued on channel {channel_id} (post id: {result['post']['id']})")


def move_to_posted(image_path: Path) -> None:
    POSTED_DIR.mkdir(exist_ok=True)
    dest = POSTED_DIR / image_path.name
    subprocess.run(["git", "mv", str(image_path), str(dest)], check=True)


def main() -> None:
    image_path = pick_next_image()
    print(f"Selected image: {image_path}")

    caption = generate_caption(image_path)
    print(f"Caption: {caption}")

    image_url = public_url_for(image_path)
    print(f"Public URL: {image_url}")

    print("Posting to Buffer channels...")
    for channel_id in BUFFER_CHANNEL_IDS:
        create_buffer_post(channel_id, caption, image_url)

    move_to_posted(image_path)
    print(f"Moved {image_path.name} to posted/. Done.")


if __name__ == "__main__":
    main()
