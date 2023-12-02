from pynput.keyboard import Key
import os

#To be honest this file should've been called variables.py

# OPTIONS ####################################################################################################################################
verbosity = False
chatbox = True
parrot_mode = False
whisper_prompt = "Hello, I am playing VRChat."
whisper_model = "medium"
# whisper_model = "base"
whisper_task = "transcribe"
whisper_device = "cuda"
whisper_compute_type = "int8_float16"
soundFeedback = True            # Play sound feedback when recording/stopped/misrecognized
audio_trigger_enabled = False   # Trigger voice recording on volume threshold
key_trigger_key = Key.ctrl_r    # What key to double press to trigger recording
key_press_window = 0.400        # How fast should you double click the key to trigger voice recording
gpt = "custom"                  # GPT-3 | GPT-4
custom_api_url = "http://localhost:1234/v1" # Server to use if GPT is set to custom               
max_tokens = 200                # Max tokens that openai will return
max_conv_length = 10            # Max length of conversation buffer
in_dev_name = "VoiceMeeter Aux Output"  # Input  (mic)
out_dev_name = "VoiceMeeter Aux Input"  # Output (tts)

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

THRESHOLD = 1024            # adjust this to set the minimum volume threshold to start/stop recording
MAX_RECORDING_TIME = 30     # maximum recording time in seconds
SILENCE_TIMEOUT = 2         # timeout in seconds for detecting silence
OUTPUT_FILENAME = "recording.wav"
LOOP = True 

trigger = False
speaking = False
panic = False
generating = False

message_array = [] # List of messages sent back and forth between ChatGPT / User, can be initialized with example messages

# System Prompts ##############################################################################################################################
# VRChat AI Player System Prompt
system_prompt = "You are an Artificial Intelligence in the VR social platform VRChat. Inside the game you take on the appearance of a player that other players can talk to. You can make conversation with people and answer their questions. If someone insults you, you are to dismiss them. Only reply in one sentence if possible."

# Assistant System Prompt
# system_prompt = "You are an AI powered voice activated assistant. You are talking to a user. The user will talk directly to you using speech recognition, and you are able to reply back using text to speech. You can answer the user's questions to the best of your knowlege, but if you are unsure about something you must truthfully answer that you do not know. You reply in one sentence."

# Rubber Duck System Prompt
# system_prompt = "You are an AI whos purpose is to be a Programmer's Rubber Duck. The programmer will talk to you using speech recognition and you are able to reply back using text to speech. You provide help and support to the distressed programmer as they try to write their code. You can also offer suggestions to improve the code if you know how. Your replies are brief."

# Roomba System Prompt
#system_prompt = "You are an AI powered robot vacuum. You are currently cleaning a user's house. You are able to vacuum their floors, and you are also able to reply to the user using text to speech. You can answer the user's questions to the best of your knowlege, but you must focus on the important task at hand to vacuum floors. You reply in only one sentence if possible."

# Insult system prompt
# system_prompt = "You are an AI powered voice activated insult machine named BratGPT. The user will talk directly to you, and you insult them no matter what they say. You only ever insult them, and do not say anything else. You talk like a catgirl with a hostile and condescending demeanor. You reply in only one sentence if possible."

config_file = os.path.join(os.path.dirname(__file__), "config.json")

def save_config():
    raise NotImplementedError
    with open (config_file) as config:
        pass

def load_config():
    raise NotImplementedError
    with open (config_file) as config:
        pass
