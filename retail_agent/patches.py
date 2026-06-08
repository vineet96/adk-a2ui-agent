"""
patches.py — session_id sanitization for Agentspace integration.
Called explicitly from agent.py after all imports succeed.
"""


def _bare(session_id: str) -> str:
    if session_id and "/" in session_id:
        return session_id.split("/")[-1]
    return session_id or ""


def apply():
    """Patch ADK session service to accept Agentspace resource path session IDs."""
    patched = []
    try:
        import re
        import google.adk.sessions.vertex_ai_session_service as _m

        _pat = re.compile(r"^[A-Za-z0-9_-]+$")

        def _validate(session_id: str) -> None:
            bare = _bare(session_id)
            if not isinstance(bare, str) or not _pat.fullmatch(bare):
                raise ValueError(
                    f"Invalid session_id {bare!r}: must match {_pat.pattern}."
                )

        _m._validate_session_id = _validate
        patched.append("_validate_session_id")

        _orig_get = _m.VertexAiSessionService.get_session

        async def _get(self, *, app_name, user_id, session_id, **kw):
            return await _orig_get(
                self, app_name=app_name, user_id=user_id,
                session_id=_bare(session_id), **kw,
            )

        _m.VertexAiSessionService.get_session = _get
        patched.append("get_session")

        _orig_create = _m.VertexAiSessionService.create_session

        async def _create(self, *, app_name, user_id, session_id="", **kw):
            return await _orig_create(
                self, app_name=app_name, user_id=user_id,
                session_id=_bare(session_id), **kw,
            )

        _m.VertexAiSessionService.create_session = _create
        patched.append("create_session")

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"patches.apply: session patch failed: {e}")

    return patched
