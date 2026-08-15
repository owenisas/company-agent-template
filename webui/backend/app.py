"""FastAPI entry: auth, scoped profiles, chat jobs, usage, static UI."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import jobs, profiles, scope, users
from .auth import AuthError, issue_session, read_session
from .config import (
    COOKIE_MAX_AGE,
    COOKIE_NAME,
    FRONTEND_DIR,
    USERS_PATH,
    secure_cookie,
    webui_port,
)
from .usage import usage_for_profiles


class LoginBody(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class ChatBody(BaseModel):
    profile: str = Field(min_length=1)
    message: str = Field(min_length=1)


def create_app() -> FastAPI:
    app = FastAPI(title="Company agent", docs_url=None, redoc_url=None)

    def _set_session(response: Response, username: str) -> None:
        response.set_cookie(
            key=COOKIE_NAME,
            value=issue_session(username),
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=secure_cookie(),
            path="/",
        )

    def current_user(request: Request) -> dict:
        try:
            username = read_session(request.cookies.get(COOKIE_NAME))
        except AuthError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        record = users.find_user(username)
        if not record:
            raise HTTPException(status_code=401, detail="unknown user")
        return record

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "users_configured": USERS_PATH.is_file(),
        }

    @app.post("/api/login")
    async def login(request: Request) -> Response:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            payload = LoginBody.model_validate(await request.json())
            wants_json = True
        else:
            form = await request.form()
            payload = LoginBody(
                username=str(form.get("username") or ""),
                password=str(form.get("password") or ""),
            )
            wants_json = False

        if not USERS_PATH.is_file():
            raise HTTPException(status_code=503, detail="users.json is not configured")
        record = users.find_user(payload.username)
        if not record or not users.verify_password(payload.password, record):
            raise HTTPException(status_code=401, detail="invalid credentials")

        body = {
            **users.public_user(record),
            "admin": scope.is_admin(record.get("username", ""), record.get("role", "")),
        }
        if wants_json:
            response: Response = JSONResponse(body)
        else:
            response = RedirectResponse(url="/", status_code=303)
        _set_session(response, record["username"])
        return response

    @app.post("/api/logout")
    def logout() -> Response:
        response = JSONResponse({"ok": True})
        response.delete_cookie(COOKIE_NAME, path="/")
        return response

    @app.get("/api/whoami")
    def whoami(user: dict = Depends(current_user)) -> dict[str, Any]:
        return {
            **users.public_user(user),
            "admin": scope.is_admin(user.get("username", ""), user.get("role", "")),
        }

    @app.get("/api/profiles")
    def list_profiles(user: dict = Depends(current_user)) -> dict[str, Any]:
        host = profiles.list_host_profiles()
        allowed = scope.accessible_profiles(user, host)
        return {"profiles": allowed}

    @app.post("/api/chat")
    def chat(body: ChatBody, user: dict = Depends(current_user)) -> dict[str, str]:
        if not scope.can_access(user, body.profile):
            raise HTTPException(status_code=403, detail="profile not in scope")
        if not profiles.profile_exists(body.profile):
            raise HTTPException(status_code=404, detail="unknown profile")
        job = jobs.start_job(body.profile, body.message)
        return {"job_id": job.job_id}

    @app.get("/api/jobs/{job_id}")
    def job_status(job_id: str, user: dict = Depends(current_user)) -> dict[str, Any]:
        job = jobs.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="unknown job")
        if job.profile and not scope.can_access(user, job.profile):
            raise HTTPException(status_code=403, detail="profile not in scope")
        return job.public()

    @app.get("/api/usage")
    def usage(user: dict = Depends(current_user)) -> dict[str, Any]:
        host = profiles.list_host_profiles()
        allowed = scope.accessible_profiles(user, host)
        return {"profiles": usage_for_profiles(allowed)}

    index = FRONTEND_DIR / "index.html"

    @app.get("/")
    def root() -> FileResponse:
        return FileResponse(index)

    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=webui_port(),
        factory=False,
    )


if __name__ == "__main__":
    main()
