"""
VSS Digital — Facebook + Instagram Publisher

Objavljuje sadržaj na Facebook Page i Instagram Business Account.
Koristi Meta Graph API v22.0.
"""

import os
import json
import requests
from pathlib import Path


GRAPH_API = "https://graph.facebook.com/v22.0"


def get_page_token() -> str:
    return os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", "")


def get_page_id(token: str) -> str:
    """Dohvati Facebook Page ID.
    
    Radi s Page Access Tokenom (vraća page info direktno preko /me)
    i s User Access Tokenom (traži pages preko /me/accounts).
    """
    # Prvo probaj /me — radi za Page Access Token
    resp = requests.get(
        f"{GRAPH_API}/me",
        params={"access_token": token},
        timeout=10,
    )
    if resp.status_code != 200:
        raise ValueError(f"Token nije valjan: {resp.text}")

    data = resp.json()
    if "id" in data:
        return data["id"]

    # Fallback /me/accounts — radi za User Access Token
    resp = requests.get(
        f"{GRAPH_API}/me/accounts",
        params={"access_token": token},
        timeout=10,
    )
    resp.raise_for_status()
    accounts = resp.json().get("data", [])
    if accounts:
        return accounts[0]["id"]

    raise ValueError("Ne mogu pronaći Page ID. Token možda nema dozvole za upravljanje Pageom.")


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
    """Objavi na Facebook Page — tekst + opcionalna slika."""
    token = get_page_token()
    if not token:
        raise ValueError("FACEBOOK_PAGE_ACCESS_TOKEN nije postavljen")

    page_id = get_page_id(token)

    if image_path and Path(image_path).exists():
        with open(image_path, "rb") as f:
            resp = requests.post(
                f"{GRAPH_API}/{page_id}/photos",
                params={"access_token": token, "message": text},
                files={"source": f},
                timeout=30,
            )
    else:
        resp = requests.post(
            f"{GRAPH_API}/{page_id}/feed",
            params={"access_token": token, "message": text},
            timeout=15,
        )

    resp.raise_for_status()
    post_id = resp.json().get("id", "")
    return {"success": True, "post_id": post_id, "platform": "facebook"}


def post_to_instagram(text: str, image_path: str | None = None) -> dict | None:
    """Objavi na Instagram Business Account.
    
    Instagram zahtijeva sliku. Prvo stvara media container,
    zatim ga publisha.
    """
    token = get_page_token()
    if not token:
        raise ValueError("FACEBOOK_PAGE_ACCESS_TOKEN nije postavljen")

    page_id = get_page_id(token)
    ig_id = get_instagram_id(page_id, token)

    if not ig_id:
        print("  ℹ Instagram Business Account nije povezan uz Page — preskačem")
        return None

    if not image_path or not Path(image_path).exists():
        print("  ℹ Instagram zahtijeva sliku uz objavu — preskačem")
        return None

    # Korak 1: Stvori media container s uploadom slike
    with open(image_path, "rb") as f:
        media_resp = requests.post(
            f"{GRAPH_API}/{ig_id}/media",
            params={"access_token": token, "caption": text},
            files={"source": f},
            timeout=60,
        )

    if media_resp.status_code != 200:
        # Ako binary upload ne radi, probaj s image_url
        print(f"  ⚠ Binary upload nije uspio ({media_resp.status_code}), pokušavam s image_url...")
        return None

    media_data = media_resp.json()
    creation_id = media_data.get("id")
    if not creation_id:
        print(f"  ✗ Nije dobiven creation_id: {media_data}")
        return None

    # Korak 2: Publisaj container
    pub_resp = requests.post(
        f"{GRAPH_API}/{ig_id}/media_publish",
        params={
            "access_token": token,
            "creation_id": creation_id,
        },
        timeout=30,
    )
    pub_resp.raise_for_status()
    post_id = pub_resp.json().get("id", "")

    return {"success": True, "post_id": post_id, "platform": "instagram"}


def post_all(text: str, image_path: str | None = None) -> list[dict]:
    """Objavi na Facebook (+ Instagram) odjednom.
    Vraća listu rezultata. Ako Instagram padne, Facebook i dalje radi.
    """
    results = []

    try:
        results.append(post_to_facebook(text, image_path))
    except Exception as e:
        print(f"  ✗ Facebook error: {e}")
        results.append({"success": False, "platform": "facebook", "error": str(e)})

    try:
        ig = post_to_instagram(text, image_path)
        if ig:
            results.append(ig)
    except Exception as e:
        print(f"  ✗ Instagram error: {e}")
        results.append({"success": False, "platform": "instagram", "error": str(e)})

    return results


if __name__ == "__main__":
    import sys
    text = sys.argv[1] if len(sys.argv) > 1 else "Test objava"
    img = sys.argv[2] if len(sys.argv) > 2 else None
    results = post_all(text, img)
    print(json.dumps(results, indent=2, ensure_ascii=False))
