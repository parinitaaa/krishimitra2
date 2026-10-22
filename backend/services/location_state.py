# services/location_state.py
# DB-backed shim for pending location state using conversation_state table.

from farmer_store import get_state, set_state, clear_state, normalize_phone


class _PendingLocationProxy:
    """
    Dict-like proxy so legacy `phone in _pending_location` and
    `_pending_location.pop(phone, None)` work seamlessly against the DB.
    """

    def __contains__(self, phone: str) -> bool:
        pid = normalize_phone(phone)
        st = get_state(pid)
        return bool(st and st.get("flow") == "mandi" and st.get("step") == "ask_location")

    def __setitem__(self, phone: str, value: dict) -> None:
        pid = normalize_phone(phone)
        set_state(pid, flow="mandi", step="ask_location", data=value if isinstance(value, dict) else {})

    def __getitem__(self, phone: str) -> dict:
        pid = normalize_phone(phone)
        st = get_state(pid)
        if st and st.get("flow") == "mandi" and st.get("step") == "ask_location":
            return st.get("data") or {}
        raise KeyError(phone)

    def get(self, phone: str, default=None):
        pid = normalize_phone(phone)
        st = get_state(pid)
        if st and st.get("flow") == "mandi" and st.get("step") == "ask_location":
            return st.get("data") or {}
        return default

    def pop(self, phone: str, default=None):
        pid = normalize_phone(phone)
        st = get_state(pid)
        if st and st.get("flow") == "mandi" and st.get("step") == "ask_location":
            data = st.get("data") or {}
            clear_state(pid)
            return data
        return default


_pending_location = _PendingLocationProxy()