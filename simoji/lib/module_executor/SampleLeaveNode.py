import multiprocessing as mp

from simoji.lib.module_executor.LeaveNode import LeaveNode
from simoji.lib.module_executor.MyNode import MyNode
from simoji.lib.Sample import Sample


class SampleLeaveNode(LeaveNode):

    def __init__(self, name: str, parent: MyNode, sample: Sample, global_queue: mp.Queue):

        super(LeaveNode, self).__init__(name=name, parent=parent)

        self.sample = sample
        self.global_queue = global_queue

        self.input_queue = mp.JoinableQueue()
        self.optimization_queue = mp.Queue()
        self.result_queue = mp.Queue()
