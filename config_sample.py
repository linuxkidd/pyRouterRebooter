"""
RouterRebooter Config File
by: Michael J. Kidd

https://github.com/linuxkidd/RouterRebooter
"""

# This should be obvious
WIFI_SSID = 'MyAmazingWiFi'
WIFI_PASS = 'SuperSecretPass'

# MQTT_SERVER - the IP or Hostname of your MQTT broker
#   Leave blank to disable MQTT
MQTT_SERVER = '192.168.1.5'

# MQTT Topics to publish / subscribe to
TOPIC_BASE = b'RouterRebooter'
TOPIC_SUB = TOPIC_BASE+b'/cmd'
TOPIC_PUB = TOPIC_BASE+b'/status'

# CHECK_HOST and CHECK_PORT are the hostname (or IP) and port number
#   to open a TCP connection to.
CHECK_HOST = "one.one.one.one"
CHECK_PORT = 80

# CHECK_INTERVAL - seconds between connectivity test attempts
CHECK_INTERVAL = 60

# CHECK_MAX_MISS_TIME - seconds the internet must be offline
#   before cycling power
CHECK_MAX_MISS_TIME = 240

# CHECK_RESET_TIME - Seconds the internet must be returned before
#   resetting the 'MISS_TIME' timer.
#
# This is to make sure the internet is really back before ignoring
#   the prior failures
CHECK_RESET_TIME = 60

# MIN_ON_TIME == minimum time the power is applied before allowing 
#   the modem to be power cycled again.
RELAY_MIN_ON_TIME = 180

# OFF_DELAY == Time to leave the power off before turning it back on
RELAY_OFF_DELAY = 30

# These are correct for Sonoff S31 Lite, adjust as needed for your
# device.

PIN_BUTTON = 0
PIN_RELAY = 12
PIN_LED = 13
