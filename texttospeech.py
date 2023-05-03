import time
import os
import re
from io import BytesIO
from google.cloud import texttospeech  # Cloud TTS
from elevenlabs import ElevenLabs
from gtts import gTTS
import options as opts
from dotenv import load_dotenv
load_dotenv()


def verbose_print(text):
    if opts.verbosity:
        print(text)


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

    def tts(self, text):
        """ Returns speech from text using Eleven Labs API """
        filename = 'eleven_tts'
        verbose_print('--Getting TTS from 11.ai...')
        filtered_text = filter(text)
        return self._generate(filtered_text)

    def set_voice(self, voice_id):
        self.selected_voice = self.voices[voice_id]

    def _generate(self, text, voice_settings=None):
        """ Generate a text-to-speech with the provided text and settings """
        if self.selected_voice is None:
            self._file = BytesIO()
            return self._file
        if not voice_settings:
            voice_settings = self.selected_voice.settings

        request = self._request(
            "POST",
            "text-to-speech/%s" % self.selected_voice.id,
            {
                "text": text,
                "voice_settings": voice_settings
            }
        )

        self._file = BytesIO()
        self._file.write(request.content)
        self._file.seek(0)
        return self._file


eleven = ElevenTTS(api_key=os.getenv(
    'ELEVENLABS_API_KEY'), voice=opts.elevenVoice)
