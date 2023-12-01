import os
import sys
import threading
import time
from typing import Optional, Union, Callable
import customtkinter

import texttospeech
import options as opts
import functions as funcs
import vrcutils as vrc
import chatgpt


"""
Frame 1: Program Options ✓
    ✓ verbose logging
    ✓ chatboxes
    ✓ parrot mode
    ✓ sound feedback
    ✓ audio trigger
Frame 2: AI Stuff
    ✓ Whisper Prompt (textfield)
    - Whisper Model (dropdown)
    ✓ GPT Model (RadioButton)
    ✓ Max Tokens (spinbox)
    ✓ Max Conv Length (spinbox)
Frame 3: Bools
    ✓ key press window
    - key trigger key
Frame 4: Audio
    ✓ rms threshold (spinbox)
    ✓ silence timeout (spinbox)
    ✓ max recording time (spinbox)
    - input device name (dropdown)
    - output device name (dropdown)
Frame 5: TTS Settings
    ✓ Dynamic Frame Switcher
        ✓ Google Cloud
            - language code (dropdown)
            - voice name (dropdown)
        - Eleven Labs
            ✓ Voice Name (dropdown)
            - Voice Settings??
        - Google Translate
            - Language Code (dropdown)
        ✓ Windows Default
            ✓ Voice Name (dropdown)
            ✓ Speech Rate (spinbox)
        ✓ TikTok
            ✓ Voice Name (dropdown)
Frame 6: Direct Text Input
    - Text Box
    - Send Button
"""

app = None
icon = os.getcwd() + "\\icon.ico"

class ProgramOptionsFrame(customtkinter.CTkFrame):
    def __init__(self, master, title):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.title = title
        self.checkboxes = []
        self.checkbox_names = [
            "Verbose logging",
            "VRC Chatboxes",
            "Parrot mode",
            "Sound feedback",
            "Audio trigger"
        ]
        self.variables = [
            opts.verbosity,
            opts.chatbox,
            opts.parrot_mode,
            opts.soundFeedback,
            opts.audio_trigger_enabled
        ]

        self.title = customtkinter.CTkLabel(
            self, text=self.title, fg_color="gray30", corner_radius=6)
        self.title.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")

        self.vars = []
        for i, val in enumerate(self.variables):
            var = customtkinter.BooleanVar(value=self.variables[i])
            self.vars.append(var)

        for i, name in enumerate(self.checkbox_names):
            checkbox = customtkinter.CTkCheckBox( self, text=name, variable=self.vars[i], command=self._update_variables )
            checkbox.grid( row=i+1, column=0, padx=10, pady=(10, 0), sticky="w" )
            self.checkboxes.append(checkbox)

    def _update_variables(self):
        opts.verbosity = self.checkboxes[0].get()
        opts.chatbox = self.checkboxes[1].get()
        opts.parrot_mode = self.checkboxes[2].get()
        opts.soundFeedback = self.checkboxes[3].get()
        opts.audio_trigger_enabled = self.checkboxes[4].get()

    def update_checkboxes(self):
        # TODO: This is so ugly. Oh my god. I need to find a better way to do this.
        if self.checkboxes[0].get() is not opts.verbosity: self.checkboxes[0].toggle()
        if self.checkboxes[1].get() is not opts.chatbox: self.checkboxes[1].toggle()
        if self.checkboxes[2].get() is not opts.parrot_mode: self.checkboxes[2].toggle()
        if self.checkboxes[3].get() is not opts.soundFeedback: self.checkboxes[3].toggle()
        if self.checkboxes[4].get() is not opts.audio_trigger_enabled: self.checkboxes[3].toggle()


class AIStuffFrame(customtkinter.CTkFrame):
    def __init__(self, master, title):
        super().__init__(master)
        self.grid_columnconfigure(1, weight=1)
        self.title = title
        self.whispermodels = ["tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en", "large", "large-v2"]

        self.title = customtkinter.CTkLabel(
            self, text=self.title, fg_color="gray30", corner_radius=6)
        self.title.grid(row=0, column=0, columnspan=3, padx=10, pady=(10,0), sticky="ew")

        self.manual_entry_window_is_open = customtkinter.BooleanVar(value=False)
        
        self.whisper_prompt = customtkinter.StringVar(value=opts.whisper_prompt)
        self.selected_whisper_model = customtkinter.StringVar(value=opts.whisper_model)
        self.gpt_radio_var = customtkinter.IntVar(value=0 if opts.gpt == "GPT-3" else 1)
        self.max_tokens_var = customtkinter.IntVar(value=opts.max_tokens)
        self.max_conv_length_var = customtkinter.IntVar(value=opts.max_conv_length)
        self.sytem_prompt_var = customtkinter.StringVar(value=opts.system_prompt)

        self.label_whisper_prompt = customtkinter.CTkLabel(self, text="Whisper Prompt: ", fg_color="transparent")
        self.label_whisper_prompt.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4,1), padx=5)
        self.textfield_whisper_prompt = customtkinter.CTkEntry(self, width=200, placeholder_text="Whisper Prompt...", textvariable=self.whisper_prompt)
        self.textfield_whisper_prompt.grid(row=2, column=0, columnspan=2, sticky="ew", pady=2, padx=10)

        self.label_whisper_model = customtkinter.CTkLabel(self, text="Whisper Model: ", fg_color="transparent")
        self.label_whisper_model.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4,1), padx=5)
        self.dropdown_whisper_model = customtkinter.CTkOptionMenu(self, variable=self.selected_whisper_model, values=self.whispermodels, command=self._set_whisper_model)
        self.dropdown_whisper_model.grid(row=4, column=0, columnspan=3, sticky="ew", padx=10)

        self.label_gpt_picker = customtkinter.CTkLabel(self, text="OpenAI GPT Model: ", fg_color="transparent")
        self.label_gpt_picker.grid(row=5, column=0, sticky="w", pady=(4,1), padx=5)
        self.radiobutton_gpt_3 = customtkinter.CTkRadioButton(self, text="GPT-3", command=self._set_variables, variable=self.gpt_radio_var, value=0)
        self.radiobutton_gpt_3.grid(row=6, column=0, padx=10)
        self.radiobutton_gpt_4 = customtkinter.CTkRadioButton(self, text="GPT-4", command=self._set_variables, variable=self.gpt_radio_var, value=1)
        self.radiobutton_gpt_4.grid(row=6, column=1)

        self.label_max_tokens = customtkinter.CTkLabel(self, text="GPT Max Tokens: ", fg_color="transparent")
        self.label_max_tokens.grid(row=7, column=0, sticky="w", pady=(4,1), padx=5)
        self.spinbox_max_tokens = IntSpinbox(self, step_size=4, min=0, max=8192, value=self.max_tokens_var.get(), command=self._spinbox_callback)
        self.spinbox_max_tokens.grid(row=8, column=0, columnspan=2, sticky="ew", pady=2, padx=10)

        self.label_max_conv_length = customtkinter.CTkLabel(self, text="GPT Max Conv. Length: ", fg_color="transparent")
        self.label_max_conv_length.grid(row=9, column=0, sticky="w", pady=(4,1), padx=5)
        self.spinbox_max_conv_length = IntSpinbox(self, step_size=1, min=2, value=self.max_conv_length_var.get(), command=self._spinbox_callback)
        self.spinbox_max_conv_length.grid(row=10, column=0, columnspan=2, sticky="ew", pady=2, padx=10)

        self.label_system_prompt = customtkinter.CTkLabel(self, text="GPT System Prompt: ", fg_color="transparent")
        self.label_system_prompt.grid(row=11, column=0, sticky="w", pady=(4,1), padx=5)
        self.textbox_system_prompt = customtkinter.CTkTextbox(self, height=122, wrap="word")
        self.textbox_system_prompt.insert("0.0", opts.system_prompt)
        self.textbox_system_prompt.grid(row=12, column=0, columnspan=3, sticky="ew", padx=10, pady=(0,2))
        # self.button_system_prompt = customtkinter.CTkButton(self, text="Update System Prompt", command=self._set_variables)
        # self.button_system_prompt.grid(row=13, column=0, columnspan=3, sticky="ew", padx=10, pady=(2,10))

        self.button_reset = customtkinter.CTkButton(self, text="Clear Message History", command=self._reset_chat_buffer)
        self.button_reset.grid(row=13, column=0, columnspan=3, sticky="ew", padx=10, pady=10)

        self.button_spawn_chat_box = customtkinter.CTkButton(self, text="Open Conversation Window", command=self._spawn_manual_entry)
        self.button_spawn_chat_box.grid(row=14, column=0, columnspan=3, sticky="ew", padx=10, pady=(2,10))

        self.textbox_system_prompt.bind("<FocusOut>", self._set_variables)
        self.textbox_system_prompt.bind("<Return>", self._set_variables)

        self.textfield_whisper_prompt.bind("<FocusOut>", self._set_variables)
        self.textfield_whisper_prompt.bind("<Return>", self._set_variables)

    def update_radio_buttons(self):
        value = 0 if opts.gpt == "GPT-3" else 1
        self.gpt_radio_var.set(value)

    def _reset_chat_buffer(self):
        opts.message_array = []
        print(f'$ Messages cleared!')

    def _spinbox_callback(self):
        self.max_conv_length_var.set( int( self.spinbox_max_conv_length.get() ) ) 
        opts.max_conv_length = int( self.spinbox_max_conv_length.get() )
        self.max_tokens_var.set( int( self.spinbox_max_tokens.get() ) ) 
        opts.max_tokens = int( self.max_tokens_var.get() )

    def _set_whisper_model(self, choice):
        opts.whisper_model = choice
        self.popup = Popup(self, window_title="Restart Required",
                           window_text="Please restart the program to reload the whisper model", button_text="OK")
        self.popup.after(250, self.popup.focus) # Why do I need to wait for this???

    def _spawn_manual_entry(self):
        if self.manual_entry_window_is_open.get() == False:
            self.manual_entry_window = ManualTextEntryWindow(self, "Current Conversation")
            self.manual_entry_window.protocol("WM_DELETE_WINDOW", self._manual_entry_closed)
            self.manual_entry_window_is_open.set(True)
        self.manual_entry_window.after(250, self.manual_entry_window.focus) # Why do I need to wait for this???
    
    def _manual_entry_closed(self):
        self.manual_entry_window_is_open.set(False)
        self.manual_entry_window.destroy()

    def _set_variables(self, event=None):
        opts.system_prompt = self.textbox_system_prompt.get("0.0", "end")
        value = self.gpt_radio_var.get()
        opts.gpt = "GPT-3" if value == 0 else "GPT-4"
        opts.whisper_prompt = self.whisper_prompt.get()
        opts.max_tokens = int( self.max_tokens_var.get() )
        opts.max_conv_length = int( self.spinbox_max_conv_length.get() )


class AudioStuffFrame(customtkinter.CTkFrame):
    def __init__(self, master, title):
        super().__init__(master)
        self.title = title
        self.grid_columnconfigure(0, weight=1)
        self.textfields = []
        
        self.title = customtkinter.CTkLabel(
            self, text=self.title, fg_color="gray30", corner_radius=6)
        self.title.grid(row=0, column=0, columnspan=3, padx=10, pady=(10,0), sticky="ew")

        vcmd = (self.register(self._validate))
        
        self.rms_threshold = customtkinter.StringVar(self, value=opts.THRESHOLD)
        self.silence_timeout = customtkinter.StringVar(self, value=opts.SILENCE_TIMEOUT)
        self.max_recording_time = customtkinter.StringVar(self, value=opts.MAX_RECORDING_TIME)
        self.input_device_name = customtkinter.StringVar(self, value=opts.in_dev_name)
        self.output_device_name = customtkinter.StringVar(self, value=opts.out_dev_name)

        row_id = 1

        self.label_rms_threshold = customtkinter.CTkLabel(self, text="Audio Trigger Threshold: ", fg_color="transparent")
        self.label_rms_threshold.grid(row=row_id, column=0, sticky="w", pady=(4,1), padx=5)
        row_id += 1
        self.spinbox_rms_threshold = IntSpinbox(self, step_size=4, min=0, max=16384, value=self.rms_threshold.get(), command=self._spinbox_callback)
        self.spinbox_rms_threshold.grid(row=row_id, column=0, columnspan=2, sticky="ew", pady=2, padx=10)
        row_id += 1

        self.label_silence_timeout = customtkinter.CTkLabel(self, text="Silence Timeout: ", fg_color="transparent")
        self.label_silence_timeout.grid(row=row_id, column=0, sticky="w", pady=(4,1), padx=5)
        row_id += 1
        self.spinbox_silence_timeout = FloatSpinbox(self, step_size=0.25, min=0, max=30, value=self.silence_timeout.get(), command=self._spinbox_callback)
        self.spinbox_silence_timeout.grid(row=row_id, column=0, columnspan=2, sticky="ew", pady=2, padx=10)
        row_id += 1

        self.label_max_recording_time = customtkinter.CTkLabel(self, text="Max Listen Time: ", fg_color="transparent")
        self.label_max_recording_time.grid(row=row_id, column=0, sticky="w", pady=(4,1), padx=5)
        row_id += 1
        self.spinbox_max_recording_time = FloatSpinbox(self, step_size=0.25, min=0, max=30, value=self.max_recording_time.get(), command=self._spinbox_callback)
        self.spinbox_max_recording_time.grid(row=row_id, column=0, columnspan=2, sticky="ew", pady=2, padx=10)
        row_id += 1

        self.label_input_dev_name = customtkinter.CTkLabel(self, text="Input Device: ", fg_color="transparent")
        self.label_input_dev_name.grid(row=row_id, column=0, sticky="w", pady=(4,1), padx=5)
        row_id += 1
        self.textfield_input_dev_name = customtkinter.CTkEntry(self, width=50, placeholder_text="#", textvariable=self.input_device_name)
        self.textfield_input_dev_name.grid(row=row_id, column=0, columnspan=2, sticky="ew", pady=2, padx=10)
        self.textfields.append(self.textfield_input_dev_name)
        row_id += 1        

        self.label_output_dev_name = customtkinter.CTkLabel(self, text="Output Device: ", fg_color="transparent")
        self.label_output_dev_name.grid(row=row_id, column=0, sticky="w", pady=(4,1), padx=5)
        row_id += 1
        self.textfield_output_dev_name = customtkinter.CTkEntry(self, width=50, placeholder_text="#", textvariable=self.output_device_name)
        self.textfield_output_dev_name.grid(row=row_id, column=0, columnspan=2, sticky="ew", pady=(2,10), padx=10)
        self.textfields.append(self.textfield_output_dev_name)
        row_id += 1

        for field in self.textfields:
            field.bind("<FocusOut>", self._update_audio_page)
            field.bind("<Return>", self._update_audio_page)

    def _spinbox_callback(self):
        self.rms_threshold.set( self.spinbox_rms_threshold.get() )
        self.silence_timeout.set( self.spinbox_silence_timeout.get() )
        self.max_recording_time.set( self.spinbox_max_recording_time.get() )
        self._update_audio_page()

    def _update_audio_page(self, event=None):
        try:
            opts.THRESHOLD = int(self.rms_threshold.get())
            opts.SILENCE_TIMEOUT = float(self.silence_timeout.get())
            opts.MAX_RECORDING_TIME = float(self.max_recording_time.get())
            opts.in_dev_name = self.input_device_name.get()
            opts.out_dev_name = self.output_device_name.get()
        except ValueError as e:
            print(f"Bad value input to field: {e}")
        except Exception as e:
            print(f"Unable to update audio page: {e}")
    
    def _validate(self, P):
        if P == "":
            return True
        else:
            try:
                float(P)
                return True
            except ValueError:
                return False


class KeyboardControlFrame(customtkinter.CTkFrame):
    def __init__(self, master, title):
        super().__init__(master)
        self.title = title
        self.grid_columnconfigure(0, weight=1)
        self.textfields = []
        
        self.title = customtkinter.CTkLabel(
            self, text=self.title, fg_color="gray30", corner_radius=6)
        self.title.grid(row=0, column=0, columnspan=3, padx=10, pady=(10,0), sticky="ew")

        vcmd = (self.register(self._validate))
        
        self.key_press_window_var = customtkinter.DoubleVar(self, value=opts.key_press_window)

        row_id = 1

        self.label_key_press_window = customtkinter.CTkLabel(self, text="Double Press Window: ", fg_color="transparent")
        self.label_key_press_window.grid(row=row_id, column=0, sticky="w", pady=(4,1), padx=5)
        row_id += 1
        self.spinbox_key_press_window = FloatSpinbox(self, step_size=0.05, min=0.1, value=self.key_press_window_var.get(), command=self._spinbox_callback)
        self.spinbox_key_press_window.grid(row=row_id, column=0, sticky="ew", pady=2, padx=10)

        row_id += 1

    def _spinbox_callback(self):
        value = self.spinbox_key_press_window.get()
        if value is not None: 
            self.key_press_window_var.set( value )
        self._update_keyboard_page()

    def _update_keyboard_page(self, event=None):
        opts.key_press_window = float(self.key_press_window_var.get())

    def _validate(self, P):
        if P == "":
            return True
        else:
            try:
                float(P)
                return True
            except ValueError:
                return False


class TTSSelectorFrame(customtkinter.CTkFrame):
    def __init__(self, master, title):
        super().__init__(master)
        self.title = title
        self.width = 140
        self.columnconfigure(0, weight=1)
        self.rowconfigure((0,1), weight=0)
        self.rowconfigure(2, weight=1)

        self.title = customtkinter.CTkLabel(
            self, text=self.title, fg_color="gray30", corner_radius=6)
        self.title.grid(row=0, column=0, padx=10, pady=(10,0), sticky="ew")

        self.selected_tts_engine_name = customtkinter.StringVar(value=opts.tts_engine_name)

        self.dropdown_tts_engine_select = customtkinter.CTkOptionMenu(self, variable=self.selected_tts_engine_name, values=opts.tts_engine_selections, command=self._set_tts_engine)
        self.dropdown_tts_engine_select.grid(row=1, column=0, sticky="ew", padx=10, pady=(10,15))

        self.frame_tts_options = WindowsTTSOptionsFrame(master=self, title="Windows TTS Configuration")
        self.frame_tts_options.grid(row=2, column=0, sticky="nsew", padx=0, pady=(10,0))

    def _set_tts_engine(self, choice):
        match choice:
            case "Windows":
                opts.tts_engine = texttospeech.WindowsTTS()
                self.frame_tts_options = WindowsTTSOptionsFrame(master=self, title="Windows TTS Configuration")
                self.frame_tts_options.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
            case "Google Cloud":
                engine = texttospeech.GoogleCloudTTS()
                if not engine.ready:
                    print("Google Cloud TTS engine is not ready!")
                    popup = Popup(self, window_title="TTS engine not ready",
                                  window_text="Google Cloud's TTS engine could not start!\nMake sure your credentials are set up properly.", 
                                  button_text="OK")
                    popup.after(250, popup.focus) # Why do I need to wait for this???
                    return
                opts.tts_engine = engine
                self.frame_tts_options = GCloudOptionsFrame(master=self, title="Google Cloud TTS Configuration")
                self.frame_tts_options.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
            case "Google Translate":
                opts.tts_engine = texttospeech.GoogleTranslateTTS()
                self.frame_tts_options = GoogleTranslateOptionsFrame(master=self, title="Google Translate TTS Configuration")
                self.frame_tts_options.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
            case "ElevenLabs":
                engine = texttospeech.eleven
                if not engine.ready:
                    print("ElevenLabs TTS engine is not ready!")
                    popup = Popup(self, window_title="TTS engine not ready",
                                  window_text="ElevenLabs' TTS engine could not start!\nMake sure your credentials are set up properly.", 
                                  button_text="OK")
                    popup.after(250, popup.focus) # Why do I need to wait for this???
                    return
                opts.tts_engine = engine
                self.frame_tts_options = ElevenTTSOptionsFrame(master=self, title="ElevenLabs TTS Configuration")
                self.frame_tts_options.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
            case "TikTok":
                opts.tts_engine = texttospeech.TikTokTTS()
                self.frame_tts_options = TikTokOptionsFrame(master=self, title="TikTok TTS Configuration")
                self.frame_tts_options.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)


class PlaceholderOptionsFrame(customtkinter.CTkFrame):
    def __init__(self, master, title):
        super().__init__(master)
        self.title = title

        self.title = customtkinter.CTkLabel(
            self, text=self.title, fg_color="gray30", corner_radius=6)
        self.title.grid(row=0, column=0, columnspan=3, padx=10, pady=(10,0), sticky="ew")


class GoogleTranslateOptionsFrame(customtkinter.CTkFrame):
    def __init__(self, master, title):
        super().__init__(master, fg_color="transparent")
        self.title = title
        self.grid_columnconfigure(0, weight=1)
        self.textfields = []

        self.title = customtkinter.CTkLabel(
            self, text=self.title, fg_color="gray20", corner_radius=4)
        self.title.grid(row=0, column=0, padx=10, pady=(10,0), sticky="ew")

        if not isinstance(opts.tts_engine, texttospeech.GoogleTranslateTTS):
            self.label_error = customtkinter.CTkLabel(self, text="Google Translate is not the currently selected TTS engine.", fg_color="transparent")
            self.label_error.grid(row=1, column=0, sticky="ew", pady=(4,1), padx=5)
            return
        
        self.selected_language = customtkinter.StringVar(value=opts.gtrans_language_code)

        row_id = 1

        self.label_gtrans_tts_voice = customtkinter.CTkLabel(self, text="Language Code: ", fg_color="transparent")
        self.label_gtrans_tts_voice.grid(row=row_id, column=0, sticky="w", pady=(4,1), padx=5)
        row_id += 1

        self.textfield_selected_language = customtkinter.CTkEntry(self, width=60, placeholder_text="en", textvariable=self.selected_language)
        self.textfield_selected_language.grid(row=row_id, column=0, sticky="w", pady=(2,10), padx=10)
        self.textfields.append(self.textfield_selected_language)

        for field in self.textfields:
            field.bind("<FocusOut>", self._update_language)
            field.bind("<Return>", self._update_language)

    def _update_language(self, event=None):
        if not isinstance(opts.tts_engine, texttospeech.GoogleTranslateTTS):
            print("Google Translate is not the currently selected TTS engine")
            return
        opts.tts_engine.set_language(self.textfield_selected_language.get())



class TikTokOptionsFrame(customtkinter.CTkFrame):
    def __init__(self, master, title):
        super().__init__(master, fg_color="transparent")
        self.title = title
        self.grid_columnconfigure(0, weight=1)

        self.title = customtkinter.CTkLabel(
            self, text=self.title, fg_color="gray20", corner_radius=4)
        self.title.grid(row=0, column=0, padx=10, pady=(10,0), sticky="ew")

        self.voices = []

        if not isinstance(opts.tts_engine, texttospeech.TikTokTTS):
            self.label_error = customtkinter.CTkLabel(self, text="TikTok is not the currently selected TTS engine.", fg_color="transparent")
            self.label_error.grid(row=1, column=0, sticky="ew", pady=(4,1), padx=5)
            return
        
        self.voices = list(texttospeech.tiktok_voice_list.keys())

        self.selected_tiktok_tts_voice_name = customtkinter.StringVar(value=opts.tiktok_voice_id)
        
        row_id = 1

        self.label_tiktok_tts_voice = customtkinter.CTkLabel(self, text="Voice Name: ", fg_color="transparent")
        self.label_tiktok_tts_voice.grid(row=row_id, column=0, sticky="w", pady=(4,1), padx=5)
        row_id += 1

        self.dropdown_tiktok_tts_voice_select = customtkinter.CTkOptionMenu(self, dynamic_resizing=False, variable=self.selected_tiktok_tts_voice_name, values=self.voices, command=self._set_tts_voice)
        self.dropdown_tiktok_tts_voice_select.grid(row=row_id, column=0, sticky="ew", padx=10, pady=(0,10))
        row_id += 1

    def _set_tts_voice(self, choice):
        if not isinstance(opts.tts_engine, texttospeech.TikTokTTS):
            print("TikTok is not the currently selected TTS engine")
            return
        opts.tts_engine.set_voice(texttospeech.tiktok_voice_list[choice])
        print(f'Set TikTok voice to {choice} ({opts.tts_engine.voice_id})')


class ElevenTTSOptionsFrame(customtkinter.CTkFrame):
    def __init__(self, master, title):
        super().__init__(master, fg_color="transparent")
        self.title = title
        self.grid_columnconfigure(0, weight=1)

        self.title = customtkinter.CTkLabel(
            self, text=self.title, fg_color="gray20", corner_radius=4)
        self.title.grid(row=0, column=0, columnspan=3, padx=10, pady=(10,0), sticky="ew")

        self.voices = []

        if not isinstance(opts.tts_engine, texttospeech.ElevenTTS):
            self.label_error = customtkinter.CTkLabel(self, text="ElevenLabs is not the currently selected TTS engine.", fg_color="transparent")
            self.label_error.grid(row=1, column=0, sticky="ew", pady=(4,1), padx=5)
            return

        for voice in opts.tts_engine.voices:
            self.voices.append(voice.name)

        self.selected_eleven_tts_voice_name = customtkinter.StringVar(value=opts.eleven_voice_id)
        
        row_id = 1

        self.label_eleven_tts_voice = customtkinter.CTkLabel(self, text="Voice Name: ", fg_color="transparent")
        self.label_eleven_tts_voice.grid(row=row_id, column=0, sticky="w", pady=(4,1), padx=5)
        row_id += 1

        self.dropdown_eleven_tts_voice_select = customtkinter.CTkOptionMenu(self, dynamic_resizing=False, variable=self.selected_eleven_tts_voice_name, values=self.voices, command=self._set_tts_voice)
        self.dropdown_eleven_tts_voice_select.grid(row=row_id, column=0, sticky="ew", padx=10, pady=(0,10))
        row_id += 1

        # self.label_speaking_rate = customtkinter.CTkLabel(self, text="Speaking Rate: ", fg_color="transparent")
        # self.label_speaking_rate.grid(row=row_id, column=0, sticky="w", pady=(4,1), padx=5)
        # row_id += 1

        # self.spinbox_speaking_rate = IntSpinbox(self, step_size=1, min=1, max=500, value=self.speaking_rate.get(), command=self._spinbox_callback)
        # self.spinbox_speaking_rate.grid(row=row_id, column=0, columnspan=2, sticky="ew", pady=2, padx=10)
        # row_id += 1

    def _set_tts_voice(self, choice):
        if not isinstance(opts.tts_engine, texttospeech.ElevenTTS):
            print("ElevenLabs is not the currently selected TTS engine")
            return
        opts.tts_engine.set_voice(choice)


class WindowsTTSOptionsFrame(customtkinter.CTkFrame):
    def __init__(self, master, title):
        super().__init__(master, fg_color="transparent")
        self.title = title
        self.grid_columnconfigure(0, weight=1)

        self.title = customtkinter.CTkLabel(
            self, text=self.title, fg_color="gray20", corner_radius=4)
        self.title.grid(row=0, column=0, columnspan=3, padx=10, pady=(10,0), sticky="ew")

        self.voices = []

        if not isinstance(opts.tts_engine, texttospeech.WindowsTTS):
            self.label_error = customtkinter.CTkLabel(self, text="Windows is not the currently selected TTS engine.", fg_color="transparent")
            self.label_error.grid(row=1, column=0, sticky="ew", pady=(4,1), padx=5)
            return

        for voice in opts.tts_engine.voices: 
            self.voices.append(voice.name)

        self.selected_wtts_voice_name = customtkinter.StringVar(value=self.voices[opts.windows_tts_voice_id])
        self.speaking_rate = customtkinter.IntVar(value=opts.tts_engine.rate)

        row_id = 1

        self.label_wtts_voice = customtkinter.CTkLabel(self, text="Voice Name: ", fg_color="transparent")
        self.label_wtts_voice.grid(row=row_id, column=0, sticky="w", pady=(4,1), padx=5)
        row_id += 1

        self.dropdown_tts_voice_select = customtkinter.CTkOptionMenu(self, dynamic_resizing=False, variable=self.selected_wtts_voice_name, values=self.voices, command=self._set_tts_engine)
        self.dropdown_tts_voice_select.grid(row=row_id, column=0, sticky="ew", padx=10, pady=(0,10))
        row_id += 1

        self.label_speaking_rate = customtkinter.CTkLabel(self, text="Speaking Rate: ", fg_color="transparent")
        self.label_speaking_rate.grid(row=row_id, column=0, sticky="w", pady=(4,1), padx=5)
        row_id += 1

        self.spinbox_speaking_rate = IntSpinbox(self, step_size=1, min=1, max=500, value=self.speaking_rate.get(), command=self._spinbox_callback)
        self.spinbox_speaking_rate.grid(row=row_id, column=0, columnspan=2, sticky="ew", pady=2, padx=10)
        row_id += 1
    
    def _set_tts_engine(self, choice):
        if not isinstance(opts.tts_engine, texttospeech.WindowsTTS):
            print("Windows is not the currently selected TTS engine")
            return
        try:
            index = self.voices.index(choice)
            opts.windows_tts_voice_id = index
            opts.tts_engine.set_voice(index)
            print(f"Set TTS Engine to {self.voices[index]}")
        except ValueError:
            print("Invalid selection: " + choice)

    def _spinbox_callback(self):
        if not isinstance(opts.tts_engine, texttospeech.WindowsTTS):
            print("Windows is not the currently selected TTS engine")
            return
        opts.tts_engine.set_rate(self.spinbox_speaking_rate.get())
        # verbose_print(f"Set WTTS speaking rate to {opts.tts_engine.rate}")


class GCloudOptionsFrame(customtkinter.CTkFrame):
    def __init__(self, master, title):
        super().__init__(master, fg_color="transparent")
        self.title = title
        self.grid_columnconfigure(0, weight=1)

        self.textfields = []
        self.language_codes = {}
        self.voices = {}

        if not isinstance(opts.tts_engine, texttospeech.GoogleCloudTTS):
            self.label_error = customtkinter.CTkLabel(self, text="Google Cloud is not the currently selected TTS engine.", fg_color="transparent")
            self.label_error.grid(row=1, column=0, sticky="ew", pady=(4,1), padx=5)
            return

        #self.pitch = customtkinter.IntVar(value=opts.tts_engine.rate)
        self.pitch = customtkinter.StringVar(self, value=str(opts.tts_engine.audio_config.pitch))
        self.speaking_rate = customtkinter.StringVar(self, value=str(opts.tts_engine.audio_config.speaking_rate))
        
        self.title = customtkinter.CTkLabel(
            self, text=self.title, fg_color="gray20", corner_radius=4)
        self.title.grid(row=0, column=0, columnspan=3, padx=10, pady=(5,0), sticky="ew")
        
        self.gcloud_language_code_var = customtkinter.StringVar(self, value=opts.gcloud_language_code)
        self.gcloud_voice_name_var = customtkinter.StringVar(self, value=f"{opts.gcloud_tts_type}-{opts.gcloud_letter_id}")

        row_id = 1

        self.label_gcloud_language_code = customtkinter.CTkLabel(self, text="TTS Language Code / Voice Name: ", fg_color="transparent")
        self.label_gcloud_language_code.grid(row=row_id, column=0, columnspan=2, sticky="w", pady=(2,1), padx=5)
        row_id += 1
        self.textfield_gcloud_language_code = customtkinter.CTkEntry(self, width=60, placeholder_text="#", textvariable=self.gcloud_language_code_var)
        self.textfield_gcloud_language_code.grid(row=row_id, column=0, columnspan=1, sticky="ew", pady=2, padx=(5,0))
        self.textfields.append(self.textfield_gcloud_language_code)
        # row_id += 1

        # self.label_gcloud_voice = customtkinter.CTkLabel(self, text="TTS Voice Name: ", fg_color="transparent")
        # self.label_gcloud_voice.grid(row=row_id, column=0, sticky="w", pady=(2,1), padx=5)
        # row_id += 1
        self.textfield_gcloud_voice = customtkinter.CTkEntry(self, placeholder_text="#", textvariable=self.gcloud_voice_name_var)
        self.textfield_gcloud_voice.grid(row=row_id, column=1, columnspan=1, sticky="ew", pady=2, padx=(0,5))
        self.textfields.append(self.textfield_gcloud_voice)
        row_id += 1

        self.label_speaking_rate = customtkinter.CTkLabel(self, text="Speaking Rate: ", fg_color="transparent")
        self.label_speaking_rate.grid(row=row_id, column=0, sticky="w", pady=(2,1), padx=5)
        row_id += 1
        self.spinbox_speaking_rate = FloatSpinbox(self, step_size=0.125, min=0.25, max=4.0, value=self.speaking_rate.get(), command=self._update_gcloud)
        self.spinbox_speaking_rate.grid(row=row_id, column=0, columnspan=2, sticky="ew", pady=0, padx=10)
        row_id += 1

        self.label_pitch = customtkinter.CTkLabel(self, text="Pitch: ", fg_color="transparent")
        self.label_pitch.grid(row=row_id, column=0, sticky="w", pady=(2,1), padx=5)
        row_id += 1
        self.spinbox_pitch = FloatSpinbox(self, step_size=0.5, min=-20, max=20, value=self.pitch.get(), command=self._update_gcloud)
        self.spinbox_pitch.grid(row=row_id, column=0, columnspan=2, sticky="ew", pady=0, padx=10)
        row_id += 1

        for field in self.textfields:
            field.bind("<FocusOut>", self._update_gcloud)
            field.bind("<Return>", self._update_gcloud)

    def _update_gcloud(self, event=None):
        opts.gcloud_language_code = self.gcloud_language_code_var.get()
        opts.gcloud_voice_name = f'{self.gcloud_language_code_var.get()}-{self.gcloud_voice_name_var.get()}'
        if not isinstance(opts.tts_engine, texttospeech.GoogleCloudTTS):
            print("Google Cloud is not the currently selected TTS engine")
            return
        newPitch = self.spinbox_pitch.get()
        newSpeakingRate = self.spinbox_speaking_rate.get()
        if newPitch is not None: 
            opts.tts_engine.update_pitch(newPitch)
        if newSpeakingRate is not None: 
            opts.tts_engine.update_speaking_rate(newSpeakingRate)


class ManualTextEntryWindow(customtkinter.CTkToplevel):
    def __init__(self, master, title):
        super().__init__(master)
        app.update_idletasks()
        screenw = app.winfo_screenwidth()
        w = 600
        h = 630
        x = app.winfo_x()+app.winfo_width()
        y = app.winfo_y()
        if x+w >= screenw: x = screenw - w
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((0,2), weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.iconbitmap(icon)
        self.title = title

        opts.generating = False
        self.result = None

        self.title = customtkinter.CTkLabel(
            self, text=self.title, fg_color="gray30", corner_radius=6)
        self.title.grid(row=0, column=1, columnspan=2, padx=10, pady=(10,0), sticky="ew")

        # Frame Variables
        self.text_entry = customtkinter.StringVar(value="")
        # self.chat_history = customtkinter.StringVar(value="")

        self.button_reset = customtkinter.CTkButton(self, text="Clear", width=80, command=self._reset_chat_buffer)
        self.button_reset.grid(row=0, column=0, sticky="w", padx=(10,0), pady=(10,0))

        row_id = 1

        self.textbox_temp_chat_history = customtkinter.CTkTextbox(self, height=300, wrap="word")
        self.refresh_messages()
        self.textbox_temp_chat_history.grid(row=row_id, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)
        row_id += 1

        self.textfield_text_entry = customtkinter.CTkEntry(self, width=200, placeholder_text="Enter Message...", textvariable=self.text_entry)
        self.textfield_text_entry.grid(row=row_id, column=0, columnspan=2, sticky="ew", padx=10, pady=2)

        self.button_send = customtkinter.CTkButton(self, text="Send", command=self._start_send)
        self.button_send.grid(row=row_id, column=2, sticky="e", padx=(2,10), pady=10)

        self.textfield_text_entry.bind("<Return>", self._start_send)

    def refresh_messages(self):
        # message_history_str = "\n---\n".join(
        #     f'{"User" if message["role"] == "user" else "ChatGPT"}: {message["content"]}' 
        #     for message in opts.message_array
        #     )
        str_array = []
        for message in opts.message_array:
            if message["role"] == "user" or message["role"] == "assistant":
                if len(message["content"]) > 0:
                    str_array.append( f'{"User" if message["role"] == "user" else "ChatGPT"}: {message["content"]}' )
            elif message["role"] == "function":
                str_array.append( "[ChatGPT ran a function]" )
        message_history_str = "\n---\n".join(str_array)
        self.textbox_temp_chat_history.delete("0.0", "end")
        self.addtext(message_history_str)

    def addtext(self, text):
        self.textbox_temp_chat_history.insert("end", text)
        self.textbox_temp_chat_history.see("end")

    def _reset_chat_buffer(self):
        self.textbox_temp_chat_history.delete("0.0", "end")
        self.addtext("Messages cleared!\n")
        opts.message_array = []
        print(f'$ Messages cleared!')


    def _start_send(self, event=None):
        if opts.generating: return
        user_text = self.text_entry.get().strip()
        if len(user_text) > 0:
            self.button_send.configure(text="Wait...", state="disabled")
            self.textfield_text_entry.configure(state="disabled")
            print(f'\nUser: {user_text}')
            self.text_entry.set("")
            self.addtext("\n---\nUser: " + user_text)
            # generate_thread = threading.Thread(target=self._generate, args=(user_text=user_text,))
            if opts.parrot_mode:
                self.result = user_text
                self._end_send()
            else:
                generate_thread = threading.Thread(target=self._generate, args=(user_text,))
                generate_thread.start()

    def _generate(self, user_text, *args, **kwargs):
        opts.generating = True
        self.result = None
        start_time = time.perf_counter()
        try:
            completion = chatgpt.generate(user_text, True)
            completion_text = ''
            is_function_call = False
            function_args = {}
            print("\n>ChatGPT: ", end='')
            self.addtext("\n---\nChatGPT: ")
            for chunk in completion:
                event_text = ''
                chunk_message = chunk['choices'][0]['delta']  # extract the message
                if chunk_message.get('content'):
                    event_text = chunk_message['content']
                print(event_text, end='')
                sys.stdout.flush()
                self.addtext(event_text)
                completion_text += event_text  # append the text
                if chunk['choices'][0]['delta'].get('function_call'):
                    is_function_call = True
                    function_args = chunk['choices'][0]['delta']["function_call"]
                    break
            end_time = time.perf_counter()
            if is_function_call:
                funcs.v_print(f'--OpenAI Function call took {end_time - start_time:.3f}s')
                print("[Running Function...]")
                self.addtext("[Running Function...]\n")
                self.result = chatgpt.call_function(function_args)
                self.addtext(self.result)
            else: 
                self.result = completion_text
                if len(self.result):
                    opts.message_array.append({"role": "assistant", "content": self.result})
            funcs.v_print(f'--OpenAI API took {end_time - start_time:.3f}s')
            print()
        except Exception:
            print('Failed to generate from ChatGPT')
        finally:
            opts.generating = False
            self._end_send()

    def _end_send(self):
        if self.result is None or len(self.result) == 0: 
            funcs.v_print("!!No text to speak")
        else:
            if opts.chatbox and len(self.result) > 140:
                funcs.cut_up_text(self.result)
            else:
                text = '🤖 ' + self.result if (not opts.parrot_mode) else '💬 ' + self.result
                vrc.chatbox(f'{text}')
                if len(self.result): funcs.tts(self.result)
        self.textfield_text_entry.configure(state="normal")
        self.button_send.configure(text="Send", state="normal")
        self.refresh_messages()


class Popup(customtkinter.CTkToplevel):
    def __init__(self, master, window_title, window_text, button_text, *args, **kwargs):
        super().__init__(master)
        self.geometry("300x150")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure((0,2), weight=0)
        self.title(window_title)
        self.iconbitmap(icon)

        self.titlebar = customtkinter.CTkLabel( self, text=window_title, fg_color="gray30", corner_radius=6 )
        self.titlebar.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

        self.label = customtkinter.CTkLabel(self, text=window_text, fg_color="gray10", corner_radius=6, wraplength=260)
        self.label.grid(row=1, column=0, sticky='nsew', padx=20, pady=5)

        self.button = customtkinter.CTkButton(self, text=button_text, command=self.destroy)
        self.button.grid(row=2, column=0, sticky="s", padx=10, pady=(2,10))


class IntSpinbox(customtkinter.CTkFrame):
    def __init__(self, *args,
                 width: int = 100,
                 height: int = 32,
                 step_size: int = 1,
                 command: Callable = None,
                 value: int,
                 min: Optional [int] = None,
                 max: Optional [int] = None,
                 **kwargs):
        super().__init__(*args, width=width, height=height, **kwargs)

        self.step_size = step_size
        self.command = command

        self.min = min
        self.max = max

        self.configure(fg_color=("gray78", "gray28"))  # set frame color

        self.grid_columnconfigure((0, 2), weight=0)  # buttons don't expand
        self.grid_columnconfigure(1, weight=1)  # entry expands

        vcmd = (self.register(self._validate))

        self.subtract_button = customtkinter.CTkButton(self, text="-", width=height-6, height=height-6,
                                                       command=self.subtract_button_callback)
        self.subtract_button.grid(row=0, column=0, padx=(3, 0), pady=3)

        self.entry = customtkinter.CTkEntry(self, width=width-(2*height), height=height-6, border_width=0, validate='key', validatecommand=(vcmd, '%P'))
        self.entry.grid(row=0, column=1, columnspan=1, padx=3, pady=3, sticky="ew")

        self.add_button = customtkinter.CTkButton(self, text="+", width=height-6, height=height-6,
                                                  command=self.add_button_callback)
        self.add_button.grid(row=0, column=2, padx=(0, 3), pady=3)

        # default value
        self.entry.insert(0, int(value))

        self.entry.bind("<Key>", self.bind_callback)
        self.entry.bind("<FocusOut>", self.bind_callback)
        self.entry.bind("<Return>", self.bind_callback)
        self.entry.bind("<MouseWheel>", self.mousewheel_callback)
        
    def bind_callback(self, event):
        if self.command is not None:
            self.command()
    
    def mousewheel_callback(self, event):
        if event.delta > 0:
            self.add_button_callback()
        elif event.delta < 0:
            self.subtract_button_callback()

    def add_button_callback(self):
        try:
            value = int(self.entry.get()) + self.step_size
            if self.max is not None and value > self.max:
                return
            self.entry.delete(0, "end")
            self.entry.insert(0, value)
        except ValueError:
            return
        if self.command is not None:
            self.command()

    def subtract_button_callback(self):
        try:
            value = int(self.entry.get()) - self.step_size
            if self.min is not None and value < self.min:
                return
            self.entry.delete(0, "end")
            self.entry.insert(0, value)
        except ValueError:
            return
        if self.command is not None:
            self.command()

    def get(self) -> Union[int, None]:
        try:
            return int(self.entry.get())
        except ValueError:
            return None

    def set(self, value: int):
        self.entry.delete(0, "end")
        self.entry.insert(0, str(int(value)))

    def _validate(self, P):
        if P == "":
            return True
        else:
            try:
                int(P)
                return True
            except ValueError:
                return False


class FloatSpinbox(customtkinter.CTkFrame):
    def __init__(self, *args,
                 width: int = 100,
                 height: int = 32,
                 step_size: Union[int, float] = 1,
                 command: Callable = None,
                 value: float,
                 min: Optional [float] = None,
                 max: Optional [float] = None,
                 **kwargs):
        super().__init__(*args, width=width, height=height, **kwargs)

        self.step_size = step_size
        self.command = command

        self.min = min
        self.max = max

        self.configure(fg_color=("gray78", "gray28"))  # set frame color

        self.grid_columnconfigure((0, 2), weight=0)  # buttons don't expand
        self.grid_columnconfigure(1, weight=1)  # entry expands

        vcmd = (self.register(self._validate), '%d', '%P')

        self.subtract_button = customtkinter.CTkButton(self, text="-", width=height-6, height=height-6,
                                                       command=self.subtract_button_callback)
        self.subtract_button.grid(row=0, column=0, padx=(3, 0), pady=3)

        self.entry = customtkinter.CTkEntry(self, width=width-(2*height), height=height-6, border_width=0, validate='key', validatecommand=vcmd)
        self.entry.grid(row=0, column=1, columnspan=1, padx=3, pady=3, sticky="ew")

        self.add_button = customtkinter.CTkButton(self, text="+", width=height-6, height=height-6,
                                                  command=self.add_button_callback)
        self.add_button.grid(row=0, column=2, padx=(0, 3), pady=3)

        # default value
        self.entry.insert(0, float(value))

        self.entry.bind("<Key>", self.bind_callback)
        self.entry.bind("<FocusOut>", self.bind_callback)
        self.entry.bind("<Return>", self.bind_callback)
        self.entry.bind("<MouseWheel>", self.mousewheel_callback) 

    def bind_callback(self, event):
        if self.command is not None:
            self.command()

    def mousewheel_callback(self, event):
        if event.delta > 0:
            self.add_button_callback()
        elif event.delta < 0:
            self.subtract_button_callback()

    def add_button_callback(self):
        try:
            value = float(self.entry.get()) + self.step_size
            if self.max is not None and value > self.max:
                return
            self.entry.delete(0, "end")
            self.entry.insert(0, value)
        except ValueError:
            return
        if self.command is not None:
            self.command()

    def subtract_button_callback(self):
        try:
            value = float(self.entry.get()) - self.step_size
            if self.min is not None and value < self.min:
                return
            self.entry.delete(0, "end")
            self.entry.insert(0, value)
        except ValueError:
            return
        if self.command is not None:
            self.command()

    def get(self) -> Union[float, None]:
        try:
            return float(self.entry.get())
        except ValueError:
            return None

    def set(self, value: float):
        self.entry.delete(0, "end")
        self.entry.insert(0, str(float(value)))

    def _validate(self, d, P):
        if d == 0:
            return True
        if P == "":
            return True
        else:
            try:
                float(P)
                return True
            except ValueError:
                return False


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("VRChat AI Assistant")
        self.geometry("840x630")
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure((1,2), weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        column_id = 0
        row_id = 0

        # self.gcloud_frame = GCloudOptionsFrame(self, "GCloud TTS Configuration")
        # self.gcloud_frame.grid(row=1, column=cols, padx=(10,0), pady=(10, 10), sticky="nsew")
        self.tts_selector_frame = TTSSelectorFrame(self, "TTS Selection")
        self.tts_selector_frame.grid(row=row_id, column=column_id, padx=(10,0), pady=(10, 0), sticky="nsew")
        self.tts_selector_frame._set_tts_engine(opts.tts_engine_name)
        row_id += 1

        self.program_bools_frame = ProgramOptionsFrame(self, "Program Options")
        self.program_bools_frame.grid(row=row_id, column=column_id, padx=(10,0), pady=(10, 10), sticky="nsew")
        row_id += 1
        
        column_id += 1
        row_id = 0

        self.audio_stuff_frame = AudioStuffFrame(self, "Audio Configuration")
        self.audio_stuff_frame.grid(row=row_id, column=column_id, padx=(10,0), pady=(10, 0), sticky="nsew")
        row_id += 1

        self.keyboard_control_frame = KeyboardControlFrame(self, "Trigger Key Configuration")
        self.keyboard_control_frame.grid(row=row_id, column=column_id, padx=(10,0), pady=(10, 10), sticky="nsew")
        row_id += 1
        
        column_id += 1
        row_id = 0

        self.ai_stuff_frame = AIStuffFrame(self, "AI Configuration")
        self.ai_stuff_frame.grid(row=row_id, rowspan=2, column=column_id, padx=(10,10), pady=(10, 10), sticky="nsew")
        row_id += 1

        column_id += 1
        row_id = 0

        self.protocol("WM_DELETE_WINDOW",  self.on_close)

    def on_close(self):
        opts.LOOP = False
        self.destroy()

def initialize():
    global app 
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("green")

    app = App()
    app.iconbitmap(icon)
    app.mainloop()