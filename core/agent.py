from core.client import OUTPUTS_DIR


def log_message(role: str, user_msg: str, reply: str, tool_events: list[dict]) -> None:
    OUTPUTS_DIR.mkdir(exist_ok=True)
    event_log = "; ".join(f"{e['type']}({e['detail']})" for e in tool_events) or "none"
    with open(OUTPUTS_DIR / "chat_log.txt", "a", encoding="utf-8") as f:
        f.write(
            f"\n{'-' * 60}\n[{role}]: {user_msg}\n"
            f"Tools: {event_log}\n[PM Assistant]: {reply}\n"
        )
