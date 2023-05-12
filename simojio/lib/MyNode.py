from anytree import AnyNode


class MyNode(AnyNode):

    def __init__(self, *args, **kwargs):

        self.name = None

        self.sample = None
        self.input_queue = None
        self.result_queue = None
        self.global_queue = None
        self.optimization_queue = None

        self.save_path = None
        self.tab_window = None

        super(MyNode, self).__init__(*args, **kwargs)   # initialize at end to auto-create members from **kwargs


