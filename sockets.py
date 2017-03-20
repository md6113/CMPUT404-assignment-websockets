#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2017 Abram Hindle and J Maxwell Douglas
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, request, redirect
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True
clients = list()


class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()

    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())

    def world(self):
        return self.space

myWorld = World()


class Client:
    def __init__(self):
        self.queue = queue.Queue()

    def put(self, message):
        self.queue.put_nowait(message)

    def get(self):
        return self.queue.get()


# Code taken directly from the read_ws function found in Abram Hindle's git repo:
# https://github.com/abramhindle/WebSocketsExamples/blob/master/broadcaster.py
def send_all(msg):
    for client in clients:
        client.put( msg )


def send_all_json(obj):
    send_all( json.dumps(obj) )


def set_listener( entity, data ):
    ''' do something with the update ! '''
    # How to use json.dumps(): https://docs.python.org/2/library/json.html
    new_message = json.dumps({entity: data})
    for i in clients:
        i.put(new_message)

myWorld.add_set_listener( set_listener )


@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    return flask.redirect("/static/index.html")


def read_ws(ws,client):
    '''A greenlet function that reads from the websocket and updates the world'''
    # XXX: TODO IMPLEMENT ME
    # Code taken directly from the read_ws function found in Abram Hindle's git repo:
    # https://github.com/abramhindle/WebSocketsExamples/blob/master/broadcaster.py
    # Just added a little loop to run through the received message
    try:
        while True:
            message = ws.receive()
            print "Received: %s" % message
            if (message is not None):
                packet = json.loads(message)
                for entity in packet.keys():
                    myWorld.set(entity, packet[entity])
                send_all_json(packet)
            else:
                break
    except:
        '''Done'''


@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    # XXX: TODO IMPLEMENT ME
    # Code taken directly from the subscribe_socket function found in Abram Hindle's git repo:
    # https://github.com/abramhindle/WebSocketsExamples/blob/master/broadcaster.py
    client = Client()
    clients.append(client)
    g = gevent.spawn(read_ws, ws, client)

    msg = json.dumps(myWorld.world())
    ws.send(msg)

    try:
        while True:
            # block here
            msg = client.get()
            ws.send(msg)
    except Exception as e: # WebSocketError as e:
        print "WebSocket Error %s" % e
    finally:
        clients.remove(client)
        gevent.kill(g)


def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data != ''):
        return json.loads(request.data)
    else:
        return json.loads(request.form.keys()[0])


@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    '''update the entities via this interface'''
    new_message = flask_post_json()

    for i in new_message:
        myWorld.update(entity, i, new_message(i))

    return flask.jsonify(myWorld.get(entity))


@app.route("/world", methods=['POST','GET'])
def world():
    '''you should probably return the world here'''
    return flask.jsonify(myWorld.world())


@app.route("/entity/<entity>")
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''
    return flask.jsonify(myWorld.get(entity))


@app.route("/clear", methods=['POST','GET'])
def clear():
    '''Clear the world out!'''
    myWorld.clear()
    return flask.jsonify(myWorld.world())



if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
