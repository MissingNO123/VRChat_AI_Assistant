import tkinter.messagebox
import customtkinter
import threading
import time
# if __name__ != "__main__": import __main__
import __main__

"""
frame 1: program options
    - verbose logging
    - chatboxes
    - parrot mode
    - sound feedback
    - audio trigger
frame 2: ai stuff
    - Whisper Prompt (textfield)
    - Whisper Model (dropdown)
    - GPT Model (dropdown)
    - Max Tokens (spinbox)
    - Max Conv Length (spinbox)
frame 3: control options
    - key press window
    - key trigger key
frame 4: audio stuffs
    - rms threshold (slider?)
    - silence timeout (spinbox)
    - max recording time (spinbox)
    - input device name (textfield)
    - output device name (textfield)
frame 5: gcloud stuffs
    - language code (dropdown)
    - voice name (dropdown)
"""


class ProgramOptionsFrame(customtkinter.CTkFrame):
    def __init__(self, master, title):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.title = title
        self.checkboxes = []
        self.checkbox_names = [
            "Verbose logging",
            "Chatboxes",
            "Parrot mode",
            "Sound feedback",
            "Audio trigger"
        ]
        self.variables = [
            __main__.verbosity,
            __main__.chatbox_on,
            __main__.parrot_mode,
            __main__.soundFeedback,
            __main__.audio_trigger_enabled
        ]

        self.title = customtkinter.CTkLabel(
            self, text=self.title, fg_color="gray30", corner_radius=6)
        self.title.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")

        self.vars = []
        for i, val in enumerate(self.variables):
            var = customtkinter.BooleanVar(value=self.variables[i])
            self.vars.append(var)

        for i, name in enumerate(self.checkbox_names):
            checkbox = customtkinter.CTkCheckBox( self, text=name, variable=self.vars[i], command=self._update_checkboxes )
            # checkbox._command = lambda ind=i, c=checkbox: self._update_var( self.variable_names[ind], c )
            checkbox.grid( row=i+1, column=0, padx=10, pady=(10, 0), sticky="w" )
            self.checkboxes.append(checkbox)

    # def _update_var(self, var_name, checkbox):
    #     globals()[var_name] = bool(checkbox.get())

    def _update_checkboxes(self):
        checkboxes = []
        for i, checkbox in enumerate(self.checkboxes):
            checkboxes.append(bool(checkbox.get()))
        __main__.receiveCheckboxes(checkboxes)


class AIStuffFrame(customtkinter.CTkFrame):
    def __init__(self, master, title):
        super().__init__(master)
        self.grid_columnconfigure(1, weight=1)
        self.title = title
        self.whispermodels = ["tiny", "tiny.en", "small", "small.en", "medium", "medium.en", "large", "large-v2"]

        self.title = customtkinter.CTkLabel(
            self, text=self.title, fg_color="gray30", corner_radius=6)
        self.title.grid(row=0, column=0, columnspan=3, padx=10, pady=(10,0), sticky="ew")

        vcmd = (self.register(self._validate))

        self.whisper_prompt = customtkinter.StringVar(value=__main__.whisper_prompt)
        self.selected_whisper_model = customtkinter.StringVar(value=__main__.whisper_model)
        self.gpt_radio_var = customtkinter.IntVar(value=0 if __main__.gpt == "GPT-3.5-Turbo" else 1)
        self.max_tokens_var = customtkinter.IntVar(value=__main__.max_tokens)
        self.max_conv_length_var = customtkinter.IntVar(value=__main__.max_conv_length)
        self.sytem_prompt_var = customtkinter.StringVar(value=__main__.systemPrompt)

        self.label_whisper_prompt = customtkinter.CTkLabel(self, text="Whisper Prompt: ", fg_color="transparent")
        self.label_whisper_prompt.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4,1), padx=5)
        self.textfield_whisper_prompt = customtkinter.CTkEntry(self, width=200, placeholder_text="Whisper Prompt...", textvariable=self.whisper_prompt)
        self.textfield_whisper_prompt.grid(row=2, column=0, columnspan=2, sticky="ew", pady=2, padx=10)
        # self.button_whisper_prompt = customtkinter.CTkButton(self, text="Set", width=50, command=self._update_whisper_prompt)
        # self.button_whisper_prompt.grid(row=2, column=2, sticky="ew", padx=(0,10))

        self.label_whisper_model = customtkinter.CTkLabel(self, text="Whisper Model: ", fg_color="transparent")
        self.label_whisper_model.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4,1), padx=5)
        self.dropdown_whisper_model = customtkinter.CTkOptionMenu(self, variable=self.selected_whisper_model, values=self.whispermodels, command=self._update_whisper_model)
        self.dropdown_whisper_model.grid(row=4, column=0, columnspan=3, sticky="ew", padx=10)

        self.label_gpt_picker = customtkinter.CTkLabel(self, text="OpenAI GPT Model: ", fg_color="transparent")
        self.label_gpt_picker.grid(row=5, column=0, sticky="w", pady=(4,1), padx=5)
        self.radiobutton_gpt_3 = customtkinter.CTkRadioButton(self, text="GPT-3.5-Turbo", command=self._update_gpt_model, variable=self.gpt_radio_var, value=0)
        self.radiobutton_gpt_3.grid(row=6, column=0, padx=10)
        self.radiobutton_gpt_4 = customtkinter.CTkRadioButton(self, text="GPT-4", command=self._update_gpt_model, variable=self.gpt_radio_var, value=1)
        self.radiobutton_gpt_4.grid(row=6, column=1)

        self.label_max_tokens = customtkinter.CTkLabel(self, text="GPT Max Tokens: ", fg_color="transparent")
        self.label_max_tokens.grid(row=7, column=0, sticky="w", pady=(4,1), padx=5)
        self.textfield_max_tokens = customtkinter.CTkEntry(self, width=50, placeholder_text="###", textvariable=self.max_tokens_var, validate='key', validatecommand=(vcmd, '%P'))
        self.textfield_max_tokens.grid(row=8, column=0, columnspan=2, sticky="w", pady=2, padx=(10,2))

        self.label_max_conv_length = customtkinter.CTkLabel(self, text="GPT Max Conv. Length: ", fg_color="transparent")
        self.label_max_conv_length.grid(row=9, column=0, sticky="w", pady=(4,1), padx=5)
        self.textfield_max_conv_length = customtkinter.CTkEntry(self, width=50, placeholder_text="#", textvariable=self.max_conv_length_var, validate='key', validatecommand=(vcmd, '%P'))
        self.textfield_max_conv_length.grid(row=10, column=0, columnspan=2, sticky="w", pady=2, padx=(10,2))

        self.label_system_prompt = customtkinter.CTkLabel(self, text="GPT System Prompt: ", fg_color="transparent")
        self.label_system_prompt.grid(row=11, column=0, sticky="w", pady=(4,1), padx=5)
        self.textbox_system_prompt = customtkinter.CTkTextbox(self, height=122, wrap="word")
        self.textbox_system_prompt.insert("0.0", __main__.systemPrompt)
        self.textbox_system_prompt.grid(row=12, column=0, columnspan=3, sticky="ew", padx=10, pady=(0,2))
        self.button_system_prompt = customtkinter.CTkButton(self, text="Update System Prompt", command=self._update_system_prompt)
        self.button_system_prompt.grid(row=13, column=0, columnspan=3, sticky="ew", padx=10, pady=(2,10))

        self.button_reset = customtkinter.CTkButton(self, text="Clear Message History", command=self._reset)
        self.button_reset.grid(row=14, column=0, columnspan=3, sticky="ew", padx=10, pady=(2,10))

        self.textfield_whisper_prompt.bind("<FocusOut>", self._update_whisper_prompt)
        self.textfield_whisper_prompt.bind("<Return>", self._update_whisper_prompt)

        self.textfield_max_tokens.bind("<FocusOut>", self._update)
        self.textfield_max_tokens.bind("<Return>", self._update)

        self.textfield_max_conv_length.bind("<FocusOut>", self._update)
        self.textfield_max_conv_length.bind("<Return>", self._update)

    def _update_whisper_prompt(self, event=None):
        __main__.whisper_prompt = self.whisper_prompt.get()

    def _update_whisper_model(self, choice):
        __main__.whisper_model = choice

    def _update_gpt_model(self):
        value = self.gpt_radio_var.get()
        __main__.gpt = "GPT-3.5-Turbo" if value == 0 else "GPT-4"

    def _update_system_prompt(self):
        __main__.systemPrompt = self.textbox_system_prompt.get("0.0", "end")

    def _reset(self):
        __main__.handle_command("reset")

    def _update(self, event=None):
        __main__.systemPrompt = self.textbox_system_prompt.get("0.0", "end")
        value = self.gpt_radio_var.get()
        __main__.gpt = "GPT-3.5-Turbo" if value == 0 else "GPT-4"
        __main__.whisper_prompt = self.whisper_prompt.get()
        __main__.max_tokens = int(self.max_tokens_var.get())
        __main__.max_conv_length = int(self.max_conv_length_var.get())

    def _validate(self, P):
        if P == "":
            return True
        else:
            try:
                int(P)
                return True
            except ValueError:
                return False


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
        
        self.rms_threshold = customtkinter.StringVar(self, value=__main__.THRESHOLD)
        self.silence_timeout = customtkinter.StringVar(self, value=__main__.SILENCE_TIMEOUT)
        self.max_recording_time = customtkinter.StringVar(self, value=__main__.MAX_RECORDING_TIME)
        self.input_device_name = customtkinter.StringVar(self, value=__main__.in_dev_name)
        self.output_device_name = customtkinter.StringVar(self, value=__main__.out_dev_name)

        row_id = 1

        self.label_rms_threshold = customtkinter.CTkLabel(self, text="Audio Trigger Threshold: ", fg_color="transparent")
        self.label_rms_threshold.grid(row=row_id, column=0, sticky="w", pady=(4,1), padx=5)
        row_id += 1
        self.textfield_rms_threshold = customtkinter.CTkEntry(self, width=50, placeholder_text="#", textvariable=self.rms_threshold, validate='key', validatecommand=(vcmd, '%P'))
        self.textfield_rms_threshold.grid(row=row_id, column=0, columnspan=2, sticky="w", pady=2, padx=10)
        self.textfields.append(self.textfield_rms_threshold)
        row_id += 1

        self.label_silence_timeout = customtkinter.CTkLabel(self, text="Silence Timeout: ", fg_color="transparent")
        self.label_silence_timeout.grid(row=row_id, column=0, sticky="w", pady=(4,1), padx=5)
        row_id += 1
        self.textfield_silence_timeout = customtkinter.CTkEntry(self, width=50, placeholder_text="#", textvariable=self.silence_timeout, validate='key', validatecommand=(vcmd, '%P'))
        self.textfield_silence_timeout.grid(row=row_id, column=0, columnspan=2, sticky="w", pady=2, padx=10)
        self.textfields.append(self.textfield_silence_timeout)
        row_id += 1

        self.label_max_recording_time = customtkinter.CTkLabel(self, text="Max Listen Time: ", fg_color="transparent")
        self.label_max_recording_time.grid(row=row_id, column=0, sticky="w", pady=(4,1), padx=5)
        row_id += 1
        self.textfield_max_recording_time = customtkinter.CTkEntry(self, width=50, placeholder_text="#", textvariable=self.max_recording_time, validate='key', validatecommand=(vcmd, '%P'))
        self.textfield_max_recording_time.grid(row=row_id, column=0, columnspan=2, sticky="w", pady=2, padx=10)
        self.textfields.append(self.textfield_max_recording_time)
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

    def _update_audio_page(self, event=None):
        try:
            __main__.THRESHOLD = int(self.rms_threshold.get())
            __main__.SILENCE_TIMEOUT = float(self.silence_timeout.get())
            __main__.MAX_RECORDING_TIME = float(self.max_recording_time.get())
            __main__.in_dev_name = self.input_device_name.get()
            __main__.out_dev_name = self.output_device_name.get()
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
        
        self.key_press_window_var = customtkinter.DoubleVar(self, value=__main__.key_press_window)

        row_id = 1

        self.label_key_press_window = customtkinter.CTkLabel(self, text="Double Press Window: ", fg_color="transparent")
        self.label_key_press_window.grid(row=row_id, column=0, sticky="w", pady=(4,1), padx=5)
        row_id += 1
        self.textfield_key_press_window = customtkinter.CTkEntry(self, width=50, placeholder_text="#", textvariable=self.key_press_window_var, validate='key', validatecommand=(vcmd, '%P'))
        self.textfield_key_press_window.grid(row=row_id, column=0, columnspan=2, sticky="w", pady=2, padx=10)
        self.textfields.append(self.textfield_key_press_window)
        row_id += 1

        for field in self.textfields:
            field.bind("<FocusOut>", self._update_keyboard_page)
            field.bind("<Return>", self._update_keyboard_page)
        
    def _update_keyboard_page(self, event=None):
        __main__.key_press_window = float(self.key_press_window_var.get())

    def _validate(self, P):
        if P == "":
            return True
        else:
            try:
                float(P)
                return True
            except ValueError:
                return False


class GCloudOptionsFrame(customtkinter.CTkFrame):
    def __init__(self, master, title):
        super().__init__(master)
        self.title = title
        self.grid_columnconfigure(0, weight=1)
        self.textfields = []
        
        self.title = customtkinter.CTkLabel(
            self, text=self.title, fg_color="gray30", corner_radius=6)
        self.title.grid(row=0, column=0, columnspan=3, padx=10, pady=(10,0), sticky="ew")
        
        self.gcloud_language_code_var = customtkinter.StringVar(self, value=__main__.gcloud_language_code)
        self.gcloud_voice_name_var = customtkinter.StringVar(self, value="Standard-F")

        row_id = 1

        self.label_gcloud_language_code = customtkinter.CTkLabel(self, text="TTS Language Code: ", fg_color="transparent")
        self.label_gcloud_language_code.grid(row=row_id, column=0, sticky="w", pady=(4,1), padx=5)
        row_id += 1
        self.textfield_gcloud_language_code = customtkinter.CTkEntry(self, width=60, placeholder_text="#", textvariable=self.gcloud_language_code_var)
        self.textfield_gcloud_language_code.grid(row=row_id, column=0, columnspan=2, sticky="w", pady=2, padx=10)
        self.textfields.append(self.textfield_gcloud_language_code)
        row_id += 1

        self.label_gcloud_voice = customtkinter.CTkLabel(self, text="TTS Voice Name: ", fg_color="transparent")
        self.label_gcloud_voice.grid(row=row_id, column=0, sticky="w", pady=(4,1), padx=5)
        row_id += 1
        self.textfield_gcloud_voice = customtkinter.CTkEntry(self, placeholder_text="#", textvariable=self.gcloud_voice_name_var)
        self.textfield_gcloud_voice.grid(row=row_id, column=0, columnspan=2, sticky="ew", pady=2, padx=10)
        self.textfields.append(self.textfield_gcloud_voice)
        row_id += 1

        for field in self.textfields:
            field.bind("<FocusOut>", self._update_gcloud)
            field.bind("<Return>", self._update_gcloud)

    def _update_gcloud(self, event=None):
        __main__.gcloud_language_code = self.gcloud_language_code_var.get()
        __main__.gcloud_voice_name = f'{self.gcloud_language_code_var.get()}-{self.gcloud_voice_name_var.get()}'


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("my app")
        self.geometry("854x600")
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure((1,2), weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        cols=0

        self.program_bools_frame = ProgramOptionsFrame(self, "Program Options")
        self.program_bools_frame.grid(row=0, column=cols, padx=(10,0), pady=(10, 0), sticky="nsew")
        
        self.gcloud_frame = GCloudOptionsFrame(self, "GCloud TTS Configuration")
        self.gcloud_frame.grid(row=1, column=cols, padx=(10,0), pady=(10, 10), sticky="nsew")
        cols += 1

        self.audio_stuff_frame = AudioStuffFrame(self, "Audio Configuration")
        self.audio_stuff_frame.grid(row=0, column=cols, padx=(10,0), pady=(10, 0), sticky="nsew")

        self.keyboard_control_frame = KeyboardControlFrame(self, "Trigger Key Configuration")
        self.keyboard_control_frame.grid(row=1, column=cols, padx=(10,0), pady=(10, 10), sticky="nsew")
        cols += 1

        self.ai_stuff_frame = AIStuffFrame(self, "AI Configuration")
        self.ai_stuff_frame.grid(row=0, rowspan=2, column=cols, padx=(10,0), pady=(10, 10), sticky="nsew")
        cols += 1

        self.protocol("WM_DELETE_WINDOW",  self.on_close)

    #     self.button = customtkinter.CTkButton(self, text="my button", command=self.button_callback)
    #     self.button.grid(row=2, column=0, columnspan=3 , padx=10, pady=10, sticky="ew")

    # def button_callback(self):
    #     checked_boxes = self.program_bools_frame.get()
    #     print(checked_boxes)

    def on_close(self):
        __main__.handle_command("shutdown")
        self.destroy()


def initialize():
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("green")

    app = App()
    app.mainloop()

if __name__ == "__main__": 
    initialize()