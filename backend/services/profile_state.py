# services/profile_state.py
# DB-backed shim for pending name state using conversation_state table.

from farmer_store import get_state, set_state, clear_state, normalize_phone


def mark_pending_name(phone: str) -> None:
    pid = normalize_phone(phone)
    set_state(pid, flow="onboarding", step="ask_name")


def clear_pending_name(phone: str) -> None:
    pid = normalize_phone(phone)
    st = get_state(pid)
    if st and st.get("flow") == "onboarding" and st.get("step") == "ask_name":
        clear_state(pid)


def is_pending_name(phone: str) -> bool:
    pid = normalize_phone(phone)
    st = get_state(pid)
    return bool(st and st.get("flow") == "onboarding" and st.get("step") == "ask_name")
