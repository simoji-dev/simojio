import multiprocessing
import psutil
from typing import Optional, Callable


class ProcessManager:

    def __init__(self, nb_parallel_processes: Optional[int]=None):

        if nb_parallel_processes is None:
            nb_parallel_processes = self.get_nb_physical_cores() or 1       # at least one

        self.sema = multiprocessing.Semaphore(nb_parallel_processes)
        self.process_list = []

    def start_process(self, target_func, *args, **kwargs):
        p = multiprocessing.Process(target=self._func_and_release, args=(target_func, *args), kwargs=kwargs,
                                    daemon=True)
        self.process_list.append(p)
        self.sema.acquire()
        p.start()

        return p

    def _func_and_release(self, func: Callable, *args, **kwargs):
        # self.sema.acquire()
        func(*args, **kwargs)
        self.sema.release()

    def join_all_processes(self):
        for p in self.process_list:
            p.join()

    def get_nb_processes(self):
        return len(self.process_list)

    @staticmethod
    def get_nb_physical_cores(include_logical_cores=False) -> int:
        return psutil.cpu_count(logical=include_logical_cores)
