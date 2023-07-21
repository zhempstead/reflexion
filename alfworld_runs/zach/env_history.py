import json
from typing import Any, List, Dict, Tuple, Optional

class EnvironmentHistory:
    def __init__(self, start_info: str, history: List[Tuple[str, Dict[str, Any], str]]) -> None:
        self._start_info = start_info
        self._history = history
        self._is_exhausted: bool = False
        self._last_action = None
        self._examples = []

    def add_action(self, action_name: str, args: Dict[str, Any], obs) -> None:
        history_tup = (action_name, args, obs)
        action_tup = (action_name, args)
        self._history += [history_tup]
        if self._last_action == action_tup:
            self._is_exhausted = True
        self._last_action = action_tup

    def check_is_exhausted(self) -> bool:
        return self._is_exhausted

    def reset(self) -> None:
        self._history = []
        self._is_exhausted = False
        self._last_action = None

    def get_task_query(self, role="You are an assistant that interacts with a household to solve tasks."):
        chat = [
            {"role": "system", "content": role},
        ]
        if self._examples:
            for e in self._examples:
                chat += e._get_task_prompt()
        chat += self._get_task_prompt()
        return chat

    def _get_task_prompt(self):
        chat = [
            {"role": "user", "content": self._start_info}
        ]
        chat += self.get_history_chat()
        return chat

    def get_history_chat(self):
        history = []
        for action, args, obs in self._history:
            history.append({
                "role": "assistant",
                "function_call": {
                    "name": action,
                    "arguments": json.dumps(args),
                },
                "content": None,
            }),
            history.append({
                "role": "function",
                "name": action,
                "content": obs,
            })
        return history
