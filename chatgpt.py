import openai
import time, sys
from datetime import datetime

import vrcutils as vrc
import options as opts
import functions as funcs

logit_bias = {
#   'As',        'as',       ' an',      'AI',          ' AI',        ' language',  ' model',     'model',           
    '1722': -10, '292': -10, '281': -10, '20185': -100, '9552': -100, '3303': -100, '2746': -100, '19849': -100, 
#   'sorry',       ' sorry',     ' :',      '3',     ' n',     'ya'
    '41599': -100, '7926': -100, '1058': 1, '18': 1, '299': 5, '3972': 5
    }

# temperature = 0.5
# frequency_penalty = 0.2
# presence_penalty = 0.5


timeout = 20

default_api_base = openai.api_base


def update_base_url():
    if opts.gpt == "custom":
        openai.api_base = opts.custom_api_url
    else:
        openai.api_base = default_api_base

update_base_url()

functions=[
    {
        "name": "get_user_count",
        "description": "Get the current number of players in the current world instance. Needs to be refreshed every time as the number of players changes constantly.",
        "parameters": {
            "type": "object",
            "properties": {
                "count": {
                    "type": "string",
                    "description": "Return: The number of players in the current world instance"
                    }
            }
        }
    },
    {
        "name": "get_user_list",
        "description": "Get a list of the names of all players in the current world instance. Needs to be refreshed every time as the list of players changes constantly.",
        "parameters": {
            "type": "object", 
            "properties": {
                "names": {
                    "type": "array",
                    "description": "Return: A list of the names of all players in the current world instance",
                    "items": {"type": "string"}
                    }
            }
        }
    },
    {
        "name": "get_vrchat_player_count",
        "description": "Get the number of total active players across all of VRChat right now. Refreshes every 60 seconds.",
        "parameters": {
            "type": "object", 
            "properties": {
                "names": {
                    "type": "string",
                    "description": "Return: The number of concurrent active players across all of VRChat"
                    }
            }
        }
    }
]

def generate(text, return_completion=False):
    """ Sends text to OpenAI, gets the response, and returns it """
    opts.generating = True
    while len(opts.message_array) > opts.max_conv_length:  # Trim down chat buffer if it gets too long
        opts.message_array.pop(0)
    # Add user's message to the chat buffer
    opts.message_array.append({"role": "user", "content": text})
    # Init system prompt with date and add it persistently to top of chat buffer
    system_prompt_object = generate_system_prompt_object()
    message_plus_system = system_prompt_object + opts.message_array
    err = None
    gpt_snapshot = "gpt-3.5-turbo-0613" if opts.gpt == "GPT-3" else "gpt-4-0613" if opts.gpt == "GPT-4" else "custom"
    try:
        vrc.chatbox('🤔 Thinking...')
        start_time = time.perf_counter()
        completion = openai.ChatCompletion.create(
            model=gpt_snapshot,
            messages=message_plus_system,
            max_tokens=opts.max_tokens,
            temperature=opts.temperature,
            frequency_penalty=opts.frequency_penalty,
            presence_penalty=opts.presence_penalty,
            top_p=opts.top_p,
            min_p=opts.min_p,
            top_k=opts.top_k,
            timeout=timeout,
            stream=True,
            logit_bias=logit_bias,
            functions=functions,
            function_call="auto"
            )
        if return_completion:
            return completion
        completion_text = ''
        is_function_call = False
        function_args = {}
        print("\n>AI: ", end='')
        for chunk in completion:
            event_text = ''
            chunk_message = chunk['choices'][0]['delta']  # extract the message
            if chunk_message.get('content'):
                event_text = chunk_message['content']
            print(event_text, end='')
            sys.stdout.flush()
            completion_text += event_text  # append the text
            if chunk['choices'][0]['delta'].get('function_call'):
                is_function_call = True
                function_args = chunk['choices'][0]['delta']["function_call"]
                break
        end_time = time.perf_counter()
        if is_function_call:
            funcs.v_print(f'--OpenAI Function call took {end_time - start_time:.3f}s')
            print("[Running Function...]")
            return call_function(function_args)
        print()
        funcs.v_print(f'--OpenAI API took {end_time - start_time:.3f}s')
        # result = completion.choices[0].message.content
        result = completion_text
        opts.message_array.append({"role": "assistant", "content": result})
        # print(f"\n>AI: {result}")
        opts.generating = False
        return result
    except openai.APIError as e:
        err = e
        print(f"!!Got API error from OpenAI: {e}")
        return None
    except openai.InvalidRequestError as e:
        err = e
        print(f"!!Invalid Request: {e}")
        return None
    except openai.OpenAIError as e:
        err = e
        print(f"!!Got OpenAI Error from OpenAI: {e}")
        return None
    except Exception as e:
        err = e
        print(f"!!Exception: {e}")
        return None
    finally:
        opts.generating = False
        vrc.clear_prop_params()
        if err is not None: 
            vrc.chatbox(f'⚠ {err}')
            return None


def get_completion(text):
    """ Sends text to OpenAI, gets the response, and returns the raw completion object """
    while len(opts.message_array) > opts.max_conv_length:  # Trim down chat buffer if it gets too long
        opts.message_array.pop(0)
    # Add user's message to the chat buffer
    opts.message_array.append({"role": "user", "content": text})
    # Init system prompt with date and add it persistently to top of chat buffer
    system_prompt_object = generate_system_prompt_object()
    message_plus_system = system_prompt_object + opts.message_array
    # err = None
    gpt_snapshot = "gpt-3.5-turbo-0613" if opts.gpt == "GPT-3" else "gpt-4-0613" if opts.gpt == "GPT-4" else "custom"
    try:
        # vrc.chatbox('📡 Sending to OpenAI...')
        # start_time = time.perf_counter()
        return openai.ChatCompletion.create(
            model=gpt_snapshot,
            messages=message_plus_system,
            max_tokens=opts.max_tokens,
            temperature=opts.temperature,
            frequency_penalty=opts.frequency_penalty,
            presence_penalty=opts.presence_penalty,
            top_p=opts.top_p,
            min_p=opts.min_p,
            top_k=opts.top_k,
            timeout=timeout,
            stream=True,
            logit_bias=logit_bias
            )
    except Exception as e:
        # err = e
        print(f"!!Exception: {e}")
        return None


def call_function(function_args):
    """ Runs a function whenever CGPT suggests one to be called, then returns the result from CGPT """
    function_name = function_args.get("name")
    function_content = ""
    
    if function_name == "get_user_count":
        function_content = str(funcs.get_player_count())

    elif function_name == "get_user_list":
        user_list = funcs.get_player_list()
        function_content = ', '.join(['"{0}"'.format(item) for item in user_list])

    elif function_name == "get_vrchat_player_count":
        function_content = funcs.get_vrchat_player_count()
        if function_content is None:
            function_content = "An error occurred getting the player count."

    function_call_message_object = {
        "role": "assistant",
        "content": "",
        "function_call": function_args
    }
    function_return_message_object = {
        "role": "function",
        "name": function_name,
        "content": function_content
    }
    opts.message_array.append(function_call_message_object)
    opts.message_array.append(function_return_message_object)

    # Init system prompt with date and add it persistently to top of chat buffer
    system_prompt_object = generate_system_prompt_object()
    message_plus_system = system_prompt_object + opts.message_array
    # err = None
    gpt_snapshot = "gpt-3.5-turbo-0613" if opts.gpt == "GPT-3" else "gpt-4-0613" if opts.gpt == "GPT-4" else "custom" 
    try:
        completion = openai.ChatCompletion.create(
            model=gpt_snapshot,
            messages=message_plus_system,
            max_tokens=opts.max_tokens,
            temperature=opts.temperature,
            frequency_penalty=opts.frequency_penalty,
            presence_penalty=opts.presence_penalty,
            timeout=timeout,
            logit_bias=logit_bias
            )
        result = completion["choices"][0]["message"]["content"]
        opts.message_array.append({"role": "assistant", "content": result})
        print(result)
        return result
    except Exception as e:
        # err = e
        print(f"!!Exception: {e}")
        return None
    

def generate_system_prompt_object():
    # create object with system prompt and other realtime info
    
    content = "\n"
    content += f' The current date and time is {datetime.now().strftime("%A %B %d %Y, %I:%M:%S %p")} Eastern Standard Time.'
    if opts.gpt != 'custom':
        content += f' You are using {opts.gpt} from OpenAI.'
    if (funcs.log_parser.running):
        content += "\nHere is some information about what's happening in the current VRChat world:"
        content += f'\nWorld Name: {funcs.log_parser.world_name}'
        content += f'\nInstance ID: {funcs.log_parser.instance_id}'
        content += f'\nInstance Privacy: {funcs.log_parser.instance_privacy}'
        
        player_list = funcs.get_player_list()
        player_count = funcs.get_player_count()
        if player_list != None and player_count != None:
            content += f'\nThere are {player_count} players in this instance: '
            player_list = ', '.join([f'"{item}"' for item in player_list]) # formats it to look like a python list, might inference better idk
            player_list = f"[{player_list}]"
            content += player_list
    
    content += "\n\n"

    system_prompt = [{"role": "system", "content":
           opts.system_prompt
           + content}]
    return system_prompt
