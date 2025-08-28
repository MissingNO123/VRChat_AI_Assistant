# functions.py (c) 2023 MissingNO123
# Description: This module contains global utility functions that are reused throughout the program.

import json
import os
import re
import shutil
from typing import Callable, Optional
import wave
import pyaudio
import time
import struct
import threading
from io import BytesIO

import vrcutils as vrc
import options as opts
import texttospeech as ttsutils
import vision as eyes

vb_out = None
vb_in = None
pyAudio = None

empty_audio = BytesIO(b"\x52\x49\x46\x46\x52\x49\x00\x00\x57\x41\x56\x45\x66\x6d\x74\x20\x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00\x64\x61\x74\x61\x00\x00\x00\x00")

speech_on = "Speech On.wav"
speech_off = "Speech Sleep.wav"
speech_mis = "Speech Misrecognition.wav"

_handle_command: Optional[Callable] = None
def register_command_handler(func):
    global _handle_command
    _handle_command = func


def v_print(*args, **kwargs):
    if opts.verbosity:
        print(*args, **kwargs)

# region Message Functions

def queue_message(message):
    """ Queues a message to be spoken by the bot """
    if len(message) == 0:
        print("!!Trying to append empty message to array")
        return
    message = replace_bad_words(message, regexes["input"])
    opts.message_queue.append(message)


def append_user_message(message):
    """ Appends user message to the conversation buffer """
    if len(message) == 0:
        print("!!Trying to append empty message to array")
        return
    message = replace_bad_words(message, regexes["input"])
    opts.message_array.append({"role": "user", "content": message})


def append_bot_message(message):
    """ Appends bot message to the conversation buffer """
    if len(message) == 0:
        print("!!Trying to append empty message to array")
        return
    message = replace_bad_words(message, regexes["output"])
    opts.message_array.append({"role": "assistant", "content": message})


def append_image_message(image_as_b64: str, text: str):
    """ Appends an image message to the conversation buffer """
    opts.message_array.append(eyes.format_chatapi_img_obj(image_as_b64, text))

# endregion

# region Audio Functions

def init_audio_windows():
    global vb_in
    global vb_out
    global pyAudio
    pyAudio = pyaudio.PyAudio()
    info = pyAudio.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    # vrc_chatbox('🔢 Enumerating Audio Devices...')
    # Get VB Aux Out for Input to Whisper, and VB Aux In for mic input
    start_time = time.perf_counter()
    for i in range(numdevices):
        info = pyAudio.get_device_info_by_host_api_device_index(0, i)
        if (info.get('maxInputChannels')) > 0:
            if info.get('name').startswith(opts.in_dev_name):
                v_print("~Found Input Device")
                v_print( info.get('name') )
                vb_out = i
        if (info.get('maxOutputChannels')) > 0: 
            if info.get('name').startswith(opts.out_dev_name):
                v_print("~Found Output Device")
                v_print( info.get('name') )
                vb_in = i
        if vb_in is not None and vb_out is not None: break
    if vb_out is None:
        print("!!Could not find input device for mic. Exiting...")
        raise RuntimeError("No Input Device")
    if vb_in is None:
        print("!!Could not find output device for tts. Exiting...")
        raise RuntimeError("No Output Device")

    end_time = time.perf_counter()
    v_print(f'--Audio initialized in {end_time - start_time:.5f}s')


def init_audio_linux():
    global vb_in
    global vb_out
    global pyAudio
    pyAudio = pyaudio.PyAudio()
    host_apis = [api for api in (pyAudio.get_host_api_info_by_index(i) for i in range(pyAudio.get_host_api_count()))]
    # use JACK if available, otherwise ALSA
    host_api = next((api for api in host_apis if api['name'] == 'JACK Audio Connection Kit'), None)
    if host_api is None:
        host_api = next((api for api in host_apis if api['name'] == 'ALSA'), None)
    if host_api is None:
        print("!!Could not find JACK or ALSA host API. Exiting...")
        raise RuntimeError("No Aduio Host API")
    host_api_index = host_api['index']
    info = pyAudio.get_host_api_info_by_index(host_api_index)
    numdevices = info.get('deviceCount')
    start_time = time.perf_counter()
    for i in range(numdevices):
        info = pyAudio.get_device_info_by_host_api_device_index(host_api_index, i)
        if (info.get('maxInputChannels')) > 0:
            if opts.in_dev_name in info.get('name'):
                v_print("~Found Input Device")
                v_print( info.get('name') )
                vb_out = info.get('index')
        if (info.get('maxOutputChannels')) > 0: 
            if opts.out_dev_name in info.get('name'):
                v_print("~Found Output Device")
                v_print( info.get('name') )
                vb_in = info.get('index')
        if vb_in is not None and vb_out is not None: break
    if vb_out is None:
        print("!!Could not find input device for mic. Exiting...")
        raise RuntimeError("No Input Device")
    if vb_in is None:
        print("!!Could not find output device for tts. Exiting...")
        raise RuntimeError("No Output Device")
    end_time = time.perf_counter()
    v_print(f'--Audio initialized in {end_time - start_time:.5f}s')
    pass


def init_audio():
    if os.name == 'nt':
        init_audio_windows()
    else:
        init_audio_linux()

class AudioFile:
    chunk = 1024

    def __init__(self, file):
        """ Init audio stream """
        init_audio()
        self.wf = wave.open(file, 'rb')
        self.p = pyAudio #pyaudio.PyAudio()
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
            if opts.panic: break
            self.stream.write(data)
            data = self.wf.readframes(self.chunk)
        self.close()

    def close(self):
        """ Graceful shutdown """
        self.stream.close()
        self.p.terminate()


def play_sound(file):
    """ Plays a sound, waits for it to finish before continuing """
    audio = AudioFile(file)
    audio.play()


def play_sound_threaded(file, acquire_lock=False, set_is_speaking=False):
    """ Plays a sound without blocking the main thread, optionally acquiring the speaking lock """
    def target():
        audio = AudioFile(file)
        audio.play()
        if acquire_lock:
            opts.is_speaking_lock.release()
        if set_is_speaking:
            opts.speaking = False

    if acquire_lock:
        opts.is_speaking_lock.acquire()
    if set_is_speaking:
        opts.speaking = True
    thread = threading.Thread(target=target)
    thread.start()
 

def save_recorded_frames(frames) -> BytesIO:
    """ Saves recorded frames to a BytesIO object and returns it """
    if opts.sound_feedback:
        play_sound_threaded(speech_off)
    recording = BytesIO()
    wf = wave.open(recording, 'wb')
    wf.setnchannels(2)
    wf.setsampwidth(pyAudio.get_sample_size(opts.FORMAT))
    wf.setframerate(opts.RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    recording.seek(0)
    return recording
    ## transcription = openai_whisper_transcribe(recording) # uncomment for Slower Whisper
    # transcription = faster_whisper_transcribe(recording)
    # if transcription is not None:
    #     if ui.app.ai_stuff_frame.manual_entry_window_is_open.get() == True:
    #         ui.app.ai_stuff_frame.manual_entry_window.addtext("\n---\nUser: " + transcription)
    #     if opts.parrot_mode:
    #         text = transcription
    #     else: 
    #         funcs.append_user_message(transcription)
    #         text = chatgpt.generate(transcription)
    #     if text is None: 
    #         funcs.v_print("!!No text returned from LLM")
    #     else:
    #         if ui.app.ai_stuff_frame.manual_entry_window_is_open.get() == True:
    #             ui.app.ai_stuff_frame.manual_entry_window.refresh_messages()
    #             ui.app.ai_stuff_frame.manual_entry_window.button_send.configure(text="Send", state="normal")
    #             ui.app.ai_stuff_frame.manual_entry_window.textfield_text_entry.configure(state="normal")
    #         if opts.chatbox and len(text) > 140:
    #             funcs.cut_up_text(text)
    #         else:
    #             if opts.parrot_mode:
    #                 e_text = '💬 ' + text
    #             else:
    #                 e_text = '🤖 ' + text
    #             vrc.chatbox(f'{e_text}')
    #             if len(text): funcs.tts(e_text)
    #     vrc.set_parameter('VoiceRec_End', True)
    #     vrc.set_parameter('CGPT_Result', True)
    #     vrc.set_parameter('CGPT_End', True)
 

def detect_silence(wf) -> float:
    """ Detects the duration of silence at the end of a wave file """
    threshold = 1024
    channels = wf.getnchannels()
    frame_rate = wf.getframerate()
    n_frames = wf.getnframes()
    if n_frames == 2147483647 or n_frames == 0: 
        v_print("!!Something went bad trying to detect silence")
        return 0.0
    duration = n_frames / frame_rate

    # set the position to the end of the file
    wf.setpos(n_frames - 1)

    # read the last frame and convert it to integer values
    last_frame = wf.readframes(1)
    last_frame_values = struct.unpack("<h" * channels, last_frame)

    # check if the last frame is silent
    is_silent = all(abs(value) < threshold for value in last_frame_values)

    if is_silent:
        # if the last frame is silent, continue scanning backwards until a non-silent frame is found
        while True:
            # move the position backwards by one frame
            wf.setpos(wf.tell() - 2)

            # read the current frame and convert it to integer values
            current_frame = wf.readframes(1)
            current_frame_values = struct.unpack("<h" * channels, current_frame)

            # check if the current frame is silent
            is_silent = all(abs(value) < threshold for value in current_frame_values)

            if not is_silent:
                # if a non-silent frame is found, calculate the duration of the silence at the end
                silence_duration = duration - (wf.tell() / frame_rate)
                return silence_duration
            elif wf.tell() == 0:
                # if the beginning of the file is reached without finding a non-silent frame, assume the file is silent
                return duration
    else:
        # if the last frame is not silent, assume the file is not silent
        return 0.0


def clip_audio_end(audio_bytes: BytesIO) -> BytesIO:
    """Trims the end of audio in a BytesIO object"""
    audio_bytes.seek(0)
    with wave.open(audio_bytes, mode='rb') as wf:
        channels, sample_width, framerate, nframes = wf.getparams()[:4]
        duration = nframes / framerate
        silence_duration = detect_silence(wf)
        trimmed_length = int((duration - silence_duration + 0.050) * framerate)
        if trimmed_length <= 0:
            return BytesIO(b'RIFF\x00\x00\x00\x00WAVE')
        wf.setpos(0)
        output_bytes = BytesIO()
        with wave.open(output_bytes, mode='wb') as output_wf:
            output_wf.setnchannels(channels)
            output_wf.setsampwidth(sample_width)
            output_wf.setframerate(framerate)
            output_wf.writeframes(wf.readframes(trimmed_length))
        output_bytes.seek(0)
        return output_bytes

# endregion


# region Text Functions

def cut_up_text(text: str) -> None:
    """ Cuts text into segments of 144 chars that are pushed one by one to VRC Chatbox """
    # if isinstance(opts.tts_engine, ttsutils.AllTalkTTS):
    return cut_up_text_slow(text)
    
    txt = text
    segments = []
    while len(txt) > 142:
        punctuation_markers = ['.', ',', '!', '?', ')', ']', '}', '>', ':', ';', '"', '\n']
        last_indices = [txt[:141].rfind(sub) for sub in punctuation_markers]
        last_punc_index = max(last_indices)
        if last_punc_index == -1:
            last_punc_index = txt[:141].rfind(' ')
        if last_punc_index == -1:
            last_punc_index = 141
        chunk = txt[:last_punc_index]
        chunk = chunk.replace('\n', ' ')
        segments.append(chunk)
        txt = txt[last_punc_index+1:]
    segments.append(txt)

    i = 0
    list = []
    for i, segment in enumerate(segments):
        filtered_text = ttsutils.filter(segment)
        audio = empty_audio
        if len(filtered_text):
            audio = opts.tts_engine.tts(filtered_text)
            if ( i is not len(segments) - 1 ) and ( (not isinstance(opts.tts_engine, ttsutils.ElevenTTS)) or (not isinstance(opts.tts_engine, ttsutils.GoogleTranslateTTS))  ):
                audio = clip_audio_end(audio)
        list.append((segment, audio))

    with opts.is_speaking_lock:
        opts.speaking = True
        for text, audio in list:
            if opts.panic: break
            audio.seek(0)
            if not opts.parrot_mode:
                text = '🤖 ' + text
            vrc.chatbox(f'{text}')
            play_sound(audio)
            audio.close()
        opts.speaking = False


def cut_up_text_slow(text: str) -> None:
    """ Same method as above but alternates between pushing text to the chatbox and getting new tts generations, for engines that take longer """
    txt = text
    segments = []
    while len(txt) > 142:
        punctuation_markers = ['.', ',', '!', '?', ')', ']', '}', '>', ':', ';', '"', '\n']
        last_indices = [txt[:141].rfind(punc) for punc in punctuation_markers]
        last_punc_index = max(last_indices)
        if last_punc_index == -1:
            last_punc_index = txt[:141].rfind(' ')
        if last_punc_index == -1:
            last_punc_index = 141
        chunk = txt[:last_punc_index]
        chunk = chunk.replace('\n', ' ')
        segments.append(chunk)
        txt = txt[last_punc_index+1:]
    segments.append(txt)

    i = 0
    for i, segment in enumerate(segments):
        if opts.panic: break
        filtered_text = ttsutils.filter(segment)
        audio = empty_audio
        if len(filtered_text.strip()) > 0:
            audio = opts.tts_engine.tts(filtered_text)
            if ( i is not len(segments) - 1 ) and ( (not isinstance(opts.tts_engine, ttsutils.ElevenTTS)) or (not isinstance(opts.tts_engine, ttsutils.GoogleTranslateTTS)) ): # clip audio if not last segment, don't clip if tts engine is one that returns mp3 instead of wav
                audio = clip_audio_end(audio)
        if not opts.parrot_mode:
            segment = '🤖 ' + segment
        opts.is_speaking_lock.acquire() # acquire and immediately release lock to prevent tts from playing over itself
        opts.is_speaking_lock.release()
        audio_copy = BytesIO(audio.getvalue())
        audio.close()
        vrc.chatbox(f'{segment}')
        audio_copy.seek(0)
        play_sound_threaded(audio_copy, acquire_lock=True, set_is_speaking=True)


def inverse_title_case(text) -> str:
    """ Inverse title case for text """
    # lower case the first letter of each word, except for words whose second letter is capital
    # in order to preserve acronyms
    # return text[0].lower() + ' '.join([word[0].lower() + word[1:] for word in text[1:].split()])
    return ' '.join([
        word[0].lower() + word[1:] if len(word) > 1 and word[1].islower() else 
        (word[0].lower() if len(word) == 1 else word) # always lowercase if 1 letter otherwise passthru
        for word in text.split()
        ])


# Load regexes for filtering bad words from a JSON file
def load_badwords_from_file(file_path) -> dict:
    compiled_regexes_in = []
    compiled_regexes_out = []
    flags = re.UNICODE | re.IGNORECASE
    try:
        with open(file_path, 'r') as file:
            regexes = json.load(file)
            inputs = regexes.get("input")
            outputs = regexes.get("output")
        for regex_str in inputs:
            try:
                re.compile(regex_str, flags=flags)
                compiled_regexes_in.append(regex_str)
            except re.error:
                print(f"Error compiling regex: {regex_str}")
        for regex_str in outputs:
            try:
                re.compile(regex_str, flags=flags)
                compiled_regexes_out.append(regex_str)
            except re.error:
                print(f"Error compiling regex: {regex_str}")
        return {'input': compiled_regexes_in, 'output': compiled_regexes_out}
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return {'input': [], 'output': []}

badwords_file = os.path.join(os.path.dirname(__file__), "badwords.json")
badwords_file_example = os.path.join(os.path.dirname(__file__), "badwords.example.json")
if not os.path.exists(badwords_file):
    if os.path.exists(badwords_file_example):
        shutil.copy(badwords_file_example, 'badwords.json')
regexes = load_badwords_from_file(badwords_file)


# Replace bad words in a string with asterisks
def replace_bad_words(input_str, regexes) -> str:
    for regex in regexes:
        word = re.search(regex, input_str)
        if word:
            word = word.group()
            replacement = ''.join('*' if c != ' ' else ' ' for c in word)
            input_str = re.sub(regex, replacement, input_str)
    return input_str


def clear_between_tags(text, start_tag="<think>", end_tag="<\\/think>") -> str:
    """ Removes anything between specified tags from text. By default removes anything between <think> tags """
    return re.sub(f'({start_tag}).*?({end_tag})', '', text, flags=re.I | re.S)
    

#endregion


def faster_whisper_transcribe(model, recording) -> tuple[bool, str | None]:
    """ Transcribes audio in .wav file to text using Faster Whisper """
    if model is None:
        return (False, "Whisper model not loaded")
    if opts.whisper_task == 'transcribe':
        vrc.chatbox('✍️ Transcribing...')
        v_print('~Transcribing...')
    elif opts.whisper_task == 'translate': 
        vrc.chatbox('[あ>A] Translating...')
        v_print('~Translating...')

    with opts.whisper_lock:
        start_time = time.perf_counter()
        # audio = ffmpeg_for_whisper(recording) # This adds 500ms of latency with no apparent benefit 
        # Initialize transcription object on the recording
        segments, info = model.transcribe(
            recording, task=opts.whisper_task, beam_size=opts.whisper_beams, initial_prompt=opts.whisper_prompt, no_speech_threshold=0.3, log_prob_threshold=0.8)

        v_print(f'lang: {info.language}, {info.language_probability * 100:.1f}%')

        # if too short, skip
        if info.duration <= (opts.silence_timeout + 0.1):
            vrc.chatbox('⚠ [nothing heard]')
            if opts.sound_feedback:
                play_sound_threaded(speech_mis)
            vrc.clear_prop_params()
            return (False, "Nothing heard")

        # if not recognized as speech, dont bother processing anything  
        if info.language_probability < 0.6:
            vrc.chatbox('⚠ [unintelligible]')
            if opts.sound_feedback:
                play_sound_threaded(speech_mis)
                play_sound('./prebaked_tts/Ididntunderstandthat.wav')
            vrc.clear_prop_params()
            end_time = time.perf_counter()
            v_print(f"--Transcription failed and took: {end_time - start_time:.3f}s")
            return (False, "Speech unintelligible")

        # Transcribe and concatenate the text segments
        text = ""
        for segment in segments:
            text += segment.text
        text = text.strip()

        end_time = time.perf_counter()
    v_print(f"--Transcription took: {end_time - start_time:.3f}s")

    if text == "":
        print ("\n>User: <Nothing was recognized>")
        vrc.chatbox('⚠ [nothing heard]')
        vrc.clear_prop_params()
        return (False, "Nothing was recognized")

    # print the recognized text
    print(f"\n>User: {text}")

    # if keyword detected, send to command handler instead
    if text.lower().startswith("system"):
        _handle_command(text.lower())
        vrc.clear_prop_params()
        return (False, "Command Handled")

    
    # otherwise, return the recognized text
    else:
        vrc.set_parameter('VoiceRec_End', True)
        # return text
        return (True, inverse_title_case(text))


def tts(text):
    opts.speaking = True
    audioBytes = opts.tts_engine.tts(text)
    if audioBytes == None:
        opts.speaking = False
        opts.panic = True
        return
    play_sound(audioBytes)
    audioBytes.close()
    opts.speaking = False


