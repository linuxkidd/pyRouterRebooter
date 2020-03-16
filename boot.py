"""
RouterRebooter
by: Michael J. Kidd

https://github.com/linuxkidd/RouterRebooter
"""

import micropython
import network
import uselect
import usocket
import time
import ntptime
from umqtt.simple import MQTTClient
from ubinascii import hexlify
import machine
from esp import osdebug
import ujson
import gc


osdebug(None)
gc.collect()
import config as C

# Status array
S = {
    'check_fail_count':      0,
    'check_first_fail':      0,
    'check_last_success':    0,
    'client_id': hexlify(machine.unique_id()),
    'current_time':          0,
    'ip_address':           "",
    'mem_free':              0,
    'net_status':            0,
    'relay_change_time':     0,
    'relay_status':          1,
    'uptime':                0,
    'wifi_last_reconnect':   0,
    'wifi_status':           0
    }

# Internal array
I = {
    'boot_time':             0,
    'button_down_time':      0,
    'button_debounce':     100,
    'check_last_fail':       0,
    'led_last_change':       0,
    'led_state':             1,
    'mqttc':             False,
    'mqtt_last_status':      0,
    'toggled':               0
    }

# Pins array
P = {
    'button':  machine.Pin(C.PIN_BUTTON, machine.Pin.IN, machine.Pin.PULL_UP),
    'led':     machine.Pin(C.PIN_LED, machine.Pin.OUT, value=0),
    'relay':   machine.Pin(C.PIN_RELAY, machine.Pin.OUT, value=S['relay_status'])
    }

P['led'].on()  # NOTE: This is inverse of the LED illumination

I['station'] = network.WLAN(network.STA_IF)
I['station'].active(True)
I['station'].connect(C.WIFI_SSID, C.WIFI_PASS)

I['ap'] = network.WLAN(network.AP_IF)
I['ap'].active(False)
