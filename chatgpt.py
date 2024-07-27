# chatgpt.py (c) 2023 MissingNO123
# Description: This module contains functions to handle the main chat generation loop. It sends messages to an OpenAI API-compatible model and processes the streamed token responses. The module also contains functions to dynamically generate system prompts and call OpenAI functions. It is also able to return the raw completion object to be handled by other modules.

import openai
import time, sys
from datetime import datetime

import vrcutils as vrc
import options as opts
import functions as funcs
import embeddings as emb
emb.load_memory_from_file()

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

headers = {
    "HTTP-Referer": "https://github.com/MissingNO123/VRChat_AI_Assistant/",
    "X-Title": "VRChat AI Assistant"
}

providers = {
    "order": [
        "Fireworks", 
        "OctoAI", 
        "Novita", 
        "Together"
    ],
    "allow_fallbacks": False    
}


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

def generate(text="", return_completion=False):
    """ Sends text to OpenAI, gets the response, and returns it """
    opts.generating = True
    while len(opts.message_array) > opts.max_conv_length:  # Trim down chat buffer if it gets too long
        opts.message_array.pop(0)
    # Init system prompt with date and add it persistently to top of chat buffer
    system_prompt_object = generate_system_prompt_object()
    message_plus_system = system_prompt_object 
    if not any(msg in opts.message_array[:len(opts.example_messages)] for msg in opts.example_messages):
        message_plus_system += opts.example_messages # checks if any of the example messages are already in the message array
    message_plus_system += opts.message_array
    err = None
    gpt_snapshot = "gpt-3.5-turbo-0613" if opts.gpt == "GPT-3" else "gpt-4-0613" if opts.gpt == "GPT-4" else opts.custom_model_name if opts.gpt == "custom" else "gpt-3.5-turbo-0613"
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
            headers=headers,
            provider=providers,
            # logit_bias=logit_bias,  # doesn't work for LLaMA
            # functions=functions,    # eats tokens
            # function_call="auto"
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
        result = completion_text.strip()
        funcs.append_bot_message(funcs.inverse_title_case(result))
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


# def get_completion(text):
#     """ Sends text to OpenAI, gets the response, and returns the raw completion object """
#     while len(opts.message_array) > opts.max_conv_length:  # Trim down chat buffer if it gets too long
#         opts.message_array.pop(0)
#     # Add user's message to the chat buffer
#     funcs.append_user_message(text)
#     # Init system prompt with date and add it persistently to top of chat buffer
#     system_prompt_object = generate_system_prompt_object()
#     message_plus_system = system_prompt_object 
#     if not any(msg in opts.message_array[:len(opts.example_messages)] for msg in opts.example_messages):
#         message_plus_system += opts.example_messages # checks if any of the example messages are already in the message array
#     message_plus_system += opts.message_array
#     # err = None
#     gpt_snapshot = "gpt-3.5-turbo-0613" if opts.gpt == "GPT-3" else "gpt-4-0613" if opts.gpt == "GPT-4" else "custom"
#     try:
#         # vrc.chatbox('📡 Sending to OpenAI...')
#         # start_time = time.perf_counter()
#         return openai.ChatCompletion.create(
#             model=gpt_snapshot,
#             messages=message_plus_system,
#             max_tokens=opts.max_tokens,
#             temperature=opts.temperature,
#             frequency_penalty=opts.frequency_penalty,
#             presence_penalty=opts.presence_penalty,
#             top_p=opts.top_p,
#             min_p=opts.min_p,
#             top_k=opts.top_k,
#             timeout=timeout,
#             stream=True,
#             logit_bias=logit_bias
#             )
#     except Exception as e:
#         # err = e
#         print(f"!!Exception: {e}")
#         return None


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
    message_plus_system = system_prompt_object 
    if not any(msg in opts.message_array[:len(opts.example_messages)] for msg in opts.example_messages):
        message_plus_system += opts.example_messages # checks if any of the example messages are already in the message array
    message_plus_system += opts.message_array
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
        funcs.append_bot_message(funcs.inverse_title_case(result))
        print(result)
        return result
    except Exception as e:
        # err = e
        print(f"!!Exception: {e}")
        return None
    
prev_semantic_results = ""
def generate_system_prompt_object():
    # create object with system prompt and other realtime info
    system_prompt = opts.system_prompt.format(bot_name=opts.bot_name, bot_personality=opts.bot_personality)

    global prev_semantic_results
    # attempt to look up relevant details from memory
    semantic_results = emb.search_memory(opts.message_array[-1]["content"])
    semantic_results = " ".join(semantic_results)

    # persist memory results for at least one extra generation 
    # but remove any repeated sentences to save tokens
    if semantic_results != "" and prev_semantic_results != "":
        # Find common text and remove it from prev_semantic_results
        for sentence in semantic_results.split("."):
            if sentence in prev_semantic_results:
                prev_semantic_results = prev_semantic_results.replace(sentence, "")
    
    content = ""

    if semantic_results != "": 
        content += f' Extra info: {semantic_results}'
        if prev_semantic_results != "":
            content += f' {prev_semantic_results}'
    prev_semantic_results = semantic_results

    content += f' The current date and time is {datetime.now().strftime("%A %B %d %Y, %I:%M %p")}.'
    if opts.gpt != 'custom':
        content += f' You are using {opts.gpt} from OpenAI.'
    if (vrc.log_parser.vrc_is_running):
        content += " In VRChat, "
        content += f'The world {opts.bot_name} is in is named \"{vrc.log_parser.world_name}\"'
        content += f', Instance ID:{vrc.log_parser.instance_id}'
        content += f', and its privacy is {vrc.log_parser.instance_privacy}.'
        
        player_list = vrc.get_player_list()
        player_count = vrc.get_player_count()
        if player_list != None and player_count != None:
            content += f' There are {player_count} players with you in the world: '
            player_list = ', '.join([f'"{item}"' for item in player_list]) 
            player_list = f"[{player_list}]" # formats it to look like a python list, might inference better idk
            content += player_list
    
    content += "\n\n"

    system_prompt = [{"role": "system", "content":
           system_prompt
           + content}]
    return system_prompt

if __name__ == "__main__":
    print("You ran the wrong file")
    quit()