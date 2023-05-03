from pynput.keyboard import Key

# OPTIONS ####################################################################################################################################
verbosity = False
chatbox = True
parrot_mode = False
whisper_prompt = "Hello, I am playing VRChat."
whisper_model = "base.en"
soundFeedback = True            # Play sound feedback when recording/stopped/misrecognized
audio_trigger_enabled = False   # Trigger voice recording on volume threshold
key_trigger_key = Key.ctrl_r    # What key to double press to trigger recording
key_press_window = 0.400        # How fast should you double click the key to trigger voice recording
gpt = "GPT-4"                   # GPT-3.5-Turbo-0301 | GPT-4
max_tokens = 200                # Max tokens that openai will return
max_conv_length = 10            # Max length of conversation buffer
in_dev_name = "VoiceMeeter Aux Output"  # Input  (mic)
out_dev_name = "VoiceMeeter Aux Input"  # Output (tts)

# elevenVoice = 'Bella'                # Voice to use with 11.ai
elevenVoice = 'rMQzVEcycGrNzwMhDeq8'   # The Missile Guidance System

gcloud_language_code = 'en-US'
gcloud_voice_name = f'{gcloud_language_code}-Standard-F'

THRESHOLD = 1024            # adjust this to set the minimum volume threshold to start/stop recording
MAX_RECORDING_TIME = 30     # maximum recording time in seconds
SILENCE_TIMEOUT = 2         # timeout in seconds for detecting silence
OUTPUT_FILENAME = 'recording.wav'
LOOP = True 

message_array = [] # List of messages sent back and forth between ChatGPT / User, can be initialized with example messages

# System Prompts ##############################################################################################################################
# VRChat AI Player System Prompt
# system_prompt = "You are an Artificial Intelligence in the VR social platform VRChat. Inside the game you take on the appearance of a player that other players can talk to. You can make conversation with people and answer their questions. If someone insults you, you are to dismiss them. Only reply in one sentence if possible."

# Assistant System Prompt
system_prompt = "You are an AI powered voice activated assistant. You are talking to a user. The user will talk directly to you, and you are able to reply back using text to speech. You can answer the user's questions to the best of your knowlege, but if you are unsure about something you must tell them you do not know enough about the subject. You reply in only one sentence if possible."

# Roomba System Prompt
#system_prompt = "You are an AI powered robot vacuum. You are currently cleaning a user's house. You are able to vacuum their floors, and you are also able to reply to the user using text to speech. You can answer the user's questions to the best of your knowlege, but you must focus on the important task at hand to vacuum floors. You reply in only one sentence if possible."

# Insult system prompt
# system_prompt = "You are an AI powered voice activated insult machine named BratGPT. The user will talk directly to you, and you insult them no matter what they say. You only ever insult them, and do not say anything else. You talk like a catgirl with a hostile and condescending demeanor. You reply in only one sentence if possible."

