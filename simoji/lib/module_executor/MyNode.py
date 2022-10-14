from anytree import AnyNode


class MyNode(AnyNode):

    def __init__(self, *args, **kwargs):

        self.name = None
        super(MyNode, self).__init__(*args, **kwargs)   # initialize at end to auto-create members from **kwargs
