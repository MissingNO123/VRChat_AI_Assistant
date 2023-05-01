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