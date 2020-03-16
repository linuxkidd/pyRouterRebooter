"""
RouterRebooter
by: Michael J. Kidd

https://github.com/linuxkidd/RouterRebooter
"""

def elapsed(total_seconds):
    """ Return human formatted elapsed time
        Adapted from: https://thesmithfam.org/blog/2005/11/19/python-uptime-script/ """

    # Helper vars:
    MINUTE  = 60
    HOUR    = MINUTE * 60
    DAY     = HOUR * 24

    # Get the days, hours, etc:
    days    = int(total_seconds / DAY)
    hours   = int((total_seconds % DAY) / HOUR)
    minutes = int((total_seconds % HOUR) / MINUTE)
    seconds = int(total_seconds % MINUTE)

    # Build up the pretty string (like this: "N days, N hours, N minutes, N seconds")
    string = ""
    if days > 0:
        string += str(days) + " d,"
    if len(string) > 0 or hours > 0:
        string += str(hours) + " h, "
    if len(string) > 0 or minutes > 0:
        string += str(minutes) + " m, "
    string += str(seconds) + " s"
    return string

def mqtt_cb(topic, msg):
    """ Called with topic and message as callback on received message to MQTT subscription """
    print((topic, msg))
    if topic == b'RouterRebooter/cmd':
        if msg == b'off':
            set_relay(0)
        elif msg == b'on':
            set_relay(1)
        elif msg == b'reboot':
            machine.reset()

def connect_MQTT():
    """ connect as MQTT client """
    if C.MQTT_SERVER != "":
        try:
            I['mqttc'] = MQTTClient(S['client_id'], C.MQTT_SERVER)
            I['mqttc'].set_callback(mqtt_cb)
            I['mqttc'].set_last_will(C.TOPIC_PUB, '{"status": "dead"}',True)
            I['mqttc'].connect()
            I['mqttc'].subscribe(C.TOPIC_SUB)
            print("Connected to %s MQTT broker, subscribed to %s topic" % (C.MQTT_SERVER, C.TOPIC_SUB))
        except OSError as e:
            print("Error setting up MQTT: ", end="")
            print(e)

def send_mqtt_status():
    """ Send MQTT status packet """
    if I['station'].isconnected() and C.MQTT_SERVER != "":
        try:
            S['uptime'] = elapsed(time.time()-I['boot_time'])
            S['current_time'] = time.time()
            S['mem_free'] = gc.mem_free()
            S['ip_address'] = I['station'].ifconfig()[0]
            I['mqttc'].publish(C.TOPIC_PUB, ujson.dumps(S))
            print("Published: %s" % ujson.dumps(S))
            I['mqtt_last_status'] = time.time()
        except:
            connect_MQTT()

def check_WiFi():
    """ Restart ESP to attempt a reconnection to WiFi """
    if not I['station'].isconnected():
        S['net_status'] = "offline"
        S['wifi_status'] = 0
        if time.time()-I['check_last_fail'] > C.CHECK_INTERVAL:
            I['check_last_fail'] = time.time()
            S['check_fail_count'] += 1
        print(".",end="")
        if time.time()-S['wifi_last_reconnect'] > 180:
            S['wifi_last_reconnect'] = time.time()
            I['station'].active(False)
            time.sleep(1)
            I['station'].active(True)
            I['station'].connect(C.WIFI_SSID, C.WIFI_PASS)
            print("WiFi Dropped, retrying connection")
    elif not S['wifi_status']:
        S['net_status'] = "online"
        S['wifi_status'] = 1
        print("Connection successful: ", end="")
        print(I['station'].ifconfig())

        print('Setting time...',end=" ")
        ntptime.settime()
        if not I['boot_time']:
            I['boot_time'] = time.time()
        if not S['relay_change_time']:
            S['relay_change_time'] = time.time()
        print("done")
        S['wifi_last_reconnect'] = time.time()
        print("%04d-%02d-%02d %02d:%02d:%02d" % time.localtime()[0:6])
        S['ip_address'] = I['station'].ifconfig()[0]
        connect_MQTT()

def check_success():
    """ Set variables for check success """
    S["message"] = ""
    S["check_last_success"] = time.time()
    if S["check_fail_count"] > 0:
        if time.time()-I["check_last_fail"] > C.CHECK_RESET_TIME:
            S["check_first_fail"] = 0
            S["check_fail_count"] = 0
        else:
            S["check_first_fail"] += C.CHECK_INTERVAL
            S["check_fail_count"] -= 1

def check_failed(er):
    """ Set variables for check failed """
    S["message"] = er
    if not S["check_first_fail"]:
        S["check_first_fail"] = time.time()
        S['net_status'] = "recent miss"
    I["check_last_fail"] = time.time()
    S["check_fail_count"] += 1


def check_internet():
    """ Check ability to open a socket to configured host """
    if I["station"].isconnected():
        try:
            addr = usocket.getaddrinfo(C.CHECK_HOST, C.CHECK_PORT)[0][-1]
            s = usocket.socket()
            s.settimeout(250)
            s.connect(addr)
            check_success()
        except OSError as e:
            check_failed(str(e))
        finally:
            s.close()

def set_relay(setto=5):
    """ Set relay status based on connection check state """
    if setto in [0,1]:
        # Set the relay to on (1) or off (0)
        S['relay_status'] = setto
        S['relay_change_time'] = time.time()
        send_mqtt_status()
    elif setto == 3:
        # Toggle the relay
        S['relay_status'] = int(not S['relay_status'])
        S['relay_change_time'] = time.time()
        send_mqtt_status()
    else:
        # Cycle power if no good ping in MAX_MISS_TIME
        if S["check_fail_count"] \
                and time.time()-S['check_first_fail'] > C.CHECK_MAX_MISS_TIME \
                and S['relay_status']:
            # NOTE: Prevent rebooting more frequently than every 3 minutes
            if time.time()-S['relay_change_time'] > C.RELAY_MIN_ON_TIME:
                S['relay_status'] = 0
                S['relay_change_time'] = time.time()
            else:
                S['net_status'] = "delay reboot %d seconds" % (C.RELAY_MIN_ON_TIME -(time.time()-S['relay_change_time']))

    # If the relay has been off longer than the configured delay, turn it back on
    if not S['relay_status'] and time.time() - S['relay_change_time'] > C.RELAY_OFF_DELAY:
        S['relay_status'] = 1
        S['relay_change_time'] = time.time()
        S['check_fail_count'] = 0
        S['check_first_fail'] = 0
        send_mqtt_status()

    P['relay'].value(S['relay_status'])

def check_button():
    """ Check the button status and toggle the relay """

    # NOTE: Value of 0 == button pressed, 1 == button released
    if not P['button'].value():
        # Button Pressed
        if I['button_down_time'] == 0:
            I['button_down_time'] = time.ticks_ms()
        else:
            if (time.ticks_ms()-I['button_down_time']) > I['button_debounce'] and not I['toggled']:
                I['toggled'] = 1
                set_relay(3) # Toggle
    else:
        # Button Released
        if I['button_down_time'] > 0:
            I['button_down_time'] = 0
            I['toggled'] = 0

def led_on():
    """ Turn on the LED """
    I['led_last_change'] = time.ticks_ms()
    I['led_state']=0
    P['led'].off() # LED state is inverse of pin

def led_off():
    """ Turn off the LED """
    I['led_last_change'] = time.ticks_ms()
    I['led_state']=1
    P['led'].on()  # LED state is inverse of pin

def led_toggle():
    """ Toogle the LED """
    I['led_state']=not I['led_state']
    P['led'].value(I['led_state'])
    I['led_last_change'] = time.ticks_ms()

def set_led():
    """ Toggle the LED on/off depending on status """
    led_delta=time.ticks_ms()-I['led_last_change']
    if not I['station'].isconnected():
        if led_delta > 200:
            led_toggle()
    else:
        if I['check_last_fail'] > 0:
            clf_delta = time.time()-I['check_last_fail']
            # NOTE: Multiplying by 7 because there are 7 x 1 second attempts during a miss
            miss_time = (time.time()-S["check_first_fail"]) * 7
            if clf_delta < (miss_time*0.25):
                S['net_status'] = "recent miss"
                if I['led_state'] and  led_delta > 800:
                    led_on()
                elif led_delta > 200:
                    led_off()
            elif clf_delta < (miss_time*0.75):
                S['net_status'] = "recovering"
                if I['led_state'] and led_delta > 500:
                    led_on()
                elif led_delta > 500:
                    led_off()
            elif (clf_delta > miss_time) and I['led_state']:
                led_on()
        else:
            led_on()

def main():
    """ main entry point """
    stat_count = 0
    try:
        tick=time.ticks_ms()
        while not I['station'].isconnected():
            if time.ticks_ms()-tick > 1000:
                check_WiFi()
                tick=time.ticks_ms()
            set_led()
        check_WiFi()
        check_internet()
        set_led()
        send_mqtt_status()
    except OSError as e:
        pass

    while True:
        try:
            if I['station'].isconnected():
                if C.MQTT_SERVER != "":
                    if not I['mqttc']:
                        connect_MQTT()
                    if I['mqttc']:
                        I['mqttc'].check_msg()
            else:
                check_WiFi()

            check_button()
            set_led()
            set_relay()

            if time.time() - I['mqtt_last_status'] > C.CHECK_INTERVAL:
                check_internet()
                if C.MQTT_SERVER != "":
                    send_mqtt_status()
                else:
                    I['mqtt_last_status'] = time.time()
                gc.collect()
                stat_count += 1
            else:
                time.sleep_ms(1)

            if (C.CHECK_INTERVAL * stat_count) > 120 and I['station'].isconnected():
                stat_count = 0
                ntptime.settime()

        except OSError as e:
            pass

if __name__ == '__main__':
    main()
