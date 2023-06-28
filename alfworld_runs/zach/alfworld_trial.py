"""Adapted from https://github.com/ysymyth/ReAct/blob/master/alfworld.ipynb"""

import os
import sys
import json
import yaml
import openai
import importlib
import alfworld
import alfworld.agents.environment
from env_history import EnvironmentHistory

from typing import List, Dict, Any, Tuple

openai.api_key = os.environ["OPENAI_API_KEY"]
FOLDER = './prompts'
PROMPT_FILE = 'alfworld_3prompts.json'

TASK_SPLIT_PROMPTS_FILE = 'task_split_prompts.json'
SUBTASK_PROMPTS_DIR = 'subtask_prompts'

SUBTASK_QUESTION = "What subtasks does this entail?"

example_histories = {}
with open(TASK_SPLIT_PROMPTS_FILE, 'r') as f:
    for task, entry in json.load(f).items():
        history = []
        try:
            with open(os.path.join(SUBTASK_PROMPTS_DIR, task)) as sf:
                subtasks_txt = sf.read().split('\n\n')
        except FileNotFoundError:
                subtasks_txt = []
        for idx in range(len(subtasks_txt)):
            subtask = entry['subtasks'][idx]
            subtask_history = []
            for item in subtasks_txt[idx].split('\n'):
                if item.startswith('> '):
                    subtask_history.append({'label': 'action', 'value': item[2:]})
                else:
                    subtask_history.append({'label': 'observation', 'value': item})
            history.append((subtask, subtask_history))


        example_histories[task] = EnvironmentHistory(start_info=entry['description'], history=history, curr_subtask=0, memory=[], examples=[])

def llm(chat, stop=None):
    try:
        cur_try = 0
        while cur_try < 6:
            response = openai.ChatCompletion.create(
              model="gpt-3.5-turbo",
              messages=chat,
              temperature=cur_try * 0.2,
              max_tokens=100,
              stop=stop
            )
            text = response["choices"][0]["message"]["content"]
            # dumb way to do this
            if len(text.strip()):
                return response["choices"][0]["message"]["content"]
            cur_try += 1
        return ""
    except Exception as e:
        print(chat)
        print(e)
        import sys
        sys.exit(1)

def process_ob(ob):
    if ob.startswith('You arrive at loc '):
        ob = ob[ob.find('. ')+2:]    
    return ob


def alfworld_run(env, examples, memory: List[str], to_print=True, ob='', use_subtasks=True) -> Tuple[EnvironmentHistory, bool]:
    if len(memory) > 3:
        env_history = EnvironmentHistory(ob, [], 0, memory[-3:], examples)
    else:
        env_history = EnvironmentHistory(ob, [], 0, memory, examples)
    env_history.reset()
    # init_prompt = prompt + ob + '\n>'
    # prompt = ''
    if to_print:
        print(ob)
        sys.stdout.flush()
    if use_subtasks:
        subtasks = llm(env_history.get_split_query()).strip()
        print(subtasks)
        env_history.set_subtasks(subtasks)
    else:
        env_history.set_subtasks('- N/A')
    cur_step = 0
    if to_print and use_subtasks:
        print(f'*** SUBTASK: {env_history.get_subtask()} ***')
    while cur_step < 50:
        if use_subtasks:
            query = env_history.get_subtask_query()
        else:
            query = env_history.get_task_query()
        action = llm(query, stop=['\n']).strip()
            
        env_history.add("action", action)
        observation, reward, done, info = env.step([action])
        observation, reward, done = process_ob(observation[0]), info['won'][0], done[0]
        if action.startswith('think:') or action.startswith('done'):
            observation = 'OK.'
        env_history.add("observation", observation)
        if to_print:
            print(f'> {action}\n{observation}')
            sys.stdout.flush()
        # prompt += f' {action}\n{observation}\n>'
        if done:
            return env_history, True
        elif env_history.check_is_exhausted():
            return env_history, False

        if use_subtasks and env_history.get_subtask_observations() and not env_history.is_last_subtask():
            is_done = llm(env_history.get_done_query(), stop=['\n']).strip()
            if is_done.lower().startswith('yes'):
                #print(env_history.get_done_query() + ' ' + is_done)
                #import pdb; pdb.set_trace()
                env_history.advance_subtask()
                if to_print:
                    print(f'*** SUBTASK: {env_history.get_subtask()} ***')
        cur_step += 1
    return env_history, False

PREFIXES = {
    'pick_and_place': 'put',
    'pick_clean_then_place': 'clean',
    'pick_heat_then_place': 'heat',
    'pick_cool_then_place': 'cool',
    'look_at_obj': 'examine',
    'pick_two_obj': 'puttwo'
}

def run_trial(
        trial_log_path: str,
        world_log_path: str,
        trial_idx: int,
        env_configs: List[Dict[str, Any]],
        use_memory: bool,
        use_subtasks: bool,
    ) -> List[Dict[str, Any]]:
    importlib.reload(alfworld)
    importlib.reload(alfworld.agents.environment)

    with open('../base_config.yaml') as reader:
        config = yaml.safe_load(reader)
    split = "eval_out_of_distribution"

    env = getattr(alfworld.agents.environment, config["env"]["type"])(config, train_eval=split)
    env = env.init_env(batch_size=1)

    num_successes: int = 0
    num_additional_successes: int = 0
    num_envs: int = len(env_configs)

    for z, env_config in enumerate(env_configs):
        ob, info = env.reset()
        ob = '\n'.join(ob[0].split('\n\n')[1:])
        name = '/'.join(info['extra.gamefile'][0].split('/')[-3:-1])

        print(f"using {name}")

        if env_config["is_success"]:
            num_successes += 1

            # log to world log
            with open(world_log_path, 'a') as wf:
                wf.write(f'Environment #{z} Trial #{trial_idx}: SUCCESS\n')
            with open(trial_log_path, 'a') as wf:
                wf.write(f'\n#####\n\nEnvironment #{z}: Success\n\n#####\n')
            continue

        for i, (k, v) in enumerate(PREFIXES.items()):
            if name.startswith(k):
                examples = [example_histories[f'react_{v}_1'], example_histories[f'react_{v}_0']]
                final_env_history, is_success = alfworld_run(env, examples, env_config["memory"] if use_memory else [], to_print=True, ob=ob, use_subtasks=use_subtasks)

                # update env config
                if is_success:
                    status_str: str = f'Environment #{z} Trial #{trial_idx}: SUCCESS'
                    env_configs[z]['is_success'] = True
                    num_successes += 1
                    num_additional_successes += 1
                else:
                    status_str: str = f'Environment #{z} Trial #{trial_idx}: FAIL'

                # log to world log
                with open(world_log_path, 'a') as f:
                    f.write(status_str + '\n')

                # log env results to trial log
                with open(trial_log_path, 'a') as wf:
                    wf.write(f'\n#####\n\nEnvironment #{z}:\n{str(final_env_history)}\n\nSTATUS: {"OK" if is_success else "FAIL"}\n\n#####\n')

    # close environment object
    env.close()

    # log trial results to trial and world logs
    log_str: str = f"""
-----
SUCCESS: {num_successes}
ADDITIONAL SUCCESS: {num_additional_successes}
FAIL: {num_envs - num_successes}
TOTAL: {num_envs}
ACCURACY: {round(num_successes / num_envs, 2)}
-----"""
    with open(trial_log_path, 'a') as wf:
        wf.write(log_str)
    with open(world_log_path, 'a') as wf:
        wf.write(log_str + '\n')

    return env_configs
