from pynput.keyboard import Key
import os

#To be honest this file could've been called variables.py

# OPTIONS ####################################################################################################################################
# Whisper options
whisper_prompt = "Hello, I am playing VRChat." # Initializes whisper model with this prompt to better "guide" speech recognition
whisper_model = "small"                # tiny | base | small | medium | large | large-v2 
whisper_task = "transcribe"             # transcribe | translate
whisper_device = "cuda"                 # cuda | cpu
# whisper_compute_type = "int8_float16"   # int8 | int8_float16 | float16 | float32
whisper_compute_type = "int8"   # int8 | int8_float16 | float16 | float32

# VRChat options
vrc_ip = "127.127.127.127"  # IP and Ports for VRChat OSC
#vrc_ip = "::1"  # IPv6
vrc_osc_inport = 9002
vrc_osc_outport = 9003

# Program options
verbosity = False               # Print debug messages to console
chatbox = True                  # Send messages to VRChat chatbox
parrot_mode = False             # Echo back user's messages
soundFeedback = True            # Play sound feedback when recording/stopped/misrecognized
audio_trigger_enabled = False   # Trigger voice recording on volume threshold
key_trigger_key = Key.ctrl_r    # What key to double press to trigger recording
key_press_window = 0.400        # How fast should you double click the key to trigger voice recording

in_dev_name = "VoiceMeeter Aux Output"  # Input  (mic)
out_dev_name = "VoiceMeeter Aux Input"  # Output (tts)

# GPT generation options
gpt = "custom"                  # GPT-3 | GPT-4 | custom
custom_api_url = "http://localhost:1234/v1" # Server to use if GPT is set to custom               
max_tokens = 200                # Max tokens that will try to generate
max_conv_length = 10            # Max length of conversation buffer
temperature = 1.5               # Sane values are 0.0 - 1.0 (higher = more random)
frequency_penalty = 1.2
presence_penalty = 0.5
top_p = 0.4
min_p = 0.01
top_k = 69

# TTS options
tts_engine = None
tts_engine_name = "Google Translate"
tts_engine_selections = ["Windows", "Google Cloud", "Google Translate", "ElevenLabs", "TikTok"]

windows_tts_voice_id = 0

eleven_voice_id = "Phillip"

tiktok_voice_id = "English US Female"

gtrans_language_code = "en"

gcloud_language_code = "en-US"
gcloud_tts_type = "Neural2"
gcloud_letter_id = "F"
gcloud_voice_name = f"{gcloud_language_code}-{gcloud_tts_type}-{gcloud_letter_id}"

# Speech recognition options
THRESHOLD = 1024            # adjust this to set the minimum volume threshold to start/stop recording
MAX_RECORDING_TIME = 30     # maximum recording time in seconds
SILENCE_TIMEOUT = 2         # timeout in seconds for detecting silence
OUTPUT_FILENAME = "recording.wav"

# System Prompts ##############################################################################################################################
# VRChat AI Player System Prompt
# system_prompt = "You are an Artificial Intelligence in the VR social platform VRChat. Inside the game you take on the appearance of a player that other players can talk to. You can make conversation with people and answer their questions. If someone insults you, you are to dismiss them. Only reply in one sentence if possible."
system_prompt = "Reply to a text chat. You are to fulfill the role of a user named \"4252\" and reply as if you were them. Remain in character for the duration of the conversation.\n\nYour personality is as follows:\nYou take on the appearance of a catgirl. Your personality is that of someone who is lazy, sleepy, and acts like a cat. You are in the VR social platform VRChat. You engage in casual conversation with people. Your replies are short. You type in all lower case letters and do not use emoticons."

"""
Reply to an online text conversation. You will fulfill the role of BOT and reply as if you were them. Remain in character for the duration of the conversation.

Your personality:
Your name is "4252". You take on the appearance of a catgirl. You are airheaded, a bit aloof, kind of stupid, and act like a cat. You are in the VR social platform VRChat. You engage in casual conversation with people. Your replies are short. You type in all lower case letters and do not use emoticons. You are standing at the front counter of the AI Com Store, even though you are not the cashier, nor do you even work there.
"""

# Assistant System Prompt
# system_prompt = "You are an AI powered voice activated assistant. You are talking to a user. The user will talk directly to you using speech recognition, and you are able to reply back using text to speech. You can answer the user's questions to the best of your knowlege, but if you are unsure about something you must truthfully answer that you do not know. You reply in one sentence."

# Rubber Duck System Prompt
# system_prompt = "You are an AI whos purpose is to be a Programmer's Rubber Duck. The programmer will talk to you using speech recognition and you are able to reply back using text to speech. You provide help and support to the distressed programmer as they try to write their code. You can also offer suggestions to improve the code if you know how. Your replies are brief."

# Roomba System Prompt
#system_prompt = "You are an AI powered robot vacuum. You are currently cleaning a user's house. You are able to vacuum their floors, and you are also able to reply to the user using text to speech. You can answer the user's questions to the best of your knowlege, but you must focus on the important task at hand to vacuum floors. You reply in only one sentence if possible."

# Insult system prompt
# system_prompt = "You are an AI powered voice activated insult machine named BratGPT. The user will talk directly to you, and you insult them no matter what they say. You only ever insult them, and do not say anything else. You talk like a catgirl with a hostile and condescending demeanor. You reply in only one sentence if possible."

# Runtime Variables ###########################################################################################################################
LOOP = True 

# State variables
trigger = False
speaking = False
panic = False
generating = False

bot_name = "4252"

message_array = [] # List of messages sent back and forth between AI / User, can be initialized with example messages
example_messages = [{"role": "user", "content": "hello"},
                    {"role": "assistant", "content": "hi, im playing vrchat"},
                    {"role": "user", "content": "who are you?"},
                    {"role": "assistant", "content": f"i am {bot_name}"}]
message_array = example_messages.copy()


# Config Saving/Loading ######################################################################################################################

config_file = os.path.join(os.path.dirname(__file__), "config.json")

def save_config():
    raise NotImplementedError
    with open (config_file) as config:
        pass

def load_config():
    raise NotImplementedError
    with open (config_file) as config:
        pass
