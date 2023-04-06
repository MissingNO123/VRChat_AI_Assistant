# VRChat AI Assistant
GPT-4 powered AI Assistant that integrates with VRChat
This program is currently in an "it works on my machine" state, and will most likely not work without a ton of tinkering.
For example, it relies on VB-Audio VoiceMeeter Banana to play audio over the microphone.

# Usage
The program will start listening when it detects either the parameters ChatGPT or ChatGPT_PB. Alternatively, double-tap the Right Control key. Voice gets forwarded to OpenAI, and the response is read out with TTS and fed into the VRChat Chatbox. 

System commands are triggerable by saying "System" and the name of the command, which will also bypass OpenAI.

# Requirements
Python 3.8 or higher with Pip. Reccomended to use a venv. 

Required libraries: audioop, dotenv, ElevenLabs, faster_whisper, ffmpeg, google.cloud, gtts, openai, pynput, python-osc, pyttsx3.

The following files need to be grabbed from C:\Windows\Media as I can't upload them to Github due to them being owned by Windows:

- Speech Misrecognition.wav
- Speech Off.wav
- Speech On.wav
- Speech Sleep.wav