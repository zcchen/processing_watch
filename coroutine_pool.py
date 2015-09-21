#!/usr/bin/env python
# -*-   encoding : utf8   -*-

'''This module is used for generate one process for multi-coroutines
with a monitor waiting for an error to passing out.
'''

import sys
import multiprocessing
import concurrent
import asyncio

try:
    from processing_watch import _base
except ImportError:
    import _base

class sync_pool_process(_base.__base_process):

    def __init__(self, target=[], loop=None, name=None):
        '''pool(target = <funcion(*args, **kwargs)|... >, loop = [asyncio.loop],
        name = [process_name])
        funcions should be all coroutines.
        '''
        self._config = {}
        for i in target:
            if asyncio.iscoroutinefunction(i):
                raise NotImplementedError( \
                        str(i) + " did not contain *args or **kwargs.")
            elif not asyncio.iscoroutine(i):
                raise NotImplementedError( \
                        str(i) + " should be a coroutine function.")
        self._config['target'] = target
        self._config['name'] = name
        if loop:
            self.loop = loop
        else:
            self.loop = asyncio.get_event_loop()
        self.process = multiprocessing.Process(target=self._proc,
                                       name=self._config['name'])

    @asyncio.coroutine
    def __watch_dog(self):
        while self.is_started:
            if self._watch_outside.is_set():
                raise KeyboardInterrupt("Terminating from outside")
            yield from asyncio.sleep(_base._watch_dog_interval)

    @asyncio.coroutine
    def __coroutine_prog(self, func):
        self.set_started(True)
        try:
            yield from func
        except BaseException as e:
            self.queue_err_out.put_nowait((self.process.name, e))
        self.set_started(False)

    def _proc(self):
        tmp_tasks = [self.__coroutine_prog(i) for i in self._config['target'] ]
        tmp_tasks += [self.__watch_dog()]
        if sys.version_info.minor == 4 and sys.version_info.micro <= 3:
            tmp_tasks = [asyncio.async(i) for i in tmp_tasks]
        else:
            tmp_tasks = [asyncio.ensure_future(i) for i in tmp_tasks]
        self.__tasks = asyncio.gather(*(tmp_tasks), loop=self.loop)
        try:
            self.loop.run_until_complete(self.__tasks)
        except Exception as e:
            self._is_started = False
            self.queue_err_out.put_nowait((self.process.name, e))
            self.exception_run(e)
        except KeyboardInterrupt as e:
            self._is_started = False
            self.keyboard_interrupt_run(e)
        finally:
            self.__end()

    def __end(self):
        '''Funcion to exit loop gracefully.'''
        self.first_clean()
        close_tasks = [self.close()]
        self.loop.run_until_complete(asyncio.wait(close_tasks))
        try:
            self.__tasks.cancel()
            self.__tasks.exception()
        except asyncio.InvalidStateError:
            pass
        except KeyboardInterrupt:
            pass
        except Exception as e:
            self.exception_run(e)
        finally:
            self.loop.close()
            self.last_clean()

    @asyncio.coroutine
    def close(self):
        '''closing loop handler, modify it if you need.
        NOTICE: asyncio.coroutine type
        '''
        pass

###### Test function as below ###

@asyncio.coroutine
def con_1(n):
    for i in range(n):
        print(n - i, "second to end. con_1")
        yield from asyncio.sleep(1)
    print("Done. con_1")

@asyncio.coroutine
def con_2(n):
    for i in range(n):
        print(n - i, "second to end. con_2")
        yield from asyncio.sleep(1)
    print("Done. con_2")

def test(error_test=False):
    target = [con_1(5), con_2(5)]
    a = sync_pool_process(target=target)
    print("test start, error_test=", error_test)
    a.start()
    try:
        if not error_test:
            a.join()
        else:
            a.join(3)
            print("starting to raise error")
            raise ValueError("just for test")
    except Exception as e:
        print("sending error")
        a.terminate()
    except KeyboardInterrupt:
        print("Terminated by user.")
        a.terminate()
    if a.is_alive():
        a.join()

if __name__ == '__main__':
    print("no error raising test")
    test(error_test=False)

    print("")
    print("error raising test")
    test(error_test=True)
