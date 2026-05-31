"""
VSS Digital — Facebook + Instagram Publisher

Objavljuje sadržaj na Facebook Page i Instagram Business Account.
Koristi Meta Graph API.
"""

import os
import json
import requests
from pathlib import Path


GRAPH_API = "https://graph.facebook.com/v22.0"


def get_page_token() -> str:
    return os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", "")


def get_page_id(token: str) -> str:
    """Dohvati Facebook Page ID iz tokena."""
    resp = requests.get(
        f"{GRAPH_API}/me/accounts",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json().get("data", [])
    if data:
        return data[0]["id"]
    # Fallback: probaj /me
    resp = requests.get(
        f"{GRAPH_API}/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def get_instagram_id(page_id: str, token: str) -> str | None:
    """Dohvati Instagram Business Account ID povezan s Pageom."""
    resp = requests.get(
        f"{GRAPH_API}/{page_id}",
        params={
            "fields": "instagram_business_account",
            "access_token": token,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    ig = data.get("instagram_business_account")
    if ig:
        return ig["id"]
    return None


def post_to_facebook(text: str, image_path: str | None = None) -> dict:
    """
    Objavi na Facebook Page.
    """
    token = get_page_token()
    if not token:
        raise ValueError("FACEBOOK_PAGE_ACCESS_TOKEN nije postavljen")

    page_id = get_page_id(token)
    print(f"  → Facebook Page ID: {page_id}")

    if image_path and Path(image_path).exists():
        # Objava sa slikom
        with open(image_path, "rb") as f:
            resp = requests.post(
                f"{GRAPH_API}/{page_id}/photos",
                params={"access_token": token, "message": text},
                files={"source": f},
                timeout=30,
            )
    else:
        # Samo tekst
        resp = requests.post(
            f"{GRAPH_API}/{page_id}/feed",
            params={"access_token": token, "message": text},
            timeout=15,
        )

    resp.raise_for_status()
    post_id = resp.json().get("id", "")
    return {"success": True, "post_id": post_id, "platform": "facebook"}


def post_to_instagram(text: str, image_path: str | None = None) -> dict | None:
    """
    Objavi na Instagram Business Account.
    Instagram zahtijeva sliku (image_url) + caption.
    """
    token = get_page_token()
    if not token:
        raise ValueError("FACEBOOK_PAGE_ACCESS_TOKEN nije postavljen")

    page_id = get_page_id(token)
    ig_id = get_instagram_id(page_id, token)

    if not ig_id:
        print("  ℹ Instagram Business Account nije povezan — preskačem")
        return None

    print(f"  → Instagram ID: {ig_id}")

    if image_path and Path(image_path).exists():
        # Instagram zahtijeva image_url — uploadaj na server
        with open(image_path, "rb") as f:
            media_resp = requests.post(
                f"{GRAPH_API}/{ig_id}/media",
                params={
                    "access_token": token,
                    "image_url": None,  # Ne možemo direktno upload file za IG
                    "caption": text,
                },
                files={"source": f},
                timeout=30,
            )

        # Alternativa: probaj s media upload
        media_resp = requests.post(
            f"{GRAPH_API}/{ig_id}/media",
            params={
                "access_token": token,
                "caption": text,
            },
            files={"source": open(image_path, "rb")},
            timeout=30,
        )
        media_resp.raise_for_status()
        creation_id = media_resp.json().get("id")

        if creation_id:
            # Publish
            pub_resp = requests.post(
                f"{GRAPH_API}/{ig_id}/media_publish",
                params={
                    "access_token": token,
                    "creation_id": creation_id,
                },
                timeout=15,
            )
            pub_resp.raise_for_status()
            post_id = pub_resp.json().get("id", "")
            return {"success": True, "post_id": post_id, "platform": "instagram"}
    else:
        # Samo tekst nije podržan na Instagramu
        print("  ℹ Instagram zahtijeva sliku uz objavu — preskačem")
        return None


def post_all(text: str, image_path: str | None = None) -> list[dict]:
    """Objavi na Facebook (+ Instagram) odjednom."""
    results = []
    results.append(post_to_facebook(text, image_path))
    ig = post_to_instagram(text, image_path)
    if ig:
        results.append(ig)
    return results


if __name__ == "__main__":
    import sys
    text = sys.argv[1] if len(sys.argv) > 1 else "Test objava"
    img = sys.argv[2] if len(sys.argv) > 2 else None
    results = post_all(text, img)
    print(json.dumps(results, indent=2))
