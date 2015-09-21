#!/usr/bin/env python
# -*-   encoding : utf8   -*-

'''This module is used for generating a process with a monitor
waiting for an error to passing out.
'''

import sys
import multiprocessing
import concurrent
import asyncio

try:
    from processing_watch import _base
except ImportError:
    import _base

class process(_base.__base_process):

    def __init__(self, target=None, loop=None, name=None,
                       args=(), kwargs={}):
        '''process(target = <function>, loop = [asyncio.loop],
        name = [process_name],
        args = [function_args], kwargs = [function_kwargs])
        '''
        self._config = {}
        self._config['target'] = target
        self._config['name'] = name
        self._config['args'] = args
        self._config['kwargs'] = kwargs
        if loop:
            self.loop = loop
        else:
            self.loop = asyncio.get_event_loop()
        if not asyncio.iscoroutinefunction(self._config['target']):
            self.executor = \
                    concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.process = multiprocessing.Process(target=self._proc,
                                       name=self._config['name'],)

    @asyncio.coroutine
    def __watch_dog(self):
        while self.is_started:
            if self._watch_outside.is_set():
                raise KeyboardInterrupt("Terminating from outside")
            yield from asyncio.sleep(_base._watch_dog_interval)

    @asyncio.coroutine
    def __coroutine_prog(self):
        self.set_started(True)
        try:
            yield from self._config['target'](*self._config['args'],
                                              **self._config['kwargs'])
        except BaseException as e:
            self.queue_err_out.put_nowait((self.process.name, e))
        self.set_started(False)

    def __normal_prog(self):
        self.set_started(True)
        try:
            self._config['target'](*self._config['args'],
                                   **self._config['kwargs'])
        except BaseException as e:
            self.queue_err_out.put_nowait((self.process.name, e))
        self.set_started(False)

    def __executor_run(self):
        self.executor.submit(self.__normal_prog,)

    def _proc(self):
        if not asyncio.iscoroutinefunction(self._config['target']):
            tmp_tasks = [self.__watch_dog()]
        else:
            tmp_tasks = [self.__coroutine_prog(),
                         self.__watch_dog()]
        if sys.version_info.minor == 4 and sys.version_info.micro <= 3:
            tmp_tasks = [asyncio.async(i) for i in tmp_tasks]
        else:
            tmp_tasks = [asyncio.ensure_future(i) for i in tmp_tasks]
        self.__tasks = asyncio.gather(*(tmp_tasks), loop=self.loop)
        try:
            if not asyncio.iscoroutinefunction(self._config['target']):
                self.__executor_run()
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
        if not asyncio.iscoroutinefunction(self._config['target']):
            self.executor.shutdown(False)
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

### Test funcion as below ###

@asyncio.coroutine
def coroutine_count_down(n):
    for i in range(n):
        print(n - i, "seconds to end.")
        yield from asyncio.sleep(1)
    print("Done")

def normal_count_down(n):
    for i in range(n):
        print(n - i, "seconds to end.")
        time.sleep(1)
    print("Done")

def test(target, error_test=False):
    a = process(target=target, args=(5,))
    print(a)
    print(a.process)
    a.start()
    try:
        if not error_test:
            a.join()
        else:
            a.join(3)
            print('Starting to raise error')
            raise ValueError("just for test")
    except Exception as e:
        print("sending error")
        #a.queue_err_in.put_nowait(e)
    except KeyboardInterrupt:
        print("Terminated by user.")
    if a.is_alive():
        a.join()

if __name__ == '__main__':
    import time

    print("coroutine_count_down testing start...")
    test(coroutine_count_down)
    print('')

    print("normal_count_down testing start...")
    test(normal_count_down)
    print('')

    print("error_test handle: coroutine_count_down testing start...")
    test(coroutine_count_down, True)
    print('')

    print("error_test handle: normal_count_down testing start...")
    test(normal_count_down, True)
    print('')

