#!/usr/bin/env python3

import time
from rpi_ws281x import PixelStrip, Color
import argparse
from argparse import Namespace
import zmq
from threading import Thread

# LED strip configuration:
LED_INNER = 40
LED_OUTER = 48
LED_COUNT = LED_INNER + LED_OUTER   # Number of LED pixels.
LED_PIN = 18            # GPIO pin connected to the pixels (18 uses PWM!).
# LED_PIN = 10          # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ = 800000    # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10            # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255    # Set to 0 for darkest and 255 for brightest
LED_INVERT = False      # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0         # set to '1' for GPIOs 13, 19, 41, 45 or 53

MISSTEP = LED_OUTER / (LED_OUTER - LED_INNER)


class StripManager(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.__run = True
        self.action = None
        self.strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
        self.strip.begin()

    def run(self):
        while self.__run:
            if self.action is not None:
                self.do_action()
            time.sleep(0.1)

    def setAll(self, color):
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, color)
        self.strip.show()

    def flash(self, r, g, b, wait_ms=5):
        for i in range(max(r,g,b)):
            self.setAll(Color(min(r,i),min(g,i),min(b,i)))
            time.sleep(wait_ms / 1000.0)

    def drawBothRings(self, color, position):
        dpos = round (position / MISSTEP)
        self.strip.setPixelColor(position - dpos, color)
        self.strip.setPixelColor(LED_INNER + position, color)

    def colorWipe(self, color, start_led=0, end_led=LED_COUNT, wait_ms=50):
        for i in range(start_led, end_led):
            self.strip.setPixelColor(i, color)
            self.strip.show()
            time.sleep(wait_ms / 1000.0)

    def drawTimer(self, color, seconds=5):
        if seconds <= 0:
            print('no countdown')
            return
        for i in range(0, seconds):
            position = round((i+1) * LED_OUTER/seconds)
            for pos in range(0, position):
                self.drawBothRings(color, pos)
            self.strip.show()
            time.sleep(1)

    def stop(self):
        self.__run = False

    def do_action(self):
        msg = self.action
        if msg.mode == 'timer':
            strip.drawTimer(Color(msg.r, msg.g, msg.b), msg.duration)
        elif msg.mode == 'flash':
            strip.flash(msg.r, msg.g, msg.b, msg.wait)
        elif msg.mode == 'wipe':
            strip.colorWipe(Color(msg.r, msg.g, msg.b), msg.wait)
        elif msg.mode == 'setAll':
            strip.setAll(Color(msg.r, msg.g, msg.b))
            msg.reset = False
        if not hasattr(msg, 'reset') or msg.reset == True:
            strip.setAll(Color(0, 0, 0))
        self.action = None

    def set_action(self, action):
        self.action = action

def handle_message(strip, message):
    msg = Namespace(**message)
    try:
        msg.r = int(msg.r)
        msg.g = int(msg.g)
        msg.b = int(msg.b)
        if msg.mode == 'timer':
            msg.duration = int(msg.duration)
        elif msg.mode == 'flash':
            msg.wait = int(msg.wait)
        elif msg.mode == 'wipe':
            msg.wait = int(msg.wait)
        elif msg.mode == 'setAll':
            pass
        else:
            socket.send_string('failure: unknown message')
            return
    except (AttributeError, ValueError, TypeError) as e:
        print('attribute error %s' % e)
        socket.send_string('failure: %s' % e)
        return
    strip.set_action(msg)
    socket.send_string('message handled')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    strip = StripManager()
    strip.start()

    print('Press Ctrl-C to quit.')
    
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind('tcp://*:5555')
    try:
        while True:
            try:
                message = socket.recv_json(flags=zmq.NOBLOCK)
                print('Received: %s' % message)
                handle_message(strip, message)
            except zmq.Again:
                pass

    except KeyboardInterrupt:
        strip.colorWipe(Color(0, 0, 0), wait_ms=10)
        strip.stop()
        strip.join()
