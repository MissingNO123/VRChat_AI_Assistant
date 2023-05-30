from pythonosc import udp_client
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer

import options as opts
import functions as funcs

ip = "127.0.0.1"  # IP and Ports for VRChat OSC
inPort = 9000
outPort = 9001


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


# VRC OSC init
# Client (Sending)
osc_client = udp_client.SimpleUDPClient(ip, inPort)
# chatbox('▶️ Starting...')
# Server (Receiving)
dispatcher = Dispatcher()
dispatcher.map("/avatar/parameters/*", parameter_handler)
osc_server = ThreadingOSCUDPServer((ip, outPort), dispatcher)
