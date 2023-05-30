import time
import os
import re
import requests
import json
import base64
from io import BytesIO
from google.cloud import texttospeech  # Cloud TTS
from elevenlabs import ElevenLabs
from gtts import gTTS
import pyttsx3
import ffmpeg
import options as opts
from dotenv import load_dotenv
load_dotenv()


def verbose_print(text):
    if opts.verbosity:
        print(text)


def to_wav_bytes(file, speed=1.0):
    """Converts an .mp3 BytesIO object to a .wav BytesIO object and optionally speeds it up"""
    file.seek(0)
    try:
        start_time = time.perf_counter()
        input_stream = ffmpeg.input('pipe:', format='mp3', loglevel='quiet', threads=0)
        audio = input_stream.audio.filter('atempo', speed)
        output_stream = audio.output('-', format='wav', loglevel='quiet')
        stdout, stderr = ffmpeg.run(output_stream, input=file.read(), cmd=["ffmpeg", "-nostdin"], capture_stdout=True, capture_stderr=True)
        end_time = time.perf_counter()
        verbose_print(f'--ffmpeg to_wav took {end_time - start_time:.3f}s')
        return BytesIO(stdout)
    except ffmpeg.Error as e:
        raise RuntimeError(f"Failed to convert audio: {e.stderr.decode()}") from e
 

def filter(string):
    """ Makes words in input string pronuncable by TTS """
    replacements = {
        '```': 'code.',
        '`': '',
        '💬': '',
        '🤖':'',
        '~': '',
        '*': '',
        'missingno': 'missing no',
        'missingo123': 'missing no one two three',
        'vrchat': 'VR Chat',
        'nya': 'nyaah'
    }
    for word, replacement in replacements.items():
        word_pattern = re.escape(word)
        string = re.sub(word_pattern, replacement, string, flags=re.IGNORECASE)
    return string


class WindowsTTS():
    def __init__(self):
        self.ttsEngine = pyttsx3.init()
        self.rate = 180
        self.ttsEngine.setProperty('rate', self.rate)
        self.voices = self.ttsEngine.getProperty('voices')
        self.ttsEngine.setProperty('voice', self.voices[opts.windows_tts_voice_id].id) #eva mobile
   
    def tts(self, text):
        """ Returns speech from text using Windows API """
        audio = BytesIO()
        self.ttsEngine.save_to_file(filter(text), 'tts.wav')
        self.ttsEngine.runAndWait()
        with open('tts.wav', 'rb') as f:
            audio = BytesIO(f.read())
        audio.seek(0)
        return audio
    
    def set_voice(self, index):
        if index > len(self.voices): return
        self.ttsEngine.setProperty('voice', self.voices[index].id)

    def set_rate(self, rate):
        self.rate = rate
        self.ttsEngine.setProperty('rate', self.rate)


class GoogleTranslateTTS():
    def __init__(self, lang='en'):
        self.language = lang

    def tts(self, text):
        """ Returns speech from text using Google Translate API """
        if text == '': return
        start_time = time.time()
        filtered_text = filter(text)
        output = BytesIO()
        tts = gTTS(filtered_text, lang=self.language)
        tts.write_to_fp(output)
        output.seek(0)
        output = to_wav_bytes(output)
        output.seek(0)
        end_time = time.time()
        verbose_print(f'--gTTS took {end_time - start_time:.3f}s')
        return output

    def set_language(self, lang):
        self.language = lang


class GoogleCloudTTS():
    def __init__(self, language_code=opts.gcloud_language_code, name=opts.gcloud_voice_name):
        try:
            self.client = texttospeech.TextToSpeechClient()
            self.audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                speaking_rate=1.15,
                pitch=-1.0
            )
            self.ready = True
        except Exception as e:
            print(f"Failed to load Google Cloud TTS engine: {e}")
            self.ready = False

    def tts(self, text):
        """ Calls Google Cloud API to synthesize speech from the input string of text and writes it to a wav file """
        if not self.ready:
            print("Google Cloud TTS engine is not ready!")
            return None
        start_time = time.perf_counter()
        filtered_text = filter(text)
        input_text = texttospeech.SynthesisInput(text=filtered_text)
        self.voice = texttospeech.VoiceSelectionParams(
            language_code=opts.gcloud_language_code,
            name=opts.gcloud_voice_name
        )
        try:
            response = self.client.synthesize_speech(
                request={"input": input_text, "voice": self.voice,
                         "audio_config": self.audio_config}
            )
        except Exception as e:
            print(e)
            return None

        output = BytesIO()
        output.write(response.audio_content)
        output.seek(0)
        end_time = time.perf_counter()
        verbose_print(f'--google cloud took {end_time - start_time:.3f}s')
        return output


class TikTokTTS():
    def __init__(self, voice_id = None):
        if voice_id is None:
            voice_id = "en_us_001"
        self.voice_id = voice_id
        self.rate_limit = 9999

    def tts(self, text):
        request = self._request(
            "POST",
            {
                "text": filter(text),
                "voice": self.voice_id
            }
        )
        # headers = request.headers
        # self.rate_limit = int(headers.get("x-ratelimit-remaining"))
        # if self.rate_limit <= 9998:
        #     rate_limit_reset = int(headers.get("x-ratelimit-reset")/1000)
        #     time_diff = rate_limit_reset - time.time()
        #     print(f"TikTok TTS rate limit exceeded, please try again in: {time_diff:.0} seconds") # Turns out it was actually Cloudflare's rate limit
        #     return None
        response = json.loads(request.content)

        if response['success']:
            file = BytesIO( base64.b64decode(response['data']) )
            file.seek(0)
            file = to_wav_bytes(file)
            file.seek(0)
            return file
        else:
            print(response['error'])
            return None
        
    def set_voice(self, voice_id):
        self.voice_id = voice_id

    def _request(self, method, body=None):
        url = "https://tiktok-tts.weilnet.workers.dev/api/generation"

        request = requests.request(
            method,
            url,
            json=body,
            headers={ "Content-Type": "application/json" }
        )

        if request.status_code != 200:
            print(request.content)
            raise Exception("%s" % (
                request.status_code
            ))

        return request


class ElevenTTS(ElevenLabs):
    def __init__(self, voice=None, *args, **kwargs):
        try:
            super().__init__(*args, **kwargs)
            _voice_id = voice
            if _voice_id is None:
                _voice_id = opts.eleven_voice_id
            self.selected_voice = self.voices[_voice_id]
            self.voice_settings = self.selected_voice.settings
            self.ready = True
        except Exception as e:
            print(f"Failed to load ElevenLabs engine: {e}")
            self.ready = False

    def tts(self, text):
        """ Returns speech from text using Eleven Labs API """
        if not self.ready:
            print("ElevenLabs TTS engine is not ready!")
            return None
        verbose_print('--Getting TTS from 11.ai...')
        start_time = time.perf_counter()
        if self.selected_voice is None:
            return None

        request = self._request(
            "POST",
            "text-to-speech/%s" % self.selected_voice.id,
            {
                "text": filter(text),
                "voice_settings": self.voice_settings
            }
        )

        file = BytesIO()
        file.write(request.content)
        file.seek(0)
        end_time = time.perf_counter()
        verbose_print(f'--11.ai TTS took {end_time - start_time:.3f}s')
        file = to_wav_bytes(file)
        file.seek(0)
        return file

    def set_voice(self, voice_id):
        self.selected_voice = self.voices[voice_id]


eleven = ElevenTTS(api_key=os.getenv('ELEVENLABS_API_KEY'), voice=opts.eleven_voice_id)

tiktok_voice_list = {
    "English US Female":  "en_us_001",
    "English US Male 1":  "en_us_006",
    "English US Male 2":  "en_us_007",
    "English US Male 3":  "en_us_009",
    "English US Male 4":  "en_us_010",
    "English UK Male 1":  "en_uk_001",
    "English UK Male 2":  "en_uk_003",
    "English AU Female":  "en_au_001",
    "English AU Male": "en_au_002",
    "French Male 1": "fr_001",
    "French Male 2": "fr_002",
    "German Female": "de_001",
    "German Male": "de_002",
    "Spanish Male": "es_002",
    "Spanish MX Male": "es_mx_002",
    "Portuguese BR Female 1": "br_003",
    "Portuguese BR Female 2": "br_004",
    "Portuguese BR Male": "br_005",
    "Indonesian Female": "id_001",
    "Japanese Female 1": "jp_001",
    "Japanese Female 2": "jp_003",
    "Japanese Female 3": "jp_005",
    "Japanese Male": "jp_006",
    "Korean Male 1": "kr_002",
    "Korean Male 2": "kr_004",
    "Korean Female": "kr_003",
    "Ghostface (Scream)": "en_us_ghostface",
    "Chewbacca (Star Wars)": "en_us_chewbacca",
    "C3PO (Star Wars)": "en_us_c3po",
    "Stitch (Lilo & Stitch)": "en_us_stitch",
    "Stormtrooper (Star Wars)": "en_us_stormtrooper",
    "Rocket (Guardians of the Galaxy)": "en_us_rocket",
    "Alto": "en_female_f08_salut_damour",
    "Tenor": "en_male_m03_lobby",
    "Sunshine Soon": "en_male_m03_sunshine_soon",
    "Warmy Breeze": "en_female_f08_warmy_breeze",
    "Glorious": "en_female_ht_f08_glorious",
    "It Goes Up": "en_male_sing_funny_it_goes_up",
    "Chipmunk": "en_male_m2_xhxs_m03_silly",
    "Dramatic": "en_female_ht_f08_wonderful_world",
    "Funny": "en_male_funny",
    "Emotional": "en_female_emotional",
    "Narrator": "en_male_narration"
}