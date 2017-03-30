#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# This application is simply a library for Hayo
# 
# Copyright (c) 2017 François Wautier
#
# Permission is hereby granted, free of charge, to any person obtaining a copy 
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies
# or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR 
# IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
import asyncio as aio
import json,datetime


UDP_BROADCAST_PORT = 49073
CLICK_TIMEOUT = 300 #millisecs max length of inter click click
LONG_TIMEOUT = 600 #millisecs min length of long click

class Boxel():
    def __init__(self,name,hayo,loop):
        self.name=name
        self.hayo=hayo
        self.loop=loop
        self.do_process=lambda y: print ("Got: {}".format(y))
        
    def process_message(self,msg):
        self.do_process(msg)
        
class Button(Boxel):
    """Here we transform the value into single click, double click or long"""
    def __init__(self,name,hayo,loop):
        super(Button,self).__init__(name,hayo,loop)
        self.timer=datetime.datetime.now()-datetime.timedelta(hours=1)
        self.state=False
        self.cstate=False #True if expecting a double click
        self.msg=None
    
    def process_message(self,msg):
        tstmp=datetime.datetime.now()
        if msg["on"]: #start of click
            if tstmp-self.timer<=datetime.timedelta(milliseconds=CLICK_TIMEOUT):
                self.cstate=True
                print("Look for double")
            self.state=True
        else:
            if tstmp-self.timer>datetime.timedelta(milliseconds=LONG_TIMEOUT):
                msg["click"]="long"
                del msg["on"]
                self.state=False
                self.do_process(msg)
            elif self.cstate:
                self.cstate=False
                msg["click"]="double"
                del msg["on"]
                self.do_process(msg)
            else:
                self.msg=msg
                aio.ensure_future(self.timeout(msg))
        self.timer = tstmp
                
    async def timeout(self,msg):
        await aio.sleep((CLICK_TIMEOUT+50.0)/1000)
        if not self.cstate:
            msg["click"]="single"
            del msg["on"]
            self.do_process(msg)
     

class Slider(Boxel):
    
    def process_message(self,msg):
        self.do_process(msg)

class Barrier(Boxel):
    
    def process_message(self,msg):
        self.do_process(msg)
   

def boxelfactory(msg,loop):
    if msg["type"]=="button":
        return Button(msg["boxel"],msg["hayo"],loop)
    elif msg["type"]=="slider":
        return Slider(msg["boxel"],msg["hayo"],loop)
    elif msg["type"]=="barrier":
        return Barrier(msg["boxel"],msg["hayo"],loop)
    else:
        print("WTF. Unknown boxel")
        return Boxel(msg["boxel"],msg["hayo"],loop)


class Hayo():
    def __init__(self, name,loop):
        self.name=name
        self.boxels={}
        self.loop=loop
        
    def process_message(self,msg):
        if msg["boxel"] not in self.boxels:
            self.boxels[msg["boxel"]]=boxelfactory(msg,self.loop)
            
        self.boxels[msg["boxel"]].process_message(msg)

class HayoListener(aio.DatagramProtocol):
  
    def __init__(self, loop, parent=None):
        self.hayo = {} #Known devices name
        self.parent = parent #Where to register new devices
        self.transport = None
        self.loop = loop

    def connection_made(self, transport):
        #print('started')
        self.transport = transport
        sock = self.transport.get_extra_info("socket")

    def datagram_received(self, data, addr):
        message=json.loads(data.decode())
        if message["hayo"] not in self.hayo:
            self.hayo[message["hayo"]]= Hayo(message["hayo"],self.loop)
        self.hayo[message["hayo"]].process_message(message)
            
           

 
            
    def connection_lost(self,e):
        print ("Ooops lost connection")
        self.loop.close()
        
    def register(self,hayo):
        if self.parent:
            self.parent.register(hayo)
        
    def unregister(self,hayo):
        try:
            self.hayo.remove(hayo.name)
        except:
            pass
        if self.parent:
            self.parent.unregister(hayo)
            

