"""
patches.py — applied by __init__.py before agent.py loads.

Strips Agentspace full resource path prefixes from session_id.
Agentspace passes: projects/.../sessions/15093948411917385183
ADK requires:      15093948411917385183

Safe to call multiple times. Never raises — any failure is silently ignored
so the agent continues to work in environments where the patch is unnecessary.
"""


def _bare(session_id: str) -> str:
    """Strip resource path prefix, return bare alphanumeric session ID."""
    if session_id and "/" in session_id:
        return session_id.split("/")[-1]
    return session_id or ""


def apply():
    try:
        import re
        import google.adk.sessions.vertex_ai_session_service as _m

        # ── 1. Replace module-level validator ─────────────────────────────
        _pat = re.compile(r"^[A-Za-z0-9_-]+$")

        def _validate(session_id: str) -> None:
            bare = _bare(session_id)
            if not isinstance(bare, str) or not _pat.fullmatch(bare):
                raise ValueError(
                    f"Invalid session_id {bare!r}: must match {_pat.pattern}."
                )

        _m._validate_session_id = _validate

        # ── 2. Patch get_session ──────────────────────────────────────────
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

        # ── 3. Patch create_session ───────────────────────────────────────
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

        # ── 4. Patch delete_session ───────────────────────────────────────
        try:
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
        except AttributeError:
            pass  # delete_session may not exist in all ADK versions

        # ── 5. Patch AdkApp.streaming_agent_run_with_events ───────────────
        # This is the Agent Engine entry point — session_id arrives inside
        # request_json as a raw JSON string, not as a kwarg.
        try:
            import json as _json
            from vertexai.agent_engines.templates import adk as _tpl

            _orig_stream = _tpl.AdkApp.streaming_agent_run_with_events

            def _stream(self, *, request_json="", **kw):
                if request_json:
                    try:
                        req = _json.loads(request_json)
                        if req.get("session_id"):
                            req["session_id"] = _bare(req["session_id"])
                            request_json = _json.dumps(req)
                    except Exception:
                        pass
                return _orig_stream(self, request_json=request_json, **kw)

            _tpl.AdkApp.streaming_agent_run_with_events = _stream
        except Exception:
            pass  # vertexai not available in local dev — skip

        return True

    except Exception:
        return False
