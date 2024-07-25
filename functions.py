import re
import wave
import pyaudio
import time
import struct
import threading
from io import BytesIO
import requests
import os
import psutil

import vrcutils as vrc
import options as opts
import texttospeech as ttsutils

vb_out = None
vb_in = None
pyAudio = None

vrc_request_timeout = time.time()
vrc_player_count = ""

empty_audio = BytesIO(b"\x52\x49\x46\x46\x52\x49\x00\x00\x57\x41\x56\x45\x66\x6d\x74\x20\x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00\x64\x61\x74\x61\x00\x00\x00\x00")

speech_on = "Speech On.wav"
speech_off = "Speech Sleep.wav"
speech_mis = "Speech Misrecognition.wav"


def v_print(text):
    if opts.verbosity:
        print(text)


def queue_message(message):
    """ Queues a message to be spoken by the bot """
    if len(message) == 0:
        print("!!Trying to append empty message to array")
        return
    opts.message_queue.append(message)


def append_user_message(message):
    """ Appends user message to the conversation buffer """
    if len(message) == 0:
        print("!!Trying to append empty message to array")
        return
    opts.message_array.append({"role": "user", "content": message})


def append_bot_message(message):
    """ Appends bot message to the conversation buffer """
    if len(message) == 0:
        print("!!Trying to append empty message to array")
        return
    opts.message_array.append({"role": "assistant", "content": message})


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
    # # Check if text has whitespace or punctuation
    # if re.search(r'[\s.,?!]', text):
    #     # Split the text into segments of up to 141 characters using the regex pattern
    #     # 141 since emoji (2 bytes) + a space (1 byte) 
    #     segments = re.findall(
    #         r'.{1,141}(?<=\S)(?=[,.?!]?\s|$)|\b.{1,141}\b', text)
    # else:
    #     # Split the text into chunks of up to 144 characters using list comprehension
    #     segments = [text[i:i+141] for i in range(0, len(text), 141)]

    txt = text
    segments = []
    while len(txt) > 142:
        substrings = [' ', '.', ',', '!', '?', ')', ']', '}', '>', ':', ';', '"', '\n']
        last_indices = [txt[:141].rfind(sub) for sub in substrings]
        last_space_index = max(last_indices)
        if last_space_index == -1:
            last_space_index = 141
        chunk = txt[:last_space_index]
        segments.append(chunk)
        txt = txt[last_space_index+1:]
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

    opts.speaking = True
    for text, audio in list:
        audio.seek(0)
        if not opts.parrot_mode:
            text = '🤖 ' + text
        vrc.chatbox(f'{text}')
        play_sound(audio)
        audio.close()
    opts.speaking = False


def inverse_title_case(text):
    """ Inverse title case for text """
    # lower case the first letter of each word
    # return text[0].lower() + ' '.join([word[0].lower() + word[1:] for word in text[1:].split()])
    return ' '.join([word[0].lower() + word[1:] for word in text.split()])


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

    
class LogWatcher:
    def __init__(self):
        self.running = False
        self.vrc_is_running = False
        self.last_line = 0
        self.last_byte = 0
        self.log_file = None
        self.log_directory = None
        self.player_count = 0
        self.player_list = []
        self.world_name = ""
        self.full_world_id = ""
        self.world_id = ""
        self.instance_id = ""
        self.instance_privacy = ""
        self.process_monitor_thread = threading.Thread(target=self._monitor_vrchat)
        self.log_watcher_thread = threading.Thread(target=self._watch_log_file)
        self.log_directory = os.path.join(os.path.expanduser("~"), 'AppData', 'LocalLow', 'VRChat', 'VRChat')

    def start(self):
        self.running = True
        self.process_monitor_thread = threading.Thread(target=self._monitor_vrchat)
        self.process_monitor_thread.start()

    def stop(self):
        self.running = False
        self.process_monitor_thread.join()

    def _check_vrchat_running(self):
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'].lower() == 'vrchat.exe':
                return True
        return False

    def _monitor_vrchat(self):
        while opts.LOOP and self.running:
            self.vrc_is_running = self._check_vrchat_running()
            if self.vrc_is_running:
                    if self.log_file is None: 
                        self.log_file = self._get_log_file(self.log_directory)
                    if not self.log_watcher_thread.is_alive():
                        self.log_watcher_thread = threading.Thread(target=self._watch_log_file)
                        self.log_watcher_thread.start()
            else:
                if self.log_watcher_thread.is_alive():
                    self.log_watcher_thread.join()
                    self.log_file = None
            time.sleep(30)

    def _watch_log_file(self):
        while self.vrc_is_running:
            time.sleep(3)
            if self.log_file:
                # new_last_line = len(open(self.log_file, encoding='utf-8').readlines())
                new_last_byte = os.path.getsize(self.log_file)
                if self.last_byte < new_last_byte:
                    with open(self.log_file, "rb") as file:
                        file.seek(self.last_byte)
                        lines = file.readlines()
                        if lines:
                            self._parse_log_lines(lines)
                    self.last_byte = new_last_byte
                # if self.last_line < new_last_line:
                #     with open(self.log_file, "r", encoding='utf-8') as file:
                #         lines = file.readlines()[self.last_line:new_last_line]
                #         if lines:
                #             self._parse_log_lines(lines)
                #     self.last_line = new_last_line

    def _get_log_file(self, directory):
        all_files = [os.path.join(directory, file) for file in os.listdir(directory)]
        files = [file for file in all_files if os.path.isfile(file)]
        if not files:
            return None
        most_recent_file = max(files, key=os.path.getmtime)
        return most_recent_file

    def _parse_log_lines(self, lines):
        for line in lines:
            if line != b"" and line != b"\r\n" and line != b"\n" :
                l = line.decode('utf-8').strip()
                self._parse_log_location(l)
                self._parse_log_on_player_joined_or_left(l)

    def _parse_log_location(self, line):
        if '[Behaviour] Entering Room: ' in line or '[RoomManager] Entering Room:' in line:
            self.player_count = 0
            self.player_list = []
            line_offset = line.rfind("] Entering Room: ")
            if (line_offset < 0):
                return
            substring_start = line_offset + 17
            if substring_start >= len(line):
                return
            self.world_name = line[substring_start:]
        if '[Behaviour] Joining wrld_' in line:
            line_offset = line.rfind("[Behaviour] Joining ")
            if (line_offset < 0):
                return
            substring_start = line_offset + 20
            if substring_start >= len(line):
                return
            self.full_world_id = line[substring_start:]

            # Regular expression pattern to match world:id
            pattern = r'wrld_([\w-]+):(\d+)'
            match_world = re.match(pattern, self.full_world_id)
            if not match_world:
                return

            self.world_id, self.instance_id = match_world.groups()

            # Regular expression pattern to match ~tag(id)
            pattern = r'~(\w+)(?:\(([\w-]+)\))?'
            tags = {}
            match_tag = re.finditer(pattern, self.full_world_id)
            for matches in match_tag:
                tag = matches.group(1)
                tag_id = matches.group(2)
                tags[tag] = tag_id if tag_id else None

            instance_privacy_map = {
                'public': 'Public',
                'hidden': 'Friends+',
                'friends': 'Friends',
                'private': 'Invite',
                'group': 'Group'
            }

            group_privacy_map = {
                'group': 'Group Members Only', 
                'plus': 'Group Plus', 
                'groupPlus': 'Group Plus', 
                'public': 'Group Public', 
            }

            for tag, value in tags.items():
                if tag in ['public', 'hidden', 'friends', 'private']:
                    self.instance_privacy = instance_privacy_map[tag]
                if tag == 'group':
                    self.instance_privacy = 'Group'
                if tag == 'groupAccessType':
                    self.instance_privacy = group_privacy_map[value]
                if opts.verbosity:
                    if value is not None:
                        print(f"Key: {tag},    Value: {value}")
                    else:
                        print(f"Key: {tag}")

    def _parse_log_on_player_joined_or_left(self, line):
        if  (
            ('[Behaviour] OnPlayerJoined' in line or '[NetworkManager] OnPlayerJoined' in line) 
             and not '] OnPlayerJoined:' in line
        ):
            self.player_count += 1
            line_offset = line.rfind('] OnPlayerJoined')
            if line_offset < 0:
                return
            substring_start = line_offset + 17
            if substring_start >= len(line):
                return
            user_display_name = line[substring_start:]
            self.player_list.append(user_display_name)
        elif (
            ('[Behaviour] OnPlayerLeft' in line or '[NetworkManager] OnPlayerLeft' in line) 
            and not 
            ('] OnPlayerLeftRoom' in line or '] OnPlayerLeft:' in line)
        ):
            self.player_count -= 1
            line_offset = line.rfind('] OnPlayerLeft')
            if line_offset < 0:
                return
            substring_start = line_offset + 15
            if substring_start >= len(line):
                return
            user_display_name = line[substring_start:]
            if user_display_name in self.player_list:
                self.player_list.remove(user_display_name)

log_parser = LogWatcher()
log_parser.start()


def get_player_list():
    if log_parser is None: 
        return None
    if log_parser.running is False: 
        return []
    return log_parser.player_list


def get_player_count():
    if log_parser is None: 
        return None
    if log_parser.running is False:
        return 0
    return log_parser.player_count


def get_vrchat_player_count():
    global vrc_request_timeout
    global vrc_player_count
    if time.time() < vrc_request_timeout:
        return vrc_player_count
    headers = {
        'User-Agent': 'VRChatAIAssistant/0.0.1 github.com/MissingNO123',
    }
    response = requests.get('https://api.vrchat.cloud/api/1/visits/', headers=headers)
    if response.status_code == 200:
        vrc_player_count = response.text
        vrc_request_timeout = time.time() + 60
        return response.text
    else:
        return None