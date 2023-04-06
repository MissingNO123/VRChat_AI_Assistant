# VRChat AI Assistant
OpenAI GPT-4 powered AI Assistant that integrates with VRChat
This program is currently in an "it works on my machine" state, and will most likely not work on yours without a ton of tinkering.
For example, it relies on VB-Audio VoiceMeeter Banana to play audio over the microphone.
Either way, I'm uploading this privately just to have it up here.

# Usage
The program will start listening when it detects either the parameters ChatGPT or ChatGPT_PB. For example, you could trigger it either from the Action Menu, or using a Contact Sender/Receiver pair on your avatar. Alternatively, double-tap the Right Control key to invoke it manually. Voice gets forwarded to OpenAI, and the response is read out with either Google Cloud TTS or 11.ai voice synthesis, and text is fed into the VRChat Chatbox. 

System commands are triggerable by saying "System" and the name of the command, which will bypass OpenAI.

# Requirements
Python 3.8 or higher with Pip. Reccomended to use a venv. 

Required libraries: audioop, dotenv, ElevenLabs, faster_whisper, ffmpeg, google.cloud, gtts, openai, pynput, python-osc, pyttsx3.

Most likely requires an nVidia GPU. Not tested with AMD, but I doubt it will work. In that case, edit the file to use CPU instead of CUDA.
To use Faster Whisper, you need both cuDNN and CUDA Toolkit 11.8 in PATH. Otherwise, use OpenAI Whisper or use CPU inference. 

The following files need to be copied over from `C:\Windows\Media` as I can't upload them to Github due to them being owned by Microsoft:

- Speech Misrecognition.wav
- Speech Off.wav
- Speech On.wav
- Speech Sleep.wav

# Copyright
Copyright (c) 2023 MissingNO123. All rights reserved.

The contents of this repository, including all code, documentation, and other materials, unless otherwise specified, are the exclusive property of MissingNO123 and are protected by copyright law. Unauthorized reproduction, distribution, or disclosure of the contents of this repository, in whole or in part, without the express written permission of MissingNO123 is strictly prohibited.

The original version of the Software was authored on the 17th of March, 2023.