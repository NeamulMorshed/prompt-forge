import uuid
import logging

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.security import create_access_token
from app.db.base import get_db
from app.db.models import OIDCConfig, User, Workspace

logger = logging.getLogger("app.auth.oidc")

router = APIRouter(prefix="/auth/oidc", tags=["auth"])


class OIDCConfigCreate(BaseModel):
    discovery_url: str
    client_id: str
    client_secret: str


@router.post("/config", status_code=201)
def save_oidc_config(
    body: OIDCConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not current_user.workspace_id:
        raise HTTPException(status_code=400, detail="No workspace")
    existing = db.scalar(
        select(OIDCConfig).where(OIDCConfig.workspace_id == current_user.workspace_id)
    )
    if existing:
        existing.discovery_url = body.discovery_url
        existing.client_id = body.client_id
        existing.client_secret = body.client_secret
        db.commit()
        return {"ok": True, "updated": True}
    config = OIDCConfig(
        id=uuid.uuid4(),
        workspace_id=current_user.workspace_id,
        discovery_url=body.discovery_url,
        client_id=body.client_id,
        client_secret=body.client_secret,
    )
    db.add(config)
    db.commit()
    return {"ok": True, "updated": False}


@router.get("/login")
def oidc_login(
    workspace_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    try:
        ws_uuid = uuid.UUID(workspace_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workspace_id")
    config = db.scalar(select(OIDCConfig).where(OIDCConfig.workspace_id == ws_uuid))
    if config is None:
        raise HTTPException(status_code=404, detail="OIDC not configured for this workspace")
    try:
        oauth = OAuth()
        oauth.register(
            name="oidc",
            server_metadata_url=config.discovery_url,
            client_id=config.client_id,
            client_secret=config.client_secret,
            client_kwargs={"scope": "openid email profile"},
        )
        redirect_uri = str(request.url_for("oidc_callback")) + f"?workspace_id={workspace_id}"
        return oauth.oidc.authorize_redirect(request, redirect_uri)
    except Exception as exc:
        logger.error("OIDC login error: %s", exc)
        raise HTTPException(status_code=500, detail="OIDC provider error")


@router.get("/callback", name="oidc_callback")
async def oidc_callback(
    workspace_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    try:
        ws_uuid = uuid.UUID(workspace_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workspace_id")
    config = db.scalar(select(OIDCConfig).where(OIDCConfig.workspace_id == ws_uuid))
    if config is None:
        raise HTTPException(status_code=404, detail="OIDC not configured")
    try:
        oauth = OAuth()
        oauth.register(
            name="oidc",
            server_metadata_url=config.discovery_url,
            client_id=config.client_id,
            client_secret=config.client_secret,
            client_kwargs={"scope": "openid email profile"},
        )
        token = await oauth.oidc.authorize_access_token(request)
        userinfo = token.get("userinfo", {})
        email = userinfo.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="OIDC provider did not return email")
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                id=uuid.uuid4(),
                email=email,
                password_hash="oidc",
                workspace_id=ws_uuid,
            )
            db.add(user)
            db.commit()
        elif user.workspace_id != ws_uuid:
            user.workspace_id = ws_uuid
            db.commit()
        jwt_token = create_access_token(subject=str(user.id))
        return {"access_token": jwt_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("OIDC callback error: %s", exc)
        raise HTTPException(status_code=500, detail="OIDC callback failed")
