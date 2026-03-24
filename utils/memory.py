from collections import defaultdict
from typing import List, Dict

_histories: Dict[str, List[Dict]] = defaultdict(list)


def get_history(session_id: str) -> List[Dict]:
    return _histories[session_id]


def add_message(session_id: str, role: str, content: str):
    _histories[session_id].append({
        "role": role,
        "content": content
    })
    # Keep last 20 messages
    if len(_histories[session_id]) > 20:
        _histories[session_id] = (
            _histories[session_id][-20:]
        )


def clear_history(session_id: str):
    _histories[session_id] = []
