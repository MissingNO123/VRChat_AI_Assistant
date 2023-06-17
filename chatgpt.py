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

temperature = 0.5
frequency_penalty = 0.2
presence_penalty = 0.5
timeout = 20

def generate(text):
    """ Sends text to OpenAI, gets the response, and returns it """
    while len(opts.message_array) > opts.max_conv_length:  # Trim down chat buffer if it gets too long
        opts.message_array.pop(0)
    # Add user's message to the chat buffer
    opts.message_array.append({"role": "user", "content": text})
    # Init system prompt with date and add it persistently to top of chat buffer
    system_prompt_object = [{"role": "system", "content":
                           opts.system_prompt
                           + f' The current date and time is {datetime.now().strftime("%A %B %d %Y, %I:%M:%S %p")} Eastern Standard Time.'
                           + f' You are using {opts.gpt} from OpenAI.'}]
    # create object with system prompt and chat history to send to OpenAI for generation
    message_plus_system = system_prompt_object + opts.message_array
    err = None
    gpt_snapshot = "gpt-3.5-turbo-0613" if opts.gpt == "GPT-3" else "gpt-4-0613"
    try:
        vrc.chatbox('📡 Sending to OpenAI...')
        start_time = time.perf_counter()
        completion = openai.ChatCompletion.create(
            model=gpt_snapshot,
            messages=message_plus_system,
            max_tokens=opts.max_tokens,
            temperature=temperature,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            timeout=timeout,
            stream=True,
            logit_bias=logit_bias
            )
        completion_text = ''
        print("\n>ChatGPT: ", end='')
        for chunk in completion:
            event_text = ''
            chunk_message = chunk['choices'][0]['delta']  # extract the message
            if chunk_message.get('content'):
                event_text = chunk_message['content']
            print(event_text, end='')
            sys.stdout.flush()
            completion_text += event_text  # append the text
        end_time = time.perf_counter()
        print()
        funcs.v_print(f'--OpenAI API took {end_time - start_time:.3f}s')
        # result = completion.choices[0].message.content
        result = completion_text
        opts.message_array.append({"role": "assistant", "content": result})
        # print(f"\n>ChatGPT: {result}")
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
        print(f"!!Other Exception: {e}")
        return None
    finally:
        vrc.set_parameter('CGPT_Result', True)
        vrc.set_parameter('CGPT_End', True)
        if err is not None: 
            vrc.chatbox(f'⚠ {err}')
            return None
        
def get_completion(text):
    """ Sends text to OpenAI, gets the response, and returns it """
    if len(opts.message_array) > opts.max_conv_length:  # Trim down chat buffer if it gets too long
        opts.message_array.pop(0)
    # Add user's message to the chat buffer
    opts.message_array.append({"role": "user", "content": text})
    # Init system prompt with date and add it persistently to top of chat buffer
    system_prompt_object = [{"role": "system", "content":
                        opts.system_prompt
                        + f' The current date and time is {datetime.now().strftime("%A %B %d %Y, %I:%M:%S %p")} Eastern Standard Time.'
                        + f' You are using {opts.gpt} from OpenAI.'}]
    # create object with system prompt and chat history to send to OpenAI for generation
    message_plus_system = system_prompt_object + opts.message_array
    # err = None
    gpt_snapshot = "gpt-3.5-turbo-0613" if opts.gpt == "GPT-3" else "gpt-4-0613"
    try:
        # vrc.chatbox('📡 Sending to OpenAI...')
        # start_time = time.perf_counter()
        return openai.ChatCompletion.create(
            model=gpt_snapshot,
            messages=message_plus_system,
            max_tokens=opts.max_tokens,
            temperature=temperature,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            timeout=timeout,
            stream=True,
            logit_bias=logit_bias
            )
    except Exception as e:
        # err = e
        print(f"!!Other Exception: {e}")
        return None