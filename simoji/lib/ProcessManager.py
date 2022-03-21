import multiprocessing
import time

import psutil
from typing import Optional, Callable


class ProcessManager:

    def __init__(self, nb_parallel_processes: Optional[int]=None):

        if nb_parallel_processes is None:
            # logical cores (includes hyperthreading)
            # nb_parallel_processes = len(psutil.Process().cpu_affinity()) - 1
            # nb_parallel_processes = multiprocessing.cpu_count()

            # physical cores
            nb_parallel_processes = (psutil.cpu_count(logical=False) - 1) or 1  # keep one core for main thread
        print("nb processes =", nb_parallel_processes)

        self.sema = multiprocessing.Semaphore(nb_parallel_processes)
        self.process_list = []

    def start_process(self, target_func, *args, **kwargs):
        # self.sema.acquire()
        p = multiprocessing.Process(target=self._func_and_release, args=(target_func, *args), kwargs=kwargs,
                                    daemon=True)
        self.process_list.append(p)
        p.start()

        return p

    def terminate_all_processes(self):
        for p in self.process_list:
            p.terminate()

    def _func_and_release(self, func: Callable, *args, **kwargs):
        # print(*args)
        self.sema.acquire()
        # time.sleep(0.1)
        func(*args, **kwargs)
        self.sema.release()

    def join_all_processes(self):
        for p in self.process_list:
            p.join()