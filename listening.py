# listening.py (c) 2024 MissingNO123 ft. some guy on github 
# Description: This module contains the main loop for listening to the microphone and processing speech. It uses the SpeechRecognition library to listen to the microphone and receive audio data, which is then processed by the Whisper ASR model. The model is loaded and initialized at startup, and the audio data is passed to the model in chunks for real-time transcription. The final transcription is then passed to the chat module for processing and response generation.

# import audioop
from io import BytesIO
from typing import Any
import numpy as np
import pyaudio
import speech_recognition as sr

import time
from queue import Queue

from whisper_online import FasterWhisperASR, OnlineASRProcessor

import options as opts
import functions as funcs
import vrcutils as vrc

# region Continuous Listening
FasterWhisperASR.whisper_compute_type = opts.whisper_compute_type

# Thread safe Queue for passing data from the threaded recording callback.
data_queue = Queue()
recorder = sr.Recognizer()
recorder.energy_threshold = opts.recording_threshold
# Dynamic energy compensation lowers the energy threshold to a point where the SpeechRecognizer never stops recording, so we disable it.
recorder.dynamic_energy_threshold = False


def record_callback(_, audio:sr.AudioData) -> None:
        """
        Threaded callback function to receive audio data when recordings finish.
        audio: An AudioData containing the recorded bytes.
        """
        # Grab the raw bytes and push it into the thread safe queue.
        data = audio.get_raw_data()
        data_queue.put(data)

        # if not opts.trigger and not (opts.generating or opts.speaking) and opts.audio_trigger_enabled:
        #     opts.trigger = True
        #     if opts.sound_feedback:
        #         funcs.play_sound_threaded(funcs.speech_on)
        #     vrc.chatbox("👂 Listening...")
        #     funcs.v_print("~Listening...")


# Main function for listening to the microphone and processing speech.
def run():
    # The last time a recording was retrieved from the queue.
    phrase_time = None

    source = sr.Microphone(sample_rate=16000, device_index=int(funcs.vb_out))

    transcription = ''

    with source:
        recorder.adjust_for_ambient_noise(source)

    # Create a background thread that will pass us raw audio bytes.
    # We could do this manually but SpeechRecognizer provides a nice helper.
    recorder.listen_in_background(source, record_callback, phrase_time_limit=opts.max_recording_time)
    recorder.pause_threshold = opts.silence_timeout

    phrase_time = -1
    phrase_complete = True

    # Load / Download model
    start_time = time.time()
    asr = FasterWhisperASR("en", opts.whisper_model_size)
    online = OnlineASRProcessor(asr)
    end_time = time.time()
    funcs.v_print(f"Time taken to load model: {end_time - start_time:4.3f} seconds")

    # Cue the user that we're ready to go.
    print("Speech Recognition Model loaded.\n")
    
    while True:
        try:
            # If the audio trigger is disabled, we can't listen for audio.
            if not opts.audio_trigger_enabled:
                phrase_complete = False
                phrase_time = -1
                data_queue.queue.clear()
                time.sleep(0.1)
                continue
            # If we're generating or speaking, we shouldn't listen for audio.
            if opts.generating or opts.speaking:
                phrase_complete = False
                phrase_time = -1
                data_queue.queue.clear()
                time.sleep(0.1)
                continue
            now = time.time()
            # Pull raw recorded audio from the queue if it's not empty.
            if not data_queue.empty():
                phrase_complete = False
                # If enough time has passed between recordings, consider the phrase complete.
                # Clear the current working audio buffer to start over with the new data.
                if phrase_time and phrase_time != -1 and (now - phrase_time) > opts.silence_timeout:
                    phrase_complete = True
                    opts.trigger = False
                    # if opts.sound_feedback:
                    #     funcs.play_sound_threaded(funcs.speech_off)
                    funcs.v_print("~Phrase Complete")
                
                # Combine audio data from queue
                audio_data = b''.join(data_queue.queue)
                data_queue.queue.clear()

                # This is the last time we received new audio data from the queue.
                phrase_time = now
                
                # Convert in-ram buffer to something the model can use directly without needing a temp file.
                # Convert data from 16 bit wide integers to floating point with a width of 32 bits.
                # Clamp the audio stream frequency to a PCM wavelength compatible default of 32768hz max.
                audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

                # Process this chunk of audio
                start_time = time.time()
                online.insert_audio_chunk(audio_np)
                # o : tuple[Start, End, Transcription] 
                o : tuple[Any|None, Any|None, str] = online.process_iter()
                end_time = time.time()
                transcription_time = end_time - start_time
                # Adding this line since on slower PCs it has the chance to stop the recording early due to how long processing takes.
                if transcription_time > (opts.silence_timeout):
                    phrase_time += transcription_time
                # print(f"Partial result: {o}")
                if o[0] is not None:
                    transcription += o[2]

                if (opts.verbosity): print(f"{transcription}", end="\r")

                # If we detected a pause between recordings, add a new item to our transcription.
                # Otherwise edit the existing one.
                if phrase_complete:
                    # vrc.chatbox('✏ Processing...')
                    result = finished_transcription(online, transcription)
                    funcs.v_print(f"\n\nFinal Transcription: \n{result}\n\n")
                    transcription = ''
            else:
                if (now - phrase_time) > opts.silence_timeout and not phrase_complete:
                    phrase_complete = True
                    phrase_time = -1
                    # vrc.chatbox('✏ Processing...')
                    result = finished_transcription(online, transcription)
                    funcs.v_print(f"\n\nFinal Transcription: \n{result}\n\n")
                    transcription = ''
                else:
                    # Infinite loops are bad for processors, must sleep.
                    time.sleep(0.05)
        except KeyboardInterrupt:
            break


# Called when end of speech is detected
# resets and re-inits the online ASR model and queues the message to be added to the conversation
def finished_transcription(online, transcription) -> str:
    opts.trigger = False
    o = online.finish()
    if o[0] is not None:
        transcription += o[2]
    online.init()
    transcription = transcription.strip()
    if len(transcription) > 0:
        funcs.queue_message(transcription)
        opts.bot_responded = False
    data_queue.queue.clear()
    return transcription

# endregion


# region Sequential Listening
frames: list[bytes] = []
lastFrames: list[bytes] = []
recording = False
silence_timeout_timer = None


def loop():
    global frames
    global lastFrames
    global recording
    global silence_timeout_timer
    # Audio setup
    funcs.init_audio()
    # Create the stream to record user voice
    pyAudio = pyaudio.PyAudio()
    print( int((pyAudio.get_device_info_by_index(funcs.vb_out)['defaultSampleRate'])) )
    try:
        streamIn = pyAudio.open(format=opts.FORMAT,
                    channels=2,
                    rate=opts.RATE,
                    input=True,
                    input_device_index=funcs.vb_out,
                    frames_per_buffer=opts.CHUNK_SIZE)
    except OSError as e:
        if "Invalid sample rate" not in str(e):
            raise e
        print(f"Error: {e}. Falling back to default sample rate.")
        opts.RATE = int(pyAudio.get_device_info_by_index(funcs.vb_out)['defaultSampleRate'])
        streamIn = pyAudio.open(
            format=opts.FORMAT,
            channels=2,
            rate=opts.RATE,
            input=True,
            input_device_index=funcs.vb_out,
            frames_per_buffer=opts.CHUNK_SIZE
        )
    print("~Waiting for sound...")
    while opts.LOOP:
        try:
            data = streamIn.read(opts.CHUNK_SIZE)
            # calculate root mean square of audio chunk
            audio_data = np.frombuffer(data, dtype=np.int16)
            if np.any(audio_data):
                rms = np.sqrt(np.abs(np.mean(np.square(audio_data))))
            else:
                rms = 0

            if opts.audio_trigger_enabled:
                if (not recording and rms > opts.recording_threshold) and not opts.speaking:
                    opts.trigger = True

            # Start recording if sound goes above threshold or parameter is triggered, but not if gpt is generating
            if (not recording and opts.trigger) and not (opts.generating):
                if len(lastFrames) > 0:
                    # Add last few frames to buffer, in case the next frame starts recording in the middle of a word
                    frames.extend(lastFrames)
                frames.append(data)
                vrc.chatbox('👂 Listening...')
                funcs.v_print("~Recording...")
                recording = True
                # set timeout to now + SILENCE_TIMEOUT seconds
                silence_timeout_timer = time.time() + opts.silence_timeout
                if opts.sound_feedback:
                    funcs.play_sound_threaded(funcs.speech_on)
            elif recording:  # If already recording, continue appending frames
                frames.append(data)
                if rms < opts.recording_threshold:
                    if time.time() > silence_timeout_timer:  # if silent for longer than SILENCE_TIMEOUT, save
                        funcs.v_print("~Saving (silence)...")
                        recording = False
                        opts.trigger = False
                        phrase = funcs.save_recorded_frames(frames)
                        process_transcription_and_respond(phrase)
                        funcs.v_print("~Waiting for sound...")
                        frames = []
                        opts.panic = False
                else:
                    # set timeout to now + SILENCE_TIMEOUT seconds
                    silence_timeout_timer = time.time() + opts.silence_timeout

                # if recording for longer than MAX_RECORDING_TIME, save
                if len(frames) * opts.CHUNK_SIZE >= opts.max_recording_time * opts.RATE:
                    funcs.v_print("~Saving (length)...")
                    recording = False
                    opts.trigger = False
                    phrase = funcs.save_recorded_frames(frames)
                    process_transcription_and_respond(phrase)
                    funcs.v_print("~Waiting for sound...")
                    frames = []
                    opts.panic = False

            lastFrames.append(data)
            while len(lastFrames) > 5:
                lastFrames.pop(0)
            time.sleep(0.001)  # sleep to avoid burning cpu
        except Exception as e:
            print(f'!!Exception:\n{e}')
            vrc.chatbox(f'⚠ {e}')
            streamIn.close()
            opts.LOOP = False
        except KeyboardInterrupt:
            print('Keyboard interrupt')
            streamIn.close()
            opts.LOOP = False
    print("Exiting, Bye!")
    streamIn.close()


def process_transcription_and_respond(phrase: BytesIO):
    vrc.set_parameter(opts.vrc_thinking_parameter.get("name"), opts.vrc_thinking_parameter.get("value_on"))
    result: tuple[bool, str|None] = funcs.faster_whisper_transcribe(opts.whisper_model, phrase)
    if result is None or not result[0]:
        funcs.v_print("Nothing returned from transcription because: " + result[1])
        vrc.set_parameter(opts.vrc_thinking_parameter.get("name"), opts.vrc_thinking_parameter.get("value_off"))
        return
    with opts.is_speaking_lock:
        funcs.queue_message(result[1])
        opts.bot_responded = False

# endregion

