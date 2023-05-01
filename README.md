# VRChat AI Assistant

[OpenAI](https://openai.com/) [GPT-4](https://openai.com/product/gpt-4) powered [AI Assistant](https://en.wikipedia.org/wiki/Virtual_assistant) that integrates with [VRChat](https://hello.vrchat.com/) using [OSC](https://docs.vrchat.com/docs/osc-overview)
This program is currently in an ["it works on my machine"](https://i.redd.it/6u77tkmyaomz.jpg) state, and will most likely not work on yours without a ton of tinkering.
For example, it relies on [VB-Audio VoiceMeeter Banana](https://vb-audio.com/Voicemeeter/banana.htm) to play audio over the microphone.
Either way, I'm uploading this privately just to have it up here.

## Usage

Run either `start_assistant.ps1` or `.bat`, which will automatically activate the virtual environment and start the program. If you for whatever reason are not using a virtual environment, just run `python assistant.py`.

The program will start listening when it detects either the parameters `ChatGPT` or `ChatGPT_PB` get triggered on your avatar. For example, you could trigger it either from the Action Menu, or using a Contact Sender/Receiver pair. Alternatively, double-tap the Right Control key to invoke it manually. Voice gets transcribed to text with [Faster Whisper](https://github.com/guillaumekln/faster-whisper/), which is forwarded to OpenAI, and the response is read out with [Google Cloud TTS](https://cloud.google.com/text-to-speech/) or optionally one of [11.ai](https://beta.elevenlabs.io/) voice synthesis, [Google Translate](https://translate.google.com/), or [Windows](https://www.microsoft.com/en-ca/windows) [Default TTS](https://en.wikipedia.org/wiki/Microsoft_text-to-speech_voices). The response text is also fed into the VRChat Chatbox.

System commands are triggerable by saying "System" and the name of the command, which will also bypass sending it to OpenAI.

## Installation

Copy `.env.example` to `.env`, get your API keys from OpenAI and from ElevenLabs, and put them in the file. Get your Google Cloud Authentication file and put it in the project directory, then add the path to it in `.env`.

Activate a virtual environment in the `.\venv` folder using `python -m venv venv`. This can be skipped, but is recommended to not conflict with globally installed packages.
Install CUDA Toolkit and cuDNN and add their respective `\bin` folders to your PATH if you plan to use the GPU.
Install the required Python packages listed below using pip.
With GPU support, you *may* need to install the latest nightly version of [PyTorch](https://pytorch.org/get-started/locally/), or uninstall and re-install if you have an old version that doesn't work and/or wasn't compiled with CUDA support.
An example command for installing PyTorch nightly on Windows using pip with CUDA 11.8 support is as follows:

```batch
pip3 install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu118

```

## Requirements

Python 3.8 or higher with Pip. Highly recommended to use a [venv](https://docs.python.org/3/library/venv.html).

Required libraries: audioop, [python-dotenv](https://pypi.org/project/python-dotenv/), [elevenlabs](https://pypi.org/project/elevenlabs/), [faster-whisper](https://github.com/guillaumekln/faster-whisper/), [ffmpeg](https://github.com/jiashaokun/ffmpeg), [google-cloud-texttospeech](https://pypi.org/project/google-cloud-texttospeech/), [gtts](https://pypi.org/project/gTTS/), [openai](https://github.com/openai/openai-python), [pynput](https://pypi.org/project/pynput/), [python-osc](https://github.com/attwad/python-osc), [pyttsx3](https://pypi.org/project/pyttsx3/), and [customtkinter](https://github.com/TomSchimansky/CustomTkinter)

Most likely requires an [NVidia GPU](https://new.reddit.com/r/nvidia/comments/yc6g3u/rtx_4090_adapter_burned/). Not tested with AMD, but I doubt it will work. In that case, edit the file to use CPU instead of CUDA.
To use Faster Whisper, you need both [cuDNN](https://developer.nvidia.com/rdp/cudnn-archive) and [CUDA Toolkit 11.8](https://developer.nvidia.com/cuda-11-8-0-download-archive) in PATH. Otherwise, use OpenAI Whisper or use CPU inference.

The following files need to be copied over from `C:\Windows\Media` as I can't upload them to Github due to them being owned by Microsoft:

- Speech Misrecognition.wav
- Speech Off.wav
- Speech On.wav
- Speech Sleep.wav

## Copyright

Copyright (c) 2023 MissingNO123. All rights reserved.

The contents of this repository, including all code, documentation, and other materials, unless otherwise specified, are the exclusive property of MissingNO123 and are protected by copyright law. Unauthorized reproduction, distribution, or disclosure of the contents of this repository, in whole or in part, without the express written permission of MissingNO123 is strictly prohibited.

The original version of the Software was authored on the 17th of March, 2023.
