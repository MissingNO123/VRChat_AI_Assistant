# vrcutils.py (c) 2023 MissingNO123
# Description: This module contains utility functions for interfacing with VRChat. It provides functions for sending messages to the chatbox, setting avatar parameters, handling OSC messages from VRChat, and parsing the VRChat log file. The module also initializes the OSC client and server for communication with VRChat.

import os, re, threading, time, psutil, requests
from pythonosc import udp_client
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer

import options as opts
import functions as funcs


def chatbox(message):
    """ Send a message to the VRC chatbox if enabled """
    if opts.chatbox:
        osc_client.send_message("/chatbox/input", [message, True, False])


def set_parameter(address, value):
    """ Sets an avatar parameter on your current VRC avatar """
    address = "/avatar/parameters/" + address
    osc_client.send_message(address, value)


def parameter_handler(address, *args):
    """ Handle OSC messages for specific parameters received from VRChat """
    if address == "/avatar/parameters/ChatGPT_PB" or address == "/avatar/parameters/ChatGPT":
        if args[0]:
            opts.trigger = True
        funcs.v_print(f"{address}: {args} (V:{opts.trigger})")


def clear_prop_params():
    set_parameter('VoiceRec_End', True)
    set_parameter('CGPT_Result', True)
    set_parameter('CGPT_End', True)

# VRC OSC init
# Client (Sending)
osc_client = udp_client.SimpleUDPClient(opts.vrc_ip, opts.vrc_osc_inport)
# chatbox('▶️ Starting...')
# Server (Receiving)
dispatcher = Dispatcher()
dispatcher.map("/avatar/parameters/*", parameter_handler)
osc_server = ThreadingOSCUDPServer(("127.127.127.127", opts.vrc_osc_outport), dispatcher)


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
        self.process_monitor_thread = threading.Thread(target=self._monitor_vrchat, daemon=True)
        self.log_watcher_thread = threading.Thread(target=self._watch_log_file, daemon=True)
        self.log_directory = os.path.join(os.path.expanduser("~"), 'AppData', 'LocalLow', 'VRChat', 'VRChat')
        # TODO: add logic for Linux/Proton

    def start(self):
        self.running = True
        # self.process_monitor_thread = threading.Thread(target=self._monitor_vrchat)
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
            time.sleep(60)

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
        return vrc_player_count