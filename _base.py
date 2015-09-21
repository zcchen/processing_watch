#!/usr/bin/env python
# -*-   encoding : utf8   -*-

import multiprocessing

_watch_dog_interval = 0.01

class __base_process(object):
    _is_started = False
    _is_closed = False
    queue_err_out = multiprocessing.Queue()
    _watch_outside = multiprocessing.Event()

    def __init__(self):
        '''Initializated by child class'''
        #raise NotImplementedError("This method should be realized by child.")
        pass

    @property
    def is_started(self):
        return self._is_started

    #@property.setter
    def set_started(self, boolean):
        self._is_started = boolean

    @property
    def is_closed(self):
        return self._is_closed

    #@property.setter
    def set_closed(self, boolean):
        self._is_closed = boolean

    def is_alive(self):
        return self.process.is_alive()

    def reset(self):
        '''When the processing is done or terminate, run this function before restart.
        '''
        if self.is_closed and not self.is_started:
            self._is_closed = False
            if self.loop.is_closed():
                self.loop = asyncio.get_event_loop()

    def first_clean(self):
        '''First action when processing is being closed.
        '''
        self._is_closed = True
        self._is_started = False

    def last_clean(self):
        '''Last action when processing is being closed.
        '''
        self._is_closed = True
        self._is_started = False
        while not self.queue_err_out.empty():
            self.queue_err_out.get_nowait()
        self._watch_outside.clear()

    def start(self):
        self.reset()
        self.process.start()
        print(self.process.name, 'is started.')

    def run(self):
        '''Run the target as common usage.
        '''
        self.start()
        self.join()

    def join(self, timeout=None):
        '''Compatiable with multiprocessing.processing.join()
        '''
        if self.process.is_alive():
            self.process.join(timeout)

    def terminate(self):
        self._watch_outside.set()

    def exception_run(self, exception):
        '''Exception handler, modify it if you need.
        '''
        print(exception)

    def keyboard_interrupt_run(self, exception):
        '''KeyboardInterrupt handler, modify it if you need.
        '''
        print(exception)
