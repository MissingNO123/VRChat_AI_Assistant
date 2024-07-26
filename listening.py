import audioop
import os
from typing import Any
import numpy as np
import speech_recognition as sr

import time
from queue import Queue

from whisper_online import FasterWhisperASR, OnlineASRProcessor

import options as opts
import functions as funcs
import vrcutils as vrc

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

    phrase_time = -1
    phrase_complete = True

    # Load / Download model
    start_time = time.time()
    asr = FasterWhisperASR("en", opts.whisper_model)
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
                time.sleep(0.5)
                continue
            # If we're generating or speaking, we shouldn't listen for audio.
            if opts.generating or opts.speaking:
                phrase_complete = False
                phrase_time = -1
                data_queue.queue.clear()
                time.sleep(0.5)
                continue
            now = time.time()
            # Pull raw recorded audio from the queue if it's not empty.
            if not data_queue.empty():
                if not opts.trigger:
                    opts.trigger = True
                    if opts.sound_feedback:
                        funcs.play_sound_threaded(funcs.speech_on)
                    if opts.chatbox:
                        vrc.chatbox("👂 Listening...")
                    funcs.v_print("~Listening...")
                phrase_complete = False
                # If enough time has passed between recordings, consider the phrase complete.
                # Clear the current working audio buffer to start over with the new data.
                if phrase_time and phrase_time != -1 and (now - phrase_time) > opts.silence_timeout:
                    phrase_complete = True
                    opts.trigger = False
                    if opts.sound_feedback:
                        funcs.play_sound_threaded(funcs.speech_off)
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
                    result = finished_transcription(online, transcription)
                    funcs.v_print(f"\n\nFinal Transcription: \n{result}\n\n")
                    transcription = ''
            else:
                if (now - phrase_time) > opts.silence_timeout and not phrase_complete:
                    phrase_complete = True
                    opts.trigger = False
                    if opts.sound_feedback:
                        funcs.play_sound_threaded(funcs.speech_off)
                    phrase_time = -1
                    result = finished_transcription(online, transcription)
                    funcs.v_print(f"\n\nFinal Transcription: \n{result}\n\n")
                    transcription = ''
                else:
                    # Infinite loops are bad for processors, must sleep.
                    time.sleep(0.1)
        except KeyboardInterrupt:
            break


# Called when end of speech is detected
# resets and re-inits the online ASR model and queues the message to be added to the conversation
def finished_transcription(online, transcription) -> str:
    o = online.finish()
    if o[0] is not None:
        transcription += o[2]
    online.init()
    transcription = transcription.strip()
    if len(transcription) > 0:
        funcs.queue_message(transcription)
        opts.bot_responded = False
    return transcription
