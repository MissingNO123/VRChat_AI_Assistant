import json
from pynput.keyboard import Key
import os

#To be honest this file could've been called variables.py

# OPTIONS ####################################################################################################################################
# Whisper options
whisper_prompt = "Hello, I am playing VRChat." # Initializes whisper model with this prompt to better "guide" speech recognition
whisper_model = "medium"                  # tiny | base | small | medium | large | large-v2 
whisper_task = "transcribe"             # transcribe | translate
whisper_device = "cuda"                 # cuda | cpu
# whisper_compute_type = "int8_float16"   # int8 | int8_float16 | float16 | float32
whisper_compute_type = "int8_float16"   # int8 | int8_float16 | float16 | float32

# VRChat options
vrc_ip = "127.127.127.127"  # IP and Ports for VRChat OSC
# vrc_ip = "192.168.2.43"
#vrc_ip = "::1"  # IPv6
vrc_osc_inport = 9000
vrc_osc_outport = 9001

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

# System Prompt ##############################################################################################################################
bot_name = ""
bot_personality = ""
system_prompt = ""

# Runtime Variables ###########################################################################################################################
LOOP = True 

# State variables
trigger = False
speaking = False
panic = False
generating = False
bot_responded = True

message_array = [] # List of messages sent back and forth between AI / User, can be initialized with example messages
message_queue = [] # Queue of messages to be processed and added to message_array
example_messages = []


# Config Saving/Loading ######################################################################################################################
safe_keys = [
    "whisper_prompt",
    "whisper_model",
    "whisper_task",
    "whisper_device",
    "whisper_compute_type",
    "vrc_ip",
    "vrc_osc_inport",
    "vrc_osc_outport",
    "verbosity",
    "chatbox",
    "parrot_mode",
    "soundFeedback",
    "audio_trigger_enabled",
    "key_trigger_key",
    "key_press_window",
    "in_dev_name",
    "out_dev_name",
    "gpt",
    "custom_api_url",
    "max_tokens",
    "max_conv_length",
    "temperature",
    "frequency_penalty",
    "presence_penalty",
    "top_p",
    "min_p",
    "top_k",
    "tts_engine",
    "tts_engine_name",
    "tts_engine_selections",
    "windows_tts_voice_id",
    "eleven_voice_id",
    "tiktok_voice_id",
    "gtrans_language_code",
    "gcloud_language_code",
    "gcloud_tts_type",
    "gcloud_letter_id",
    "gcloud_voice_name",
    "THRESHOLD",
    "MAX_RECORDING_TIME",
    "SILENCE_TIMEOUT",
    "OUTPUT_FILENAME",
    "bot_name",
    "bot_personality",
    "system_prompt",
    "example_messages"
]

config_file = os.path.join(os.path.dirname(__file__), "config.json")
config_example = os.path.join(os.path.dirname(__file__), "config.example.json")
if not os.path.exists(config_file):
    if os.path.exists(config_example):
        os.copy(config_example, config_file)

def save_config():
    with open(config_file, 'w', encoding='utf8') as config:
        config_data = {k: v for k,v in globals().items() if k in safe_keys}
        trigger_key = str(config_data["key_trigger_key"])
        trigger_key = trigger_key[trigger_key.find(".")+1:]
        config_data["key_trigger_key"] = trigger_key
        json.dump(config_data, config, indent=2)

def load_config():
    with open (config_file, 'r', encoding='utf8') as config:
        config_data = json.load(config)
        # read in config data
        for key, value in config_data.items():
            if key in safe_keys:
                if not type(value) == type(globals()[key]):
                    if key == "key_trigger_key":
                        try:
                            trigger_key = getattr(Key, value)
                            value = trigger_key
                        except AttributeError:
                            print( f'!! { key } has wrong type in config file, not loading' )
                            continue   
                    else:
                        print( f'!! { key } has wrong type in config file, not loading' )
                        continue

                if key in globals():
                    globals()[key] = value
                else:
                    print( f'!! "{key}" correlates to setting but somehow isn\'t present in module, not loading' )
            else:
                print( f'!! "{key}" found in config file doesn\'t correlate to a setting' )
    
    message_array = example_messages.copy()


if os.path.exists(config_file):
    load_config()
    pass # for breakpoint
