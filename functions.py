import re
import wave
import pyaudio
import time
import struct
import threading
from io import BytesIO

import vrcutils as vrc
import options as opts
import texttospeech as ttsutils

vb_out = None
vb_in = None
pyAudio = None

empty_audio = BytesIO(b"\x52\x49\x46\x46\x52\x49\x00\x00\x57\x41\x56\x45\x66\x6d\x74\x20\x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00\x64\x61\x74\x61\x00\x00\x00\x00")

def v_print(text):
    if opts.verbosity:
        print(text)


def init_audio():
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
        raise RuntimeError
    if vb_in is None:
        print("!!Could not find output device for tts. Exiting...")
        raise RuntimeError

    end_time = time.perf_counter()
    v_print(f'--Audio initialized in {end_time - start_time:.5f}s')


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
            self.stream.write(data)
            data = self.wf.readframes(self.chunk)
            if opts.panic: break
        self.close()

    def close(self):
        """ Graceful shutdown """
        self.stream.close()
        self.p.terminate()


def play_sound(file):
    """ Plays a sound, waits for it to finish before continuing """
    audio = AudioFile(file)
    audio.play()


def play_sound_threaded(file):
    """ Plays a sound without blocking the main thread """
    audio = AudioFile(file)
    thread = threading.Thread(target=audio.play)
    thread.start()


def detect_silence(wf):
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


def cut_up_text(text):
    """ Cuts text into segments of 144 chars that are pushed one by one to VRC Chatbox """
    # Check if text has whitespace or punctuation
    if re.search(r'[\s.,?!]', text):
        # Split the text into segments of up to 141 characters using the regex pattern
        # 141 since emoji (2 bytes) + a space (1 byte) 
        segments = re.findall(
            r'.{1,141}(?<=\S)(?=[,.?!]?\s|$)|\b.{1,141}\b', text)
    else:
        # Split the text into chunks of up to 144 characters using list comprehension
        segments = [text[i:i+141] for i in range(0, len(text), 141)]
    i = 0
    list = []
    for i, segment in enumerate(segments):
        filtered_text = ttsutils.filter(segment)
        audio = empty_audio
        if filtered_text != '':
            audio = opts.tts_engine.tts(filtered_text)
            if ( i is not len(segments) - 1 ) and ( (not isinstance(opts.tts_engine, ttsutils.ElevenTTS)) or (not isinstance(opts.tts_engine, ttsutils.GoogleTranslateTTS))  ):
                audio = clip_audio_end(audio)
        list.append((segment, audio))

    opts.speaking = True
    for text, audio in list:
        audio.seek(0)
        if not opts.parrot_mode:
            text = '🤖 ' + text
        vrc.chatbox(f'{text}')
        play_sound(audio)
        audio.close()
    opts.speaking = False


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


def read_player_list():
    raise NotImplementedError

def read_player_count():
    raise NotImplementedError