"""
In-memory session manager for multi-turn chat conversations.

Stores chat history per session_id in a simple dictionary.
Sessions are ephemeral — they are lost on server restart.
"""

import uuid
import time
from typing import Optional


class SessionManager:
    """Thread-safe in-memory session store for chat conversations."""

    def __init__(self, max_history_length: int = 50):
        self._sessions: dict = {}
        self.max_history_length = max_history_length

    def create_session(self, project_id: str) -> str:
        """Create a new chat session and return its ID."""
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {
            "project_id": project_id,
            "history": [],
            "created_at": time.time(),
            "last_active": time.time(),
        }
        return session_id

    def get_or_create_session(self, session_id: Optional[str], project_id: str) -> str:
        """Return existing session_id if valid, otherwise create a new one."""
        if session_id and session_id in self._sessions:
            self._sessions[session_id]["last_active"] = time.time()
            return session_id
        return self.create_session(project_id)

    def get_history(self, session_id: str) -> list:
        """Return the chat history for a session."""
        session = self._sessions.get(session_id)
        if not session:
            return []
        return session["history"]

    def get_project_id(self, session_id: str) -> Optional[str]:
        """Return the project_id associated with a session."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        return session["project_id"]

    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to the session history."""
        session = self._sessions.get(session_id)
        if not session:
            return

        session["history"].append({
            "role": role,
            "content": content,
        })
        session["last_active"] = time.time()

        # Trim history if it exceeds the maximum length
        if len(session["history"]) > self.max_history_length:
            session["history"] = session["history"][-self.max_history_length:]

    def clear_session(self, session_id: str) -> bool:
        """Delete a session and its history. Returns True if session existed."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def get_active_sessions_count(self) -> int:
        """Return the number of active sessions."""
        return len(self._sessions)
