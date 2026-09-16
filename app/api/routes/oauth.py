"""
LinkedIn OAuth 2.0 (Authorization Code flow) endpoints — used ONCE to
obtain a real access token and your LinkedIn member ID (URN), which then
get pasted into .env. This capstone deliberately does NOT implement
automatic token refresh (LinkedIn tokens last ~60 days) — re-running this
flow by hand when it expires is the simple, honest approach for now.

Flow:
  1. Visit GET /oauth/linkedin/login in your browser
  2. Log in to LinkedIn and approve the consent screen
  3. LinkedIn redirects to GET /oauth/linkedin/callback with a code
  4. This exchanges the code for an access token, fetches your member URN,
     and displays both so you can copy them into .env
"""
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse

from app.core.config import settings

router = APIRouter(prefix="/oauth/linkedin", tags=["oauth"])

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"

# Must exactly match the redirect URL registered in your LinkedIn app.
REDIRECT_URI = "http://localhost:8000/oauth/linkedin/callback"
SCOPES = "openid profile email w_member_social"

# In-memory state store — fine for a single-developer local OAuth flow.
# A real multi-user product would store this server-side per session instead.
_pending_states: set[str] = set()


@router.get("/login")
def linkedin_login():
    state = secrets.token_urlsafe(16)
    _pending_states.add(state)

    params = {
        "response_type": "code",
        "client_id": settings.linkedin_client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
    }
    return RedirectResponse(f"{LINKEDIN_AUTH_URL}?{urlencode(params)}")


@router.get("/callback")
def linkedin_callback(request: Request):
    error = request.query_params.get("error")
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"LinkedIn returned an error: {error} - "
            f"{request.query_params.get('error_description')}",
        )

    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code or state not in _pending_states:
        raise HTTPException(status_code=400, detail="Missing or invalid code/state in callback")
    _pending_states.discard(state)

    # Exchange the authorization code for an access token
    token_resp = httpx.post(
        LINKEDIN_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": settings.linkedin_client_id,
            "client_secret": settings.linkedin_client_secret,
        },
    )
    token_data = token_resp.json()
    if "access_token" not in token_data:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {token_data}")

    access_token = token_data["access_token"]
    expires_in = token_data.get("expires_in")

    # Fetch the member's URN (needed as the "author" field when posting)
    userinfo_resp = httpx.get(
        LINKEDIN_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    userinfo = userinfo_resp.json()
    member_id = userinfo.get("sub")
    person_urn = f"urn:li:person:{member_id}" if member_id else "UNKNOWN"

    days = round(expires_in / 86400) if expires_in else "?"
    html = f"""
    <h2>LinkedIn OAuth succeeded </h2>
    <p>Copy these two lines into your .env file:</p>
    <pre style="background:#f0f0f0; padding:1em;">
LINKEDIN_ACCESS_TOKEN={access_token}
LINKEDIN_PERSON_URN={person_urn}
    </pre>
    <p>Token expires in {expires_in} seconds (~{days} days). You'll need to
    repeat this flow after that.</p>
    """
    return HTMLResponse(html)