"""
patches.py — loaded by __init__.py before agent.py.

Patches VertexAiSessionService to accept full Agentspace resource paths
as session_id. Agentspace passes:
  projects/446449044316/locations/us/collections/.../sessions/15093948411917385183

ADK validates against ^[A-Za-z0-9_-]+$ which rejects this.
We strip the prefix to get the bare numeric ID before validation.

This is a workaround for a known ADK/Agentspace integration bug where
Agentspace does not strip the resource path before passing session_id to
the agent. Filed: https://github.com/google/adk-python/issues
"""


def _bare(session_id: str) -> str:
    """Return bare session ID, stripping any resource path prefix."""
    if session_id and "/" in session_id:
        return session_id.split("/")[-1]
    return session_id or ""


def apply():
    """Patch ADK session service. Safe to call multiple times."""
    try:
        import re
        import google.adk.sessions.vertex_ai_session_service as _m

        # 1. Replace the module-level validator so any call site is covered.
        _pat = re.compile(r"^[A-Za-z0-9_-]+$")

        def _validate(session_id: str) -> None:
            bare = _bare(session_id)
            if not isinstance(bare, str) or not _pat.fullmatch(bare):
                raise ValueError(
                    f"Invalid session_id {bare!r}: must match {_pat.pattern}."
                )

        _m._validate_session_id = _validate

        # 2. Patch get_session — strips before the validate call inside it.
        _orig_get = _m.VertexAiSessionService.get_session

        async def _get(self, *, app_name, user_id, session_id, **kw):
            return await _orig_get(
                self,
                app_name=app_name,
                user_id=user_id,
                session_id=_bare(session_id),
                **kw,
            )

        _m.VertexAiSessionService.get_session = _get

        # 3. Patch create_session.
        _orig_create = _m.VertexAiSessionService.create_session

        async def _create(self, *, app_name, user_id, session_id="", **kw):
            return await _orig_create(
                self,
                app_name=app_name,
                user_id=user_id,
                session_id=_bare(session_id),
                **kw,
            )

        _m.VertexAiSessionService.create_session = _create

        # 4. Patch delete_session.
        _orig_delete = _m.VertexAiSessionService.delete_session

        async def _delete(self, *, app_name, user_id, session_id, **kw):
            return await _orig_delete(
                self,
                app_name=app_name,
                user_id=user_id,
                session_id=_bare(session_id),
                **kw,
            )

        _m.VertexAiSessionService.delete_session = _delete

        return True

    except Exception:
        # Never crash the agent because of a patch failure.
        return False
