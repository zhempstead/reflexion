import json

PROMPT_FILE = 'prompts/alfworld_3prompts.json'
OUT_FILE = 'zach/task_split_prompts.json'

if __name__ == '__main__':
    with open(PROMPT_FILE) as pf:
        prompts = json.load(pf)

    try:
        with open(OUT_FILE) as of:
            out = json.load(of)
    except:
        out = {}

    for title, prompt in prompts.items():
        if title in out:
            print(f"Already did '{title}'...")
            continue
        if not title.startswith('react'):
            continue
        print(f'{title}:')
        task_description = prompt.split('\n>')[0]
        first_thought = prompt.split('\n> think: ')[1].split('\n')[0]
        print(task_description)
        print()
        print(first_thought)

        subtasks = []
        while True:
            subtask = input(f'{len(subtasks) + 1}. ')
            if subtask:
                subtasks.append(subtask)
            else:
                break
        out[title] = {'description': task_description, 'original_thought': first_thought, 'subtasks': subtasks}
        with open(OUT_FILE, 'w') as of:
            json.dump(out, of)
