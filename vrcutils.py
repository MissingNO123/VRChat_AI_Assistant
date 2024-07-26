# vrcutils.py (c) 2023 MissingNO123
# Description: This module contains utility functions for interfacing with VRChat. It provides functions for sending messages to the chatbox, setting avatar parameters, and handling OSC messages from VRChat. The module also initializes the OSC client and server for communication with VRChat.

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
