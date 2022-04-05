#!/usr/bin/env python3

import sys
import argparse
import zmq
import json

class MessageSender:
    def __init__(self, target, msg):
        try:
            message = json.loads(msg)
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, 10000)
            socket.connect(target)
            print('Sending message: %s' % message)
            socket.send_json(message)
            response = socket.recv_string()
            print(response)
            if response == 'failure':
                sys.exit(1)
        except json.decoder.JSONDecodeError:
            print('Message is no valid JSON')
            sys.exit(1)
        except zmq.Again:
            print('Message receival not confirmed')
            sys.exit(1)
        except KeyboardInterrupt:
            print('interrupted')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simple app to send a json message to a target')
    parser.add_argument('-t', '--target', type=str, default='tcp://localhost:5555', help='receiver of the message')
    parser.add_argument('-m', '--message', type=str, required=True, help='the json message')
    args = parser.parse_args()
    MessageSender(args.target, args.message)
