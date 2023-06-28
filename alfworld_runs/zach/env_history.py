from typing import List, Dict, Tuple


class EnvironmentHistory:
    def __init__(self, start_info: str, history: List[Tuple[str, List[Dict[str, str]]]], curr_subtask: int, memory: List[str], examples: List['EnvironmentHistory']) -> None:
        self._start_info = start_info
        self._history = history
        self._memory = memory #TODO: currently unused
        self._last_action: str = ''
        self._is_exhausted: bool = False
        self._curr_subtask = curr_subtask
        self._examples = examples

    def add(self, label: str, value: str) -> None:
        assert label in ['action', 'observation', 'human_edit']
        subtask, history = self._history[self._curr_subtask]
        history += [{
            'label': label,
            'value': value,
        }]
        self._history[self._curr_subtask] = (subtask, history)
        if label == 'action':
            if value == self._last_action:
                self._is_exhausted = True
            else:
                self._last_action = value

    def set_subtasks(self, subtasks: str) -> None:
        subtasks = f'- {subtasks}'
        self._history = []
        for line in subtasks.split('\n'):
            if not line:
                continue
            if not line.startswith('- '):
                raise ValueError(f"Invalid subtask: {line}")
            self._history.append((line[2:], []))

    def advance_subtask(self) -> None:
        if self._curr_subtask < len(self._history) - 1:
            self._curr_subtask += 1

    def get_subtask(self):
        return self._history[self._curr_subtask][0]

    def is_last_subtask(self):
        return self._curr_subtask >= len(self._history) - 1

    def check_is_exhausted(self) -> bool:
        return self._is_exhausted

    def reset(self) -> None:
        self._history = []
        self._curr_subtask = 0
        self._last_action = ''

    def get_split_query(self):
        chat = [
            {"role": "system", "content": "You are an assistant that splits tasks into subtasks."},
        ]
        if self._examples:
            for e in self._examples:
                chat += e._get_split_prompt(as_example=True)
        chat += self._get_split_prompt()
        return chat

    def get_subtask_query(self):
        chat = [
            {"role": "system", "content": "You are an assistant that interacts with a household to solve a specific subtask of a larger task."},
        ]
        if self._examples:
            for e in self._examples:
                chat += e._get_subtask_prompt(subtask=self._curr_subtask)
        chat += self._get_subtask_prompt()
        return chat

    def get_done_query(self):
        chat = [{"role": "system", "content": "You are an assistant that decides whether a task has been completed."}]

        chat += self._examples[0]._get_done_prompt(self._curr_subtask, as_example=True, example_neg=True)
        chat += self._examples[0]._get_done_prompt(self._curr_subtask, as_example=True)
        chat += self._examples[1]._get_done_prompt(self._curr_subtask, as_example=True)
        chat += self._examples[1]._get_done_prompt(self._curr_subtask, as_example=True, example_neg=True)
        chat += self._get_done_prompt()
        return chat

    def _get_split_prompt(self, as_example=False):
        content = [self._start_info, "What subtasks does this task entail?"]
        chat = [
            {"role": "user", "content": '\n'.join(content)},
        ]
        if as_example:
            content = []
            for subtask, history in self._history:
                content.append(f'- {subtask}')
            chat.append({"role": "assistant", "content": '\n'.join(content)})
        return chat

    def _get_subtask_prompt(self, subtask=None):
        if not self._history:
            raise ValueError("Need history for subtask prompt")
        if subtask is None:
            subtask = self._curr_subtask
        content = [self._start_info]
        content.append('')
        if subtask > 0:
            content.append('Here is what you have done so far:')
            for prev_subtask in range(subtask):
                content += self.get_subtask_observations(prev_subtask)
        content.append(f"The current subtask: {self._history[subtask][0]}")
        chat = [
            {"role": "user", "content": '\n'.join(content)}
        ]
        chat += self.get_subtask_history_chat(subtask)
        return chat

    def _get_done_prompt(self, subtask=None, as_example=False, example_neg=False):
        if not self._history:
            raise ValueError("Need history for done prompt")
        if subtask is None:
            subtask = self._curr_subtask
        content = ["Here is what you have done so far:"]
        history = self.get_subtask_observations(subtask)
        if example_neg:
            history = history[:-1]
        content += history
        content.append(f"Have you entirely completed the task '{self._history[subtask][0]}'?")
        chat = [{"role": "user", "content": '\n'.join(content)}]
        if as_example:
            if example_neg:
                chat.append({"role": "assistant", "content": "No."})
            else:
                chat.append({"role": "assistant", "content": "Yes."})
        return chat

    def get_subtask_history_chat(self, subtask=None):
        if subtask is None:
            subtask = self._curr_subtask
        history = []
        for item in self._history[subtask][1]:
            value = item['value']
            if item['label'] == 'action':
                history.append({"role": "assistant", "content": value})
            else:
                history.append({"role": "user", "content": value})
        return history

    def get_subtask_observations(self, subtask=None):
        if subtask is None:
            subtask = self._curr_subtask
        obs = []
        for item in self._history[subtask][1]:
            if item['label'] != 'observation' or item['value'] == 'OK.':
                continue
            obs.append(item['value'])
        return obs
        

def _get_base_query(base_query: str, start_info: str, memory: List[str]) -> str:
    query = base_query

    # add memory if it exists
    if len(memory) > 0:
        query += '\n\nYour memory for the task below:'
        for i, m in enumerate(memory):
            query += f'\nTrial {i}:\n{m.strip()}'
    query += f"\nHere is the task:\n{start_info}"
    return query
