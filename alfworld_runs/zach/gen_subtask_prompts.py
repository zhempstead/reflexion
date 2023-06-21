import json
from pathlib import Path

PROMPT_FILE = 'prompts/alfworld_3prompts.json'
SPLIT_FILE = 'zach/task_split_prompts.json'
OUTDIR = Path('zach/subtask_prompts')

if __name__ == '__main__':
    with open(PROMPT_FILE) as pf:
        prompts = json.load(pf)

    with open(SPLIT_FILE) as sf:
        splits = json.load(sf)

    for title, prompt in prompts.items():
        if (OUTDIR / title).exists():
            print(f"Already did '{title}'...")
            continue
        if not title.startswith('react'):
            continue

        print(f'{title}:')
        print(prompt)
        input("Done? ")
