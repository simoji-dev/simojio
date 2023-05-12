from simojio.lib.module_executor.MyNode import MyNode


class LeaveNode(MyNode):

    def __init__(self, name: str, parent: MyNode):

        self.save_path = None
        self.tab_window_id = None

        super(LeaveNode, self).__init__(name=name, parent=parent)

    def set_save_path(self, save_path: str):
        self.save_path = save_path
