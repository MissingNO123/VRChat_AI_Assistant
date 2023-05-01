# Copyright (C) MissingNO123 17 Mar 2023

import sys
import time
full_start_time = time.time()
import audioop
from datetime import datetime
from dotenv import load_dotenv
from elevenlabs import ElevenLabs
from faster_whisper import WhisperModel
import ffmpeg
from google.cloud import texttospeech  # Cloud TTS
from gtts import gTTS
import openai
import os
import pyaudio
from pynput.keyboard import Key, Listener
from pythonosc import udp_client
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
import pyttsx3
import re
import shutil
import threading
# import torch
import wave
# import whisper
import uistuff
import options as opts

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')
eleven = ElevenLabs(os.getenv('ELEVENLABS_API_KEY'))

# OPTIONS ####################################################################################################################################
# opts.verbosity = False
# opts.chatbox = True
opts.parrot_mode = False
opts.whisper_prompt = "Hello, I am playing VRChat."
opts.whisper_model = "base.en"
opts.soundFeedback = True            # Play sound feedback when recording/stopped/misrecognized
opts.audio_trigger_enabled = False   # Trigger voice recording on volume threshold
opts.key_trigger_key = Key.ctrl_r    # What key to double press to trigger recording
opts.key_press_window = 0.400        # How fast should you double click the key to trigger voice recording
opts.gpt = "GPT-4"                   # GPT-3.5-Turbo-0301 | GPT-4
opts.max_tokens = 200                # Max tokens that openai will return
opts.max_conv_length = 10            # Max length of conversation buffer
opts.in_dev_name = "VoiceMeeter Aux Output"  # Input  (mic)
opts.out_dev_name = "VoiceMeeter Aux Input"  # Output (tts)

# elevenVoice = 'Bella'                # Voice to use with 11.ai
opts.elevenVoice = 'rMQzVEcycGrNzwMhDeq8'   # The Missile Guidance System

opts.gcloud_language_code = 'en-US'
opts.gcloud_voice_name = f'{opts.gcloud_language_code}-Standard-F'

opts.THRESHOLD = 1024            # adjust this to set the minimum volume threshold to start/stop recording
opts.MAX_RECORDING_TIME = 30     # maximum recording time in seconds
opts.SILENCE_TIMEOUT = 2         # timeout in seconds for detecting silence
opts.OUTPUT_FILENAME = 'recording.wav'
CHUNK_SIZE = 1024           # number of frames read at a time
FORMAT = pyaudio.paInt16    # PCM format (int16)
RATE = 48000                # sample rate in Hz

# System Prompts ##############################################################################################################################
# VRChat AI Player System Prompt
# systemPrompt = "You are an Artificial Intelligence in the VR social platform VRChat. Inside the game you take on the appearance of a player that other players can talk to. You can make conversation with people and answer their questions. If someone insults you, you are to dismiss them. Only reply in one sentence if possible."

# Assistant System Prompt
systemPrompt = "You are an AI powered voice activated assistant. You are talking to a user. The user will talk directly to you, and you are able to reply back using text to speech. You can answer the user's questions to the best of your knowlege, but if you are unsure about something you must tell them you do not know enough about the subject. You reply in only one sentence if possible."

# Roomba System Prompt
#systemPrompt = "You are an AI powered robot vacuum. You are currently cleaning a user's house. You are able to vacuum their floors, and you are also able to reply to the user using text to speech. You can answer the user's questions to the best of your knowlege, but you must focus on the important task at hand to vacuum floors. You reply in only one sentence if possible."

# Insult system prompt
# systemPrompt = "You are an AI powered voice activated insult machine named BratGPT. The user will talk directly to you, and you insult them no matter what they say. You only ever insult them, and do not say anything else. You talk like a catgirl with a hostile and condescending demeanor. You reply in only one sentence if possible."


# Variables ###################################################################################################################################
model = None    # Whisper model object
messageArr = [] # List of messages sent back and forth between ChatGPT / User, initialized with example messages

vb_out = None
vb_in = None

frames = []
lastFrame = None
recording = False
speaking = False
trigger = False
panic = False
silence_timeout_timer = None

key_press_window_timeup = time.time()

# Constants
pyAudio = pyaudio.PyAudio()

speech_on = "Speech On.wav"
speech_off = "Speech Sleep.wav"
speech_mis = "Speech Misrecognition.wav"

ip = "127.0.0.1"  # IP and Ports for VRChat OSC
inPort = 9000
outPort = 9001

LOOP = True

whisper_lock = threading.Lock()


# Functions and Class (singular) ##############################################################################################################
# Loads an audio file, play() will play it through vb aux input
class AudioFile:
    chunk = 1024

    def __init__(self, file):
        """ Init audio stream """
        init_audio()
        self.wf = wave.open(file, 'rb')
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=self.p.get_format_from_width(self.wf.getsampwidth()),
            channels=self.wf.getnchannels(),
            rate=self.wf.getframerate(),
            output_device_index=vb_in,
            output=True
        )

    def play(self):
        """ Play entire file """
        data = self.wf.readframes(self.chunk)
        while data != b'':
            self.stream.write(data)
            data = self.wf.readframes(self.chunk)
            if panic: break
        self.close()

    def close(self):
        """ Graceful shutdown """
        self.stream.close()
        self.p.terminate()


def verbose_print(text):
    if opts.verbosity:
        print(text)


def play_sound(file):
    """ Plays a sound, waits for it to finish before continuing """
    audio = AudioFile(file)
    audio.play()


def play_sound_threaded(file):
    """ Plays a sound without blocking the main thread """
    audio = AudioFile(file)
    thread = threading.Thread(target=audio.play)
    thread.start()


def save_recorded_frames(frames, filename=opts.OUTPUT_FILENAME):
    """ Saves recorded frames to a .wav file and sends it to whisper to transcribe it """
    if opts.soundFeedback:
        play_sound_threaded(speech_off)
    wf = wave.open(filename, 'wb')
    wf.setnchannels(2)
    wf.setsampwidth(pyAudio.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    verbose_print("~Recording saved")
    whisper_transcribe()
    verbose_print("~Waiting for sound...")


def old_whisper_transcribe():
    """ Transcribes audio in .wav file to text """
    import whisper
    if model is None: return
    vrc_chatbox('✍️ Transcribing...')
    verbose_print('~Transcribing...')
    start_time = time.time()

    # load the audio
    audio = whisper.load_audio(opts.OUTPUT_FILENAME)
    audio = whisper.pad_or_trim(audio)
    mel = whisper.log_mel_spectrogram(audio).to(model.device)

    # decode the audio
    options = whisper.DecodingOptions(prompt=opts.whisper_prompt, language='en')
    result = whisper.decode(model, mel, options)
    end_time = time.time()
    verbose_print(f"--Transcription took: {end_time - start_time:.3f}s, U: {result.no_speech_prob*100:.1f}%")

    # print the recognized text
    print(f"\n>User: {result.text}")

    # if not speech, dont send to cgpt
    if result.no_speech_prob > 0.5:
        vrc_chatbox('⚠ [unintelligible]')
        if opts.soundFeedback: play_sound_threaded(speech_mis)
        verbose_print(f"U: {result.no_speech_prob*100:.1f}%")
        tts('I didn\'t understand that!', 'en')
        vrc_set_parameter('VoiceRec_End', True)
        vrc_set_parameter('CGPT_Result', True)
        vrc_set_parameter('CGPT_End', True)
    else:
        # otherwise, forward text to ChatGPT
        vrc_set_parameter('VoiceRec_End', True)
        vrc_chatbox('📡 Sending to OpenAI...')
        chatgpt_req(result.text)


def whisper_transcribe():
    """ Transcribes audio in .wav file to text using Faster Whisper """
    if model is None:
        return
    vrc_chatbox('✍️ Transcribing...')
    verbose_print('~Transcribing...')

    with whisper_lock:
        start_time = time.time()

        # Initialize transcription object on the recording
        segments, info = model.transcribe(
            "recording.wav", beam_size=5, initial_prompt=opts.whisper_prompt, no_speech_threshold=0.4, log_prob_threshold=0.8)

        verbose_print(f'lang: {info.language}, {info.language_probability * 100:.1f}%')

        # if not speech, dont bother processing anything  
        if info.language_probability < 0.8 or info.duration <= (opts.SILENCE_TIMEOUT + 0.3):
            vrc_chatbox('⚠ [unintelligible]')
            if opts.soundFeedback:
                play_sound_threaded(speech_mis)
            play_sound('./prebaked_tts/Ididntunderstandthat.wav')
            vrc_set_parameter('VoiceRec_End', True)
            vrc_set_parameter('CGPT_Result', True)
            vrc_set_parameter('CGPT_End', True)
            end_time = time.time()
            verbose_print(f"--Transcription failed and took: {end_time - start_time:.3f}s")
            return

        # Transcribe and concatenate the text segments
        text = ""
        for segment in segments:
            text += segment.text
        text = text.strip()

        end_time = time.time()
    verbose_print(f"--Transcription took: {end_time - start_time:.3f}s")

    # print the recognized text
    print(f"\n>User: {text}")

    # if keyword detected, send to command handler instead
    if text.lower().startswith("system"):
        command = re.sub(r'[^a-zA-Z0-9]', '', text[text.find(' ') + 1:])
        handle_command(command.lower())
        vrc_set_parameter('VoiceRec_End', True)
        vrc_set_parameter('CGPT_Result', True)
        vrc_set_parameter('CGPT_End', True)
        return

    # Repeat input if parrot mode is on 
    if opts.parrot_mode:
        if opts.chatbox and len(text) > 140:
            cut_up_text(f'{text}')
        else:
            vrc_chatbox(f'{text}')
            tts(text)
        vrc_set_parameter('VoiceRec_End', True)
        vrc_set_parameter('CGPT_Result', True)
        vrc_set_parameter('CGPT_End', True)
    else:
        # otherwise, forward text to ChatGPT
        vrc_set_parameter('VoiceRec_End', True)
        vrc_chatbox('📡 Sending to OpenAI...')
        chatgpt_req(text)


def filter_for_tts(string):
    """ Makes words in input string pronuncable by TTS """
    replacements = {
        '`': '',
        '💬': '',
        '~': '',
        '*': '',
        'missingno': 'missing no',
        'missingo123': 'missing no one two three',
        'nya': 'nia',
        'nyaa': 'nia',
        'vrchat': 'VR Chat'
    }
    for word, replacement in replacements.items():
        word_pattern = re.escape(word)
        string = re.sub(word_pattern, replacement, string, flags=re.IGNORECASE)
    return string


def chatgpt_req(text):
    """ Sends text to OpenAI, gets the response, and puts it into the chatbox """
    if len(messageArr) > opts.max_conv_length:  # Trim down chat buffer if it gets too long
        messageArr.pop(0)
    # Add user's message to the chat buffer
    messageArr.append({"role": "user", "content": text})
    # Init system prompt with date and add it persistently to top of chat buffer
    systemPromptObject = [{"role": "system", "content":
                           systemPrompt
                           + f' The current date and time is {datetime.now().strftime("%A %B %d %Y, %I:%M:%S %p")} Eastern Standard Time.'
                           + f' You are using {opts.gpt} from OpenAI.'}]
    # create object with system prompt and chat history to send to OpenAI for generation
    messagePlusSystem = systemPromptObject + messageArr
    err = None
    try:
        start_time = time.time()
        completion = openai.ChatCompletion.create(
            model=opts.gpt.lower(),
            messages=messagePlusSystem,
            max_tokens=opts.max_tokens,
            temperature=0.5,
            frequency_penalty=0.2,
            presence_penalty=0.5,
            logit_bias={'1722': -100, '292': -100, '281': -100, '20185': -100, '9552': -100, '3303': -100, '2746': -100, '19849': -100, '41599': -100, '7926': -100,
            '1058': 1, '18': 1, '299': 5, '3972': 5}
            # 'As', 'as', ' an', 'AI', ' AI', ' language', ' model', 'model', 'sorry', ' sorry', ' :', '3', ' n', 'ya'
            )
        end_time = time.time()
        verbose_print(f'--OpenAI API took {end_time - start_time:.3f}s')
        result = completion.choices[0].message.content
        messageArr.append({"role": "assistant", "content": result})
        print(f"\n>ChatGPT: {result}")
        # tts(filter_for_tts(result), 'en')
        # tts(result, 'en')
        # vrc_chatbox('🛰 Getting TTS from 11.ai...')
        if opts.chatbox and len(result) > 140:
            cut_up_text(f'💬{result}')
        else:
            vrc_chatbox(f'💬{result}')
            tts(result)
    except openai.APIError as e:
        err = e
        print(f"!!Got API error from OpenAI: {e}")
    except openai.InvalidRequestError as e:
        err = e
        print(f"!!Invalid Request: {e}")
    except openai.OpenAIError as e:
        err = e
        print(f"!!Got OpenAI Error from OpenAI: {e}")
    except Exception as e:
        err = e
        print(f"!!Other Exception: {e}")
    finally:
        if err is not None: vrc_chatbox(f'⚠ {err}')
        vrc_set_parameter('CGPT_Result', True)
        vrc_set_parameter('CGPT_End', True)


def cut_up_text(text):
    """ Cuts text into segments of 144 chars that are pushed one by one to VRC Chatbox """
    global speaking
    # Check if text has whitespace or punctuation
    if re.search(r'[\s.,?!]', text):
        # Split the text into segments of up to 144 characters using the regex pattern
        segments = re.findall(
            r'.{1,143}(?<=\S)(?=[,.?!]?\s|$)|\b.{1,143}\b', text)
    else:
        # Split the text into chunks of up to 144 characters using list comprehension
        segments = [text[i:i+143] for i in range(0, len(text), 143)]
    i = 0
    list = []
    for segment in segments:
        synthesize_text(segment, f'tts_segments/segment{i}.wav')
        if i is not len(segments) - 1:
            clip_audio_end(f'tts_segments/segment{i}.wav')
        else: 
            shutil.copy(f'tts_segments/segment{i}.wav', f'tts_segments/segment{i}_trim.wav')
        list.append(segment)
        i += 1
    # and then
    i = 0
    speaking = True
    for text in list:
        vrc_chatbox(text)
        play_sound(f'./tts_segments/segment{i}_trim.wav')
        i += 1
    speaking = False


def tts(text):
    global speaking
    speaking = True
    tts_google(text)
    speaking = False


def synthesize_text(text, filename):
    # filename = filename[0:filename.rfind('.')]
    # eleven_synthesize_text(text, filename)
    gcloud_synthesize_text(text, filename)


def tts_gtrans(text, filename='tts.wav', language='en'):
    """ Returns speech from text using google API """
    filtered_text = filter_for_tts(text)
    start_time = time.time()
    tts = gTTS(filtered_text, lang=language)
    tts.save('tts.mp3')
    end_time = time.time()
    verbose_print(f'--gTTS took {end_time - start_time:.3f}s')
    to_wav('tts.mp3', 1.3)
    play_sound('tts.wav')


def tts_windows(text, filename='tts.wav'):
    """ Returns speech from text using Windows API """
    ttsEngine = pyttsx3.init()
    ttsEngine.setProperty('rate', 180)
    ttsVoices = ttsEngine.getProperty('voices')
    ttsEngine.setProperty('voice', ttsVoices[1].id)
    filtered_text = filter_for_tts(text)
    ttsEngine.save_to_file(filtered_text, 'tts.wav')
    ttsEngine.runAndWait()
    # to_wav('tts.wav', 1.1)
    play_sound('tts.wav')


def tts_google(text, filename='tts.wav'):
    """ Returns speech from text using Google Cloud API """
    start_time = time.time()
    gcloud_synthesize_text(text)
    end_time = time.time()
    verbose_print(f'--gcTTS took {end_time - start_time:.3f}s')
    play_sound('tts.wav')


def tts_eleven(text):
    """ Returns speech from text using Eleven Labs API """
    filename = 'tts'
    verbose_print('--Getting TTS from 11.ai...')
    filtered_text = filter_for_tts(text)
    voice = eleven.voices[opts.elevenVoice]
    audio = voice.generate(filtered_text)
    audio.save(filename)
    to_wav(f'{filename}.mp3')
    play_sound(f'{filename}.wav')


def eleven_synthesize_text(text, filename):
    """ Calls Eleven Labs API to synthesize speech from the input string of text and writes it to a wav file """
    # filename = filename.split('.')[0]
    verbose_print(f'--Synthesizing {text} from 11.ai...')
    filtered_text = filter_for_tts(text)
    voice = eleven.voices[opts.elevenVoice]
    audio = voice.generate(filtered_text)
    audio.save(filename)
    to_wav(f'{filename}.mp3')


def gcloud_synthesize_text(text, filename='tts.wav'):
    """ Calls Google Cloud API to synthesize speech from the input string of text and writes it to a wav file """
    global panic
    filtered_text = filter_for_tts(text)
    client = texttospeech.TextToSpeechClient()
    input_text = texttospeech.SynthesisInput(text=filtered_text)
    voice = texttospeech.VoiceSelectionParams(
        language_code=opts.gcloud_language_code,
        name=opts.gcloud_voice_name,
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        speaking_rate=1.15,
        pitch=-1.0
    )
    try:
        response = client.synthesize_speech(
            request={"input": input_text, "voice": voice,
                    "audio_config": audio_config}
        )
    except Exception as e:
        print(e)
        panic = True
        return

    with open(filename, "wb") as out:
        out.write(response.audio_content)


def to_wav(file, speed=1.0):
    """ Turns an .mp3 file into a .wav file (and optionally speeds it up) """
    name = file[0:file.rfind('.')]
    name = name + '.wav'
    try:
        start_time = time.time()
        input_stream = ffmpeg.input(file)
        audio = input_stream.audio.filter('atempo', speed)
        output_stream = audio.output(name, format='wav')
        ffmpeg.run(output_stream, cmd=[
                   "ffmpeg", "-nostdin"], capture_stdout=True, capture_stderr=True, overwrite_output=True)
        end_time = time.time()
        verbose_print(f'--ffmpeg took {end_time - start_time:.3f}s')
    except ffmpeg.Error as e:
        raise RuntimeError(f"Failed to convert audio: {e.stderr}") from e


def clip_audio_end(filename, trim=0.400):
    """ Trims the end of audio in a file """
    name = filename[0:filename.rfind('.')]
    name = name + '_trim.wav'
    try:
        start_time = time.time()
        probe = ffmpeg.probe(filename)
        duration = float(probe['format']['duration'])
        if duration < 5.0: 
            trim = 0.250
        trimmed_length = duration - trim
        input_stream = ffmpeg.input(filename, ss='0.030', t=trimmed_length)#, **audio_format_options)
        audio = input_stream.audio
        output_stream = audio.output(name, format='wav')
        output_stream.run(quiet=True, overwrite_output=True)
        end_time = time.time()
        verbose_print(f'--ffmpeg clipping took {end_time - start_time:.3f}s')
    except ffmpeg.Error as e:
        raise RuntimeError(f"Failed to convert audio: {e.stderr}") from e


def handle_command(command):
    """ Handle voice commands """
    global messageArr

    match command:
        case 'reset':
            messageArr = []
            print(f'$ Messages cleared!')
            vrc_chatbox('🗑️ Cleared message buffer')
            play_sound('./prebaked_tts/Clearedmessagebuffer.wav')

        case 'chatbox':
            opts.chatbox = not opts.chatbox
            print(f'$ Chatbox set to {opts.chatbox}')
            play_sound(
                f'./prebaked_tts/Chatboxesarenow{"on" if opts.chatbox else "off"}.wav')

        case 'sound':
            opts.soundFeedback = not opts.soundFeedback
            print(f'$ Sound feedback set to {opts.soundFeedback}')
            vrc_chatbox(('🔊' if opts.soundFeedback else '🔈') +
                        ' Sound feedback set to ' + ('on' if opts.soundFeedback else 'off'))
            play_sound(
                f'./prebaked_tts/Soundfeedbackisnow{"on" if opts.soundFeedback else "off"}.wav')

        case 'audiotrigger':
            opts.audio_trigger_enabled = not opts.audio_trigger_enabled
            print(f'$ Audio Trigger set to {opts.audio_trigger_enabled}')
            vrc_chatbox(('🔊' if opts.audio_trigger_enabled else '🔈') +
                        ' Audio Trigger set to ' + ('on' if opts.audio_trigger_enabled else 'off'))
            # play_sound(f'./prebaked_tts/Audiotriggerisnow{"on" if audio_trigger_enabled else "off"}.wav')

        case 'messagelog':
            print(f'{messageArr}')
            vrc_chatbox('📜 Dumped messages, check console')
            play_sound('./prebaked_tts/DumpedmessagesCheckconsole.wav')

        case 'verbose':
            opts.verbosity = not opts.verbosity
            print(f'$ Verbose logging set to {opts.verbosity}')
            vrc_chatbox('📜 Verbose logging set to ' +
                        ('on' if opts.verbosity else 'off'))
            play_sound(
                f'./prebaked_tts/Verboseloggingisnow{"on" if opts.verbosity else "off"}.wav')

        case 'shutdown':
            print('$ Shutting down...')
            vrc_chatbox('👋 Shutting down...')
            play_sound('./prebaked_tts/OkayGoodbye.wav')
            sys.exit(0)

        case 'gpt3':
            opts.gpt = 'GPT-3.5-Turbo'
            print(f'$ Now using {opts.gpt}')
            vrc_chatbox('Now using GPT-3.5-Turbo')
            play_sound('./prebaked_tts/NowusingGPT35Turbo.wav')

        case 'gpt4':
            opts.gpt = 'GPT-4'
            print(f'$ Now using {opts.gpt}')
            vrc_chatbox('Now using GPT-4')
            play_sound('./prebaked_tts/NowusingGPT4.wav')

        case 'parrotmode':
            opts.parrot_mode = not opts.parrot_mode
            print(f'$ Parrot mode set to {opts.parrot_mode}')
            vrc_chatbox(
                f'🦜 Parrot mode is now {"on" if opts.parrot_mode else "off"}')
            play_sound(
                f'./prebaked_tts/Parrotmodeisnow{"on" if opts.parrot_mode else "off"}.wav')

        case 'thesenutsinyourmouth':
            vrc_chatbox('💬 Do you like Imagine Dragons?')
            play_sound('./prebaked_tts/DoyoulikeImagineDragons.wav')
            time.sleep(3)
            vrc_chatbox('💬 Imagine Dragon deez nuts across your face 😈')
            play_sound('./prebaked_tts/ImagineDragondeeznutsacrossyourface.wav')

        # If an exact match is not confirmed, this last case will be used if provided
        case _:
            print(f"$Unknown command: {command}")
            play_sound('./prebaked_tts/Unknowncommand.wav')


def default_handler(address, *args):
    """ Default handler for OSC messages received from VRChat """
    print(f"{address}: {args}")


def parameter_handler(address, *args):
    """ Handle OSC messages for specific parameters received from VRChat """
    global trigger
    if address == "/avatar/parameters/ChatGPT_PB" or address == "/avatar/parameters/ChatGPT":
        if args[0]:
            trigger = True
        verbose_print(f"{address}: {args} (V:{trigger})")


def vrc_chatbox(message):
    """ Send a message to the VRC chatbox if enabled """
    if opts.chatbox:
        vrc_osc_client.send_message("/chatbox/input", [message, True, False])


def vrc_set_parameter(address, value):
    """ Sets an avatar parameter on your current VRC avatar """
    address = "/avatar/parameters/" + address
    vrc_osc_client.send_message(address, value)


def check_doublepress_key(key):
    """ Check if ctrl key is pressed twice within a certain time window """
    global key_press_window_timeup
    global trigger
    global panic
    if key == opts.key_trigger_key:
        if speaking: panic = True
        if time.time() > key_press_window_timeup:
            key_press_window_timeup = time.time() + opts.key_press_window
        else:
            if (not recording) and (not speaking):
                trigger = True


# (thread target) Initialize Faster Whisper and move its model to the GPU if possible
def load_whisper():
    global model
    with whisper_lock:
        verbose_print("~Attempt to load Whisper...")
        vrc_chatbox('🔄 Loading Voice Recognition...')
        model = None
        start_time = time.time()
        model = WhisperModel(opts.whisper_model, device='cuda', compute_type="int8") # FasterWhisper
        end_time = time.time()
        verbose_print(f'--Whisper loaded in {end_time - start_time:.3f}s')
        vrc_chatbox('✔️ Voice Recognition Loaded')


def init_audio():
    global vb_in
    global vb_out
    info = pyAudio.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    # vrc_chatbox('🔢 Enumerating Audio Devices...')
    # Get VB Aux Out for Input to Whisper, and VB Aux In for mic input
    start_time = time.time()
    for i in range(numdevices):
        info = pyAudio.get_device_info_by_host_api_device_index(0, i)
        if (info.get('maxInputChannels')) > 0:
            if info.get('name').startswith(opts.in_dev_name):
                verbose_print("~Found Input Device")
                verbose_print( info.get('name') )
                vb_out = i
        if (info.get('maxOutputChannels')) > 0: 
            if info.get('name').startswith(opts.out_dev_name):
                verbose_print("~Found Output Device")
                verbose_print( info.get('name') )
                vb_in = i
        if vb_in is not None and vb_out is not None: break
    if vb_out is None:
        print("!!Could not find input device for mic. Exiting...")
        raise RuntimeError
    if vb_in is None:
        print("!!Could not find output device for tts. Exiting...")
        raise RuntimeError

    end_time = time.time()
    verbose_print(f'--Audio initialized in {end_time - start_time:.3f}s')


def receiveCheckboxes(checkboxes):
    # global opts.verbosity
    # global opts.chatbox 
    # global opts.parrot_mode 
    # global opts.soundFeedback
    # global opts.audio_trigger_enabled
    opts.verbosity = checkboxes[0]
    opts.chatbox = checkboxes[1]
    opts.parrot_mode = checkboxes[2]
    opts.soundFeedback = checkboxes[3]
    opts.audio_trigger_enabled = checkboxes[4]


# Program Setup #################################################################################################################################

# VRC OSC init
# Client (Sending)
vrc_osc_client = udp_client.SimpleUDPClient(ip, inPort)
vrc_chatbox('▶️ Starting...')
# Server (Receiving)
dispatcher = Dispatcher()
dispatcher.map("/avatar/parameters/*", parameter_handler)
vrc_osc_server = ThreadingOSCUDPServer((ip, outPort), dispatcher)


# Audio setup
init_audio()
# Create the stream to record user voice
streamIn = pyAudio.open(format=FORMAT,
                  channels=2,
                  rate=RATE,
                  input=True,
                  input_device_index=vb_out,
                  frames_per_buffer=CHUNK_SIZE)


# Main loop - Wait for sound. If sound heard, record frames to wav file,
#     then transcribe it with Whisper, then send that to ChatGPT, then
#     take the text from ChatGPT and play it through TTS
def loop():
    # TODO: fix this global bullshit
    global full_end_time
    global frames
    global lastFrame
    global recording
    global trigger
    global silence_timeout_timer
    global panic

    global LOOP
    LOOP = True

    full_end_time = time.time()
    print(f'--Program init took {full_end_time - full_start_time:.3f}s')

    while model is None:
        time.sleep(0.1)
        pass

    print("~Waiting for sound...")
    while LOOP:
        try:
            data = streamIn.read(CHUNK_SIZE)
            # calculate root mean square of audio data
            rms = audioop.rms(data, 2)

            if opts.audio_trigger_enabled:
                if (not recording and rms > opts.THRESHOLD):
                    trigger = True

            # Start recording if sound goes above threshold or parameter is triggered
            if not recording and trigger:
                if lastFrame is not None:
                    # Add last frame to buffer, in case the next frame starts recording in the middle of a word
                    frames.append(lastFrame)
                frames.append(data)
                vrc_chatbox('👂 Listening...')
                verbose_print("~Recording...")
                recording = True
                # set timeout to now + SILENCE_TIMEOUT seconds
                silence_timeout_timer = time.time() + opts.SILENCE_TIMEOUT
                if opts.soundFeedback:
                    play_sound_threaded(speech_on)
            elif recording:  # If already recording, continue appending frames
                frames.append(data)
                if rms < opts.THRESHOLD:
                    if time.time() > silence_timeout_timer:  # if silent for longer than SILENCE_TIMEOUT, save
                        verbose_print("~Saving (silence)...")
                        recording = False
                        trigger = False
                        save_recorded_frames(frames)
                        frames = []
                        panic = False
                else:
                    # set timeout to now + SILENCE_TIMEOUT seconds
                    silence_timeout_timer = time.time() + opts.SILENCE_TIMEOUT

                # if recording for longer than MAX_RECORDING_TIME, save
                if len(frames) * CHUNK_SIZE >= opts.MAX_RECORDING_TIME * RATE:
                    verbose_print("~Saving (length)...")
                    recording = False
                    trigger = False
                    save_recorded_frames(frames)
                    frames = []
                    panic = False

            lastFrame = data
            # time.sleep(0.001)  # sleep to avoid burning cpu
        except Exception as e:
            print(f'!!Exception:\n{e}')
            vrc_chatbox(f'⚠ {e}')
            streamIn.close()
            LOOP = False
            sys.exit(e)
        except KeyboardInterrupt:
            print('Keyboard interrupt')
            vrc_chatbox(f'⚠ Quitting')
            streamIn.close()
            vrc_osc_server.shutdown()
            sys.exit("KeyboardInterrupt")


def start_server(server):  # (thread target) Starts OSC Listening server
    verbose_print(f'~Starting OSC Listener on {ip}:{outPort}')
    server.serve_forever()


def start_key_listener():  # (thread target) Starts Keyboard Listener
    with Listener(on_release=check_doublepress_key) as listener:
        listener.join()


def start_ui(): # (thread target) Starts GUI
    uistuff.initialize()

whisper_thread = threading.Thread(name='whisper-thread', target=load_whisper)
serverThread = threading.Thread(
    name='oscserver-thread', target=start_server, args=(vrc_osc_server,), daemon=True)
key_listener_thread = threading.Thread(name='keylistener-thread', target=start_key_listener, daemon=True)
uithread = threading.Thread(name="ui-thread", target=start_ui, daemon=True)
mainLoopThread = threading.Thread(name='mainloop-thread', target=loop)

whisper_thread.start()
serverThread.start()
key_listener_thread.start()
whisper_thread.join()  # Wait for Whisper to be loaded first before trying to use it
uithread.start()
mainLoopThread.start()
uithread.join()
sys.exit(0)
