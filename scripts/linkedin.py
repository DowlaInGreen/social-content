"""
VSS Digital — LinkedIn Publisher

Objavljuje sadrzaj na LinkedIn Company Page ili osobni profil.
"""

import os
import json
import requests
from pathlib import Path


LINKEDIN_API = "https://api.linkedin.com/v2"


def get_access_token() -> str:
    return os.environ.get("LINKEDIN_ACCESS_TOKEN", "")


def get_user_id(token: str) -> str:
    """Dohvati LinkedIn user ID (sub) za daljnje API pozive."""
    resp = requests.get(
        f"{LINKEDIN_API}/userinfo",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("sub", "")


def post_to_linkedin(text: str, image_path: str | None = None) -> dict:
    """
    Objavi tekst na LinkedIn.
    Vraca {'success': True, 'post_id': '...'} ili baca gresku.
    """
    token = get_access_token()
    if not token:
        raise ValueError("LINKEDIN_ACCESS_TOKEN nije postavljen")

    user_id = get_user_id(token)
    author_urn = f"urn:li:person:{user_id}"

    # Tekstualna objava
    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }

    # Ako ima slika, dodaj
    if image_path and Path(image_path).exists():
        # Prvo uploadaj sliku
        register_upload = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": author_urn,
                "serviceRelationships": [{
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent",
                }],
            }
        }
        upload_resp = requests.post(
            f"{LINKEDIN_API}/assets?action=registerUpload",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=register_upload,
            timeout=10,
        )
        upload_resp.raise_for_status()
        upload_data = upload_resp.json()

        upload_url = upload_data["value"]["uploadMechanism"][
            "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
        ]["uploadUrl"]
        asset_urn = upload_data["value"]["asset"]

        # Uploadaj file
        with open(image_path, "rb") as f:
            requests.put(upload_url, data=f, timeout=30)

        # Dodaj u payload
        payload["specificContent"]["com.linkedin.ugc.ShareContent"] = {
            "shareCommentary": {"text": text},
            "shareMediaCategory": "IMAGE",
            "media": [{
                "status": "READY",
                "description": {"text": ""},
                "media": asset_urn,
                "title": {"text": ""},
            }],
        }

    resp = requests.post(
        f"{LINKEDIN_API}/ugcPosts",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "LinkedIn-Version": "202304",
        },
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    post_id = resp.json().get("id", "")
    return {"success": True, "post_id": post_id}


if __name__ == "__main__":
    import sys
    text = sys.argv[1] if len(sys.argv) > 1 else "Test objava"
    img = sys.argv[2] if len(sys.argv) > 2 else None
    result = post_to_linkedin(text, img)
    print(json.dumps(result, indent=2))
