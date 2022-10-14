from simoji.lib.module_executor.MyNode import MyNode


class ForkNode(MyNode):

    def __init__(self, name: str, parent: MyNode):

        super(ForkNode, self).__init__(name=name, parent=parent)