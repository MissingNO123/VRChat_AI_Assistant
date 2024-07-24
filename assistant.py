# Copyright (C) MissingNO123 17 Mar 2023
# Description: Main program for the VRChat Assistant

import os
from io import BytesIO
import sys
import time
full_start_time = time.perf_counter()
import audioop
from datetime import datetime
# import whisper
from faster_whisper import WhisperModel
import ffmpeg
import openai #0.28.0
import pyaudio
from pynput.keyboard import Listener
import re
import threading
import wave

from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

import options as opts
import texttospeech as ttsutils
import uistuff as ui
import chatgpt
import vrcutils as vrc
import functions as funcs
import listening

os.system('cls' if os.name=='nt' else 'clear')

# OPTIONS ####################################################################################################################################
CHUNK_SIZE = 1024           # number of frames read at a time
FORMAT = pyaudio.paInt16    # PCM format (int16)
RATE = 48000                # sample rate in Hz

# Variables ###################################################################################################################################
model = None    # Whisper model object

vb_out = None
vb_in = None

frames = []
lastFrame = None
recording = False
# speaking = False
# trigger = False
# panic = False
silence_timeout_timer = None

key_press_window_timeup = time.time()

# opts.tts_engine = ttsutils.WindowsTTS()
# opts.tts_engine = ttsutils.GoogleCloudTTS()
opts.tts_engine = ttsutils.GoogleTranslateTTS()
# opts.tts_engine = ttsutils.eleven
# opts.tts_engine = ttsutils.TikTokTTS()

# Constants
pyAudio = pyaudio.PyAudio()

speech_on = "Speech On.wav"
speech_off = "Speech Sleep.wav"
speech_mis = "Speech Misrecognition.wav"

ip = "127.0.0.1"  # IP and Ports for VRChat OSC
inPort = 9000
outPort = 9001

opts.LOOP = True

whisper_lock = threading.Lock()


# Functions ###################################################################################################################################

def v_print(text):
    if opts.verbosity:
        print(text)


def save_recorded_frames(frames):
    """ Saves recorded frames to a .wav file and sends it to whisper to transcribe it """
    if opts.soundFeedback:
        funcs.play_sound_threaded(speech_off)
    recording = BytesIO()
    wf = wave.open(recording, 'wb')
    wf.setnchannels(2)
    wf.setsampwidth(pyAudio.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    recording.seek(0)
    # return recording
    # transcription = openai_whisper_transcribe(recording) # uncomment for Slower Whisper
    transcription = faster_whisper_transcribe(recording)
    if transcription is not None:
        if ui.app.ai_stuff_frame.manual_entry_window_is_open.get() == True:
            ui.app.ai_stuff_frame.manual_entry_window.addtext("\n---\nUser: " + transcription)
        if opts.parrot_mode:
            text = transcription
        else: 
            funcs.append_user_message(transcription)
            text = chatgpt.generate(transcription)
        if text is None: 
            funcs.v_print("!!No text returned from LLM")
        else:
            if ui.app.ai_stuff_frame.manual_entry_window_is_open.get() == True:
                ui.app.ai_stuff_frame.manual_entry_window.refresh_messages()
                ui.app.ai_stuff_frame.manual_entry_window.button_send.configure(text="Send", state="normal")
                ui.app.ai_stuff_frame.manual_entry_window.textfield_text_entry.configure(state="normal")
            if opts.chatbox and len(text) > 140:
                funcs.cut_up_text(text)
            else:
                if opts.parrot_mode:
                    e_text = '💬 ' + text
                else:
                    e_text = '🤖 ' + text
                vrc.chatbox(f'{e_text}')
                if len(text): funcs.tts(e_text)
        vrc.set_parameter('VoiceRec_End', True)
        vrc.set_parameter('CGPT_Result', True)
        vrc.set_parameter('CGPT_End', True)


def ffmpeg_for_whisper(file):
    import numpy as np
    start_time = time.perf_counter()
    file.seek(0)
    try:
        out, _ = (
            ffmpeg.input('pipe:', loglevel='quiet', threads=0)
            .output("-", format="s16le", acodec="pcm_s16le", ac=1, ar=16000)
            .run(cmd=["ffmpeg", "-nostdin"], input=file.read(), capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}") from e
    data = np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0
    end_time = time.perf_counter()
    funcs.v_print(f"--FFMPEG for Whisper took: {end_time - start_time:.3f}s")
    return data


def openai_whisper_transcribe(recording):
    """ Transcribes audio in .wav file to text """
    import whisper
    
    if model is None: return
    vrc.chatbox('✍️ Transcribing...')
    funcs.v_print('~Transcribing...')
    start_time = time.perf_counter()
    
    audio = ffmpeg_for_whisper(recording)
    audio = whisper.pad_or_trim(audio)
    mel = whisper.log_mel_spectrogram(audio).to(model.device)

    # decode the audio
    options = whisper.DecodingOptions(prompt=opts.whisper_prompt, language='en')
    result = whisper.decode(model, mel, options)
    end_time = time.perf_counter()
    funcs.v_print(f"--Transcription took: {end_time - start_time:.3f}s, U: {result.no_speech_prob*100:.1f}%")

    # print the recognized text
    print(f"\n>User: {result.text}")

    # if not speech, dont send to cgpt
    if result.no_speech_prob > 0.5:
        vrc.chatbox('⚠ [unintelligible]')
        if opts.soundFeedback: funcs.play_sound_threaded(speech_mis)
        funcs.v_print(f"U: {result.no_speech_prob*100:.1f}%")
        # tts('I didn\'t understand that!', 'en')
        funcs.play_sound('./prebaked_tts/Ididntunderstandthat.wav')
        vrc.clear_prop_params()

        return None
    else:
        # otherwise, forward text to LLM
        vrc.set_parameter('VoiceRec_End', True)
        return result.text
        # chatgpt_req(result.text)


def faster_whisper_transcribe(recording):
    """ Transcribes audio in .wav file to text using Faster Whisper """
    if model is None:
        return None
    if opts.whisper_task == 'transcribe':
        vrc.chatbox('✍️ Transcribing...')
        funcs.v_print('~Transcribing...')
    elif opts.whisper_task == 'translate': 
        vrc.chatbox('[あ>A] Translating...')
        funcs.v_print('~Translating...')

    with whisper_lock:
        start_time = time.perf_counter()
        # audio = ffmpeg_for_whisper(recording) # This adds 500ms of latency with no apparent benefit 
        # Initialize transcription object on the recording
        segments, info = model.transcribe(
            recording, task=opts.whisper_task, beam_size=5, initial_prompt=opts.whisper_prompt, no_speech_threshold=0.4, log_prob_threshold=0.8)

        funcs.v_print(f'lang: {info.language}, {info.language_probability * 100:.1f}%')

        # if too short, skip
        if info.duration <= (opts.SILENCE_TIMEOUT + 0.1):
            vrc.chatbox('⚠ [nothing heard]')
            if opts.soundFeedback:
                funcs.play_sound_threaded(speech_mis)
            vrc.clear_prop_params()
            return None

        # if not recognized as speech, dont bother processing anything  
        if info.language_probability < 0.6:
            vrc.chatbox('⚠ [unintelligible]')
            if opts.soundFeedback:
                funcs.play_sound_threaded(speech_mis)
                funcs.play_sound('./prebaked_tts/Ididntunderstandthat.wav')
            vrc.clear_prop_params()
            end_time = time.perf_counter()
            funcs.v_print(f"--Transcription failed and took: {end_time - start_time:.3f}s")
            return None

        # Transcribe and concatenate the text segments
        text = ""
        for segment in segments:
            text += segment.text
        text = text.strip()

        end_time = time.perf_counter()
    funcs.v_print(f"--Transcription took: {end_time - start_time:.3f}s")

    if text == "":
        print ("\n>User: <Nothing was recognized>")
        vrc.clear_prop_params()
        return None

    # print the recognized text
    print(f"\n>User: {text}")

    # if keyword detected, send to command handler instead
    if text.lower().startswith("system"):
        handle_command(text.lower())
        vrc.clear_prop_params()
        return None
    
    # otherwise, return the recognized text
    else:
        vrc.set_parameter('VoiceRec_End', True)
        # return text
        return funcs.inverse_title_case(text)


# def chatgpt_req(text):
#     """ Sends text to OpenAI, gets the response, and puts it into the chatbox """
#     if len(opts.message_array) > opts.max_conv_length:  # Trim down chat buffer if it gets too long
#         opts.message_array.pop(0)
#     # Add user's message to the chat buffer
#     opts.message_array.append({"role": "user", "content": text})
#     # Init system prompt with date and add it persistently to top of chat buffer
#     system_prompt_object = [{"role": "system", "content":
#                            opts.system_prompt
#                            + f' The current date and time is {datetime.now().strftime("%A %B %d %Y, %I:%M:%S %p")} Eastern Standard Time.'
#                            + f' You are using {opts.gpt} from OpenAI.'}]
#     # create object with system prompt and chat history to send to OpenAI for generation
#     message_plus_system = system_prompt_object + opts.message_array
#     err = None
#     gpt_snapshot = "gpt-3.5-turbo-0613" if opts.gpt == "GPT-3" else "gpt-4-0613"
#     try:
#         vrc.chatbox('📡 Sending to OpenAI...')
#         start_time = time.perf_counter()
#         completion = openai.ChatCompletion.create(
#             model=gpt_snapshot,
#             messages=message_plus_system,
#             max_tokens=opts.max_tokens,
#             temperature=0.5,
#             frequency_penalty=0.2,
#             presence_penalty=0.5,
#             logit_bias={'1722': -100, '292': -100, '281': -100, '20185': -100, '9552': -100, '3303': -100, '2746': -100, '19849': -100, '41599': -100, '7926': -100,
#             '1058': 1, '18': 1, '299': 5, '3972': 5}
#             # 'As', 'as', ' an', 'AI', ' AI', ' language', ' model', 'model', 'sorry', ' sorry', ' :', '3', ' n', 'ya'
#             )
#         end_time = time.perf_counter()
#         funcs.v_print(f'--OpenAI API took {end_time - start_time:.3f}s')
#         result = completion.choices[0].message.content
#         opts.message_array.append({"role": "assistant", "content": result})
#         print(f"\n>AI: {result}")
#         return result
#     except openai.APIError as e:
#         err = e
#         print(f"!!Got API error from OpenAI: {e}")
#         return None
#     except openai.InvalidRequestError as e:
#         err = e
#         print(f"!!Invalid Request: {e}")
#         return None
#     except openai.OpenAIError as e:
#         err = e
#         print(f"!!Got OpenAI Error from OpenAI: {e}")
#         return None
#     except Exception as e:
#         err = e
#         print(f"!!Other Exception: {e}")
#         return None
#     finally:
#         if err is not None: vrc.chatbox(f'⚠ {err}')
#         vrc.set_parameter('CGPT_Result', True)
#         vrc.set_parameter('CGPT_End', True)
#         return None


def handle_command(command):
    """ Handle voice commands """
    command = re.sub(r'[^a-zA-Z0-9]', '', command[command.find(' ') + 1:])
    match command:
        case 'reset':
            opts.message_array = []
            opts.message_array = opts.example_messages.copy()
            print(f'$ Messages cleared!')
            vrc.chatbox('🗑️ Cleared message buffer')
            funcs.play_sound('./prebaked_tts/Clearedmessagebuffer.wav')

        case 'chatbox':
            opts.chatbox = not opts.chatbox
            ui.app.program_bools_frame.update_checkboxes()
            print(f'$ Chatbox set to {opts.chatbox}')
            funcs.play_sound(
                f'./prebaked_tts/Chatboxesarenow{"on" if opts.chatbox else "off"}.wav')

        case 'sound':
            opts.soundFeedback = not opts.soundFeedback
            ui.app.program_bools_frame.update_checkboxes()
            print(f'$ Sound feedback set to {opts.soundFeedback}')
            vrc.chatbox(('🔊' if opts.soundFeedback else '🔈') +
                        ' Sound feedback set to ' + ('on' if opts.soundFeedback else 'off'))
            funcs.play_sound(
                f'./prebaked_tts/Soundfeedbackisnow{"on" if opts.soundFeedback else "off"}.wav')

        case 'audiotrigger':
            opts.audio_trigger_enabled = not opts.audio_trigger_enabled
            ui.app.program_bools_frame.update_checkboxes()
            print(f'$ Audio Trigger set to {opts.audio_trigger_enabled}')
            vrc.chatbox(('🔊' if opts.audio_trigger_enabled else '🔈') +
                        ' Audio Trigger set to ' + ('on' if opts.audio_trigger_enabled else 'off'))
            # play_sound(f'./prebaked_tts/Audiotriggerisnow{"on" if audio_trigger_enabled else "off"}.wav')

        case 'messagelog':
            print(f'{opts.message_array}')
            vrc.chatbox('📜 Dumped messages, check console')
            funcs.play_sound('./prebaked_tts/DumpedmessagesCheckconsole.wav')

        case 'verbose':
            opts.verbosity = not opts.verbosity
            ui.app.program_bools_frame.update_checkboxes()
            print(f'$ Verbose logging set to {opts.verbosity}')
            vrc.chatbox('📜 Verbose logging set to ' +
                        ('on' if opts.verbosity else 'off'))
            funcs.play_sound(
                f'./prebaked_tts/Verboseloggingisnow{"on" if opts.verbosity else "off"}.wav')

        case 'shutdown':
            print('$ Shutting down...')
            vrc.chatbox('👋 Shutting down...')
            funcs.play_sound('./prebaked_tts/OkayGoodbye.wav')
            sys.exit(0)

        case 'gpt3':
            opts.gpt = 'GPT-3'
            ui.app.ai_stuff_frame.update_radio_buttons()
            chatgpt.update_base_url()
            print(f'$ Now using {opts.gpt}')
            vrc.chatbox('Now using GPT-3.5-Turbo')
            funcs.play_sound('./prebaked_tts/NowusingGPT35Turbo.wav')

        case 'gpt4':
            opts.gpt = 'GPT-4'
            chatgpt.update_base_url()
            ui.app.ai_stuff_frame.update_radio_buttons()
            print(f'$ Now using {opts.gpt}')
            vrc.chatbox('Now using GPT-4')
            funcs.play_sound('./prebaked_tts/NowusingGPT4.wav')
        
        case 'gptcustom':
            opts.gpt = 'custom'
            chatgpt.update_base_url()
            ui.app.ai_stuff_frame.update_radio_buttons()
            print(f'$ Now using {opts.gpt}')
            vrc.chatbox('Now using Custom GPT model')

        case 'parrotmode':
            opts.parrot_mode = not opts.parrot_mode
            ui.app.program_bools_frame.update_checkboxes()
            print(f'$ Parrot mode set to {opts.parrot_mode}')
            vrc.chatbox(
                f'🦜 Parrot mode is now {"on" if opts.parrot_mode else "off"}')
            funcs.play_sound(
                f'./prebaked_tts/Parrotmodeisnow{"on" if opts.parrot_mode else "off"}.wav')

        case 'thesenutsinyourmouth':
            vrc.chatbox('🤖 Do you like Imagine Dragons?')
            funcs.play_sound('./prebaked_tts/DoyoulikeImagineDragons.wav')
            time.sleep(3)
            vrc.chatbox('🤖 Imagine Dragon deez nuts across your face 😈')
            funcs.play_sound('./prebaked_tts/ImagineDragondeeznutsacrossyourface.wav')

        # If an exact match is not confirmed, this last case will be used if provided
        case _:
            print(f"$Unknown command: {command}")
            funcs.play_sound('./prebaked_tts/Unknowncommand.wav')


def default_handler(address, *args):
    """ Default handler for OSC messages received from VRChat """
    print(f"{address}: {args}")


def parameter_handler(address, *args):
    """ Handle OSC messages for specific parameters received from VRChat """
    if address == "/avatar/parameters/ChatGPT_PB" or address == "/avatar/parameters/ChatGPT":
        if args[0]:
            opts.trigger = True
        funcs.v_print(f"{address}: {args} (V:{opts.trigger})")


def check_doublepress_key(key):
    """ Check if ctrl key is pressed twice within a certain time window """
    global key_press_window_timeup
    if key == opts.key_trigger_key:
        if opts.speaking: opts.panic = True
        if time.time() > key_press_window_timeup:
            key_press_window_timeup = time.time() + opts.key_press_window
        else:
            if (not recording) and (not opts.speaking):
                opts.trigger = True


# (thread target) Initialize Faster Whisper and move its model to the GPU if possible
def load_whisper():
    global model
    with whisper_lock:
        funcs.v_print("~Attempt to load Whisper...")
        # vrc.chatbox('🔄 Loading Voice Recognition...')
        model = None
        start_time = time.perf_counter()
        model = WhisperModel(opts.whisper_model, device=opts.whisper_device, compute_type=opts.whisper_compute_type) # FasterWhisper
        end_time = time.perf_counter()
        funcs.v_print(f'--Whisper loaded in {end_time - start_time:.3f}s')
        # vrc.chatbox('✔️ Voice Recognition Loaded')


# Program Setup #################################################################################################################################

# VRC OSC init
# Client (Sending)
# vrc_osc_client = udp_client.SimpleUDPClient(ip, inPort)
vrc.chatbox('▶️ Starting...')
# Server (Receiving)
# dispatcher = Dispatcher()
# dispatcher.map("/avatar/parameters/*", parameter_handler)
# vrc_osc_server = ThreadingOSCUDPServer((ip, outPort), dispatcher)


# Audio setup
funcs.init_audio()
# Create the stream to record user voice
streamIn = pyAudio.open(format=FORMAT,
                  channels=2,
                  rate=RATE,
                  input=True,
                  input_device_index=funcs.vb_out,
                  frames_per_buffer=CHUNK_SIZE)


# Main loop - Wait for sound. If sound heard, record frames to wav file,
#     then transcribe it with Whisper, then send that to LLM, then
#     take the text from LLM and play it through TTS
def loop():
    # TODO: fix this global bullshit
    global full_end_time
    global frames
    global lastFrame
    global recording
    global silence_timeout_timer

    opts.LOOP = True

    full_end_time = time.perf_counter()
    print(f'--Program init took {full_end_time - full_start_time:.3f}s')

    while model is None:
        time.sleep(0.1)
        pass
    
    vrc.chatbox('✔️ Loaded')

    print("~Waiting for sound...")
    while opts.LOOP:
        try:
            data = streamIn.read(CHUNK_SIZE)
            # calculate root mean square of audio data
            rms = audioop.rms(data, 2)

            if opts.audio_trigger_enabled:
                if (not recording and rms > opts.THRESHOLD):
                    opts.trigger = True

            # Start recording if sound goes above threshold or parameter is triggered, but not if gpt is generating
            if (not recording and opts.trigger) and not opts.generating:
                if lastFrame is not None:
                    # Add last frame to buffer, in case the next frame starts recording in the middle of a word
                    frames.append(lastFrame)
                frames.append(data)
                vrc.chatbox('👂 Listening...')
                funcs.v_print("~Recording...")
                recording = True
                # set timeout to now + SILENCE_TIMEOUT seconds
                silence_timeout_timer = time.time() + opts.SILENCE_TIMEOUT
                if opts.soundFeedback:
                    funcs.play_sound_threaded(speech_on)
            elif recording:  # If already recording, continue appending frames
                frames.append(data)
                if rms < opts.THRESHOLD:
                    if time.time() > silence_timeout_timer:  # if silent for longer than SILENCE_TIMEOUT, save
                        funcs.v_print("~Saving (silence)...")
                        recording = False
                        opts.trigger = False
                        save_recorded_frames(frames)
                        funcs.v_print("~Waiting for sound...")
                        frames = []
                        opts.panic = False
                else:
                    # set timeout to now + SILENCE_TIMEOUT seconds
                    silence_timeout_timer = time.time() + opts.SILENCE_TIMEOUT

                # if recording for longer than MAX_RECORDING_TIME, save
                if len(frames) * CHUNK_SIZE >= opts.MAX_RECORDING_TIME * RATE:
                    funcs.v_print("~Saving (length)...")
                    recording = False
                    opts.trigger = False
                    save_recorded_frames(frames)
                    funcs.v_print("~Waiting for sound...")
                    frames = []
                    opts.panic = False

            lastFrame = data
            # time.sleep(0.001)  # sleep to avoid burning cpu
        except Exception as e:
            print(f'!!Exception:\n{e}')
            vrc.chatbox(f'⚠ {e}')
            streamIn.close()
            opts.LOOP = False
            sys.exit(e)
        except KeyboardInterrupt:
            print('Keyboard interrupt')
            vrc.chatbox(f'⚠ Quitting')
            streamIn.close()
            vrc.osc_server.shutdown()
            opts.LOOP = False
            sys.exit("KeyboardInterrupt")
    print("Exiting, Bye!")
    streamIn.close()
    vrc.osc_server.shutdown()

def loop2():
    opts.LOOP = True

    full_end_time = time.perf_counter()
    print(f'--Program init took {full_end_time - full_start_time:.3f}s')

    while model is None:
        time.sleep(0.1)
        pass

    vrc.chatbox('✔️ Loaded')

    while opts.LOOP:
        try:
            if not opts.bot_responded:
                opts.bot_responded = True
                while len(opts.message_queue): 
                    text = opts.message_queue.pop(0)
                    if text is not None:
                        if text.lower().startswith("system"):
                            handle_command(text.lower())
                            continue
                        else: 
                            funcs.append_user_message(text)
                if len(opts.message_array):
                    last_message = opts.message_array[-1]["content"]

                    if ui.app.ai_stuff_frame.manual_entry_window_is_open.get() == True:
                        ui.app.ai_stuff_frame.manual_entry_window.refresh_messages()

                    if opts.parrot_mode:
                        text = last_message
                    else: 
                        text = chatgpt.generate()

                    if text is None: 
                        funcs.v_print("!!No text returned from LLM")
                    else:
                        if ui.app.ai_stuff_frame.manual_entry_window_is_open.get() == True:
                            ui.app.ai_stuff_frame.manual_entry_window.refresh_messages()
                            ui.app.ai_stuff_frame.manual_entry_window.button_send.configure(text="Send", state="normal")
                            ui.app.ai_stuff_frame.manual_entry_window.textfield_text_entry.configure(state="normal")
                        if opts.chatbox and len(text) > 140:
                            funcs.cut_up_text(text)
                        else:
                            if opts.parrot_mode:
                                e_text = '💬 ' + text
                            else:
                                e_text = '🤖 ' + text
                            vrc.chatbox(f'{e_text}')
                            if len(text): funcs.tts(e_text)

                    vrc.set_parameter('VoiceRec_End', True)
                    vrc.set_parameter('CGPT_Result', True)
                    vrc.set_parameter('CGPT_End', True)
            else:
                if opts.panic: opts.panic = False
                time.sleep(0.05)
        except Exception as e:
            print(f'!!Exception:\n{e}')
            vrc.chatbox(f'⚠ {e}')
            streamIn.close()
            opts.LOOP = False
            sys.exit(e)
        except KeyboardInterrupt:
            print('Keyboard interrupt')
            vrc.chatbox(f'⚠ Quitting')
            streamIn.close()
            vrc.osc_server.shutdown()
            opts.LOOP = False
            sys.exit("KeyboardInterrupt")
    print("Exiting, Bye!")
    streamIn.close()
    vrc.osc_server.shutdown()

def start_server(server):  # (thread target) Starts OSC Listening server
    funcs.v_print(f'~Starting OSC Listener on {ip}:{outPort}')
    server.serve_forever()


def start_key_listener():  # (thread target) Starts Keyboard Listener
    with Listener(on_release=check_doublepress_key) as listener:
        listener.join()


def start_ui(): # (thread target) Starts GUI
    ui.initialize()

whisper_thread = threading.Thread(name='whisper-thread', target=load_whisper)
serverThread = threading.Thread(
    name='oscserver-thread', target=start_server, args=(vrc.osc_server,), daemon=True)
key_listener_thread = threading.Thread(name='keylistener-thread', target=start_key_listener, daemon=True)
uithread = threading.Thread(name="ui-thread", target=start_ui, daemon=True)
earsThread = threading.Thread(name='ears-thread', target=listening.run, daemon=True)
mainLoopThread = threading.Thread(name='mainloop-thread', target=loop2)


whisper_thread.start()
serverThread.start()
key_listener_thread.start()
whisper_thread.join()  # Wait for Whisper to be loaded first before trying to use it
uithread.start()
earsThread.start()
mainLoopThread.start()
uithread.join()
sys.exit(0)
