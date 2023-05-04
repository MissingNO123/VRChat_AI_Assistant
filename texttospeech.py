import time
import os
import re
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
        '`': '',
        '💬': '',
        '~': '',
        '*': '',
        'missingno': 'missing no',
        'missingo123': 'missing no one two three',
        'vrchat': 'VR Chat'
    }
    for word, replacement in replacements.items():
        word_pattern = re.escape(word)
        string = re.sub(word_pattern, replacement, string, flags=re.IGNORECASE)
    return string


class WindowsTTS():
    def __init__(self):
        self.ttsEngine = pyttsx3.init()
        self.ttsEngine.setProperty('rate', 180)
        ttsVoices = self.ttsEngine.getProperty('voices')
        self.ttsEngine.setProperty('voice', ttsVoices[1].id) #eva mobile
   
    def tts(self, text):
        """ Returns speech from text using Windows API """
        audio = BytesIO()
        self.ttsEngine.save_to_file(filter(text), 'tts.wav')
        self.ttsEngine.runAndWait()
        with open('tts.wav', 'rb') as f:
            audio = BytesIO(f.read())
        audio.seek(0)
        return audio


class GoogleTranslateTTS():
    def __init__(self, lang='en'):
        self.language = lang

    def tts(self, text):
        """ Returns speech from text using google API """
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


class GoogleCloudTTS():
    def __init__(self, language_code=opts.gcloud_language_code, name=opts.gcloud_voice_name):
        self.client = texttospeech.TextToSpeechClient()
        self.voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=name
        )
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            speaking_rate=1.15,
            pitch=-1.0
        )

    def tts(self, text):
        """ Calls Google Cloud API to synthesize speech from the input string of text and writes it to a wav file """
        start_time = time.time()
        filtered_text = filter(text)
        input_text = texttospeech.SynthesisInput(text=filtered_text)
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
        end_time = time.time()
        verbose_print(f'--google cloud took {end_time - start_time:.3f}s')
        return output


class ElevenTTS(ElevenLabs):
    def __init__(self,  voice=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _voice_id = voice
        if _voice_id is None:
            _voice_id = opts.elevenVoice
        self.selected_voice = self.voices[_voice_id]
        self.voice_settings = self.selected_voice.settings

    def tts(self, text):
        """ Returns speech from text using Eleven Labs API """
        verbose_print('--Getting TTS from 11.ai...')
        if self.selected_voice is None:
            self._file = BytesIO()
            return self._file

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
        file = to_wav_bytes(file)
        file.seek(0)
        return file

    def set_voice(self, voice_id):
        self.selected_voice = self.voices[voice_id]


eleven = ElevenTTS(api_key=os.getenv(
    'ELEVENLABS_API_KEY'), voice=opts.elevenVoice)
