FUNCTIONS = {
    "goto": {
        "description": "Go to a location or receptacle",
        "parameters": {
            "recep": "The type of the location or receptacle",
            "recep_idx": "The index of the location or receptacle",
        },
        "action": "go to {recep} {recep_idx}",
        "startswith": "go",
        "param_pos": [2, 3],
    },
    "take": {
        "description": "Take an object from a location or receptacle",
        "parameters": {
            "object": "The type of the object",
            "object_idx": "The index of the object",
            "recep": "The type of the location or receptacle",
            "recep_idx": "The index of the location or receptacle",
        },
        "action": "take {object} {object_idx} from {recep} {recep_idx}",
        "param_pos": [1, 2, 4, 5],
    },
    "put": {
        "description": "Put an object in or on a location or receptacle",
        "parameters": {
            "object": "The type of the object",
            "object_idx": "The index of the object",
            "recep": "The type of the location or receptacle",
            "recep_idx": "The index of the location or receptacle",
        },
        "action": "put {object} {object_idx} in/on {recep} {recep_idx}",
        "param_pos": [1, 2, 4, 5],
    },
    "open": {
        "description": "Open a receptacle",
        "parameters": {
            "recep": "The receptacle to open",
            "recep": "The type of the receptacle",
            "recep_idx": "The index of the receptacle",
        },
        "action": "open {recep} {recep_idx}",
        "param_pos": [1, 2],
    },
    "close": {
        "description": "Close a receptacle",
        "parameters": {
            "recep": "The receptacle to open",
            "recep": "The type of the receptacle",
            "recep_idx": "The index of the receptacle",
        },
        "action": "close {recep} {recep_idx}",
        "param_pos": [1, 2],
    },
    "toggle": {
        "description": "Turn an object or receptacle on or off",
        "parameters": {
            "type": "The type of the object or receptacle",
            "idx": "The index of the object or receptacle",
        },
        "action": "toggle {type} {idx}",
        "param_pos": [1, 2],
    },
    "clean": {
        "description": "Clean an object with a receptacle",
        "parameters": {
            "object": "The type of the object",
            "object_idx": "The index of the object to clean",
            "recep": "The type of the receptacle",
            "recep_idx": "The index of the receptacle",
        },
        "action": "clean {object} {object_idx} with {recep} {recep_idx}",
        "param_pos": [1, 2, 4, 5],
    },
    "heat": {
        "description": "Heat an object with a receptacle",
        "parameters": {
            "object": "The type of the object",
            "object_idx": "The index of the object to clean",
            "recep": "The type of the receptacle",
            "recep_idx": "The index of the receptacle",
        },
        "action": "heat {object} {object_idx} with {recep} {recep_idx}",
        "param_pos": [1, 2, 4, 5],
    },
    "cool": {
        "description": "Cool an object with a receptacle",
        "parameters": {
            "object": "The type of the object",
            "object_idx": "The index of the object to clean",
            "recep": "The type of the receptacle",
            "recep_idx": "The index of the receptacle",
        },
        "action": "cool {object} {object_idx} with {recep} {recep_idx}",
        "param_pos": [1, 2, 4, 5],
    },
}

REACT_FUNCTIONS = {
    "think": {
        "description": "Express your thoughts about what to do next",
        "parameters": {
            "thought": "A sentence or two of your thoughts",
        },
        "action": "think: {thought}",
        "startswith": "think:",
        "param_pos": ["rest"],
    },
}

ALL_FUNCTIONS = {**FUNCTIONS, **REACT_FUNCTIONS}

def action_str_to_dict(action_str):
    action = action_str.strip().split(' ')
    for func, details in ALL_FUNCTIONS.items():
        startswith = details.get('startswith', func)
        if action[0] != startswith:
            continue
        args = {}
        for idx, param in enumerate(details['parameters'].keys()):
            pos = details['param_pos'][idx]
            if pos == 'rest':
                args[param] = ' '.join(action[1:])
            else:
                args[param] = action[pos]
        return (func, args)
    raise ValueError(f"No match for '{action}'") 
        

def gpt_functions(include_react=False):
    functions = FUNCTIONS
    if include_react:
        functions = ALL_FUNCTIONS
    functions = functions.copy()
    return [gpt_function(name, details) for name, details in functions.items()]

def gpt_function(name, details):
    out = {}
    out["name"] = name
    out["description"] = details["description"]
    out["parameters"] = {"type": "object", "properties": {}, "required": []}
    for param, description in details["parameters"].items():
        param_type = "string"
        if param.endswith('idx'):
            param_type = "integer"
        out["parameters"]["properties"][param] = {
            "type": param_type,
            "description": description,
        }
        out["parameters"]["required"].append(param)
    return out
