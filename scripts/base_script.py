# scripts/base_script.py
from abc import ABC, abstractmethod


class ScriptBase(ABC):
    """
    所有脚本插件的抽象基类。
    定义了脚本与主GUI交互所需的标准接口。
    """
    def __init__(self, driver, stop_event, logger):
        """
        初始化脚本实例。
        :param driver: Appium driver 实例。
        :param stop_event: 一个 threading.Event 对象，用于优雅地停止脚本。
        :param logger: 一个回调函数，用于将日志信息发送到GUI。
        """
        self.driver = driver
        self.stop_event = stop_event
        self.logger = logger

    @staticmethod
    @abstractmethod
    def get_name():
        """返回脚本的名称，用于在GUI下拉列表中显示。"""
        pass

    @staticmethod
    @abstractmethod
    def get_description():
        """返回脚本的简短描述。"""
        pass

    @staticmethod
    @abstractmethod
    def get_configurable_options():
        """
        返回一个配置项列表，GUI将根据这个列表动态生成设置界面。
        返回格式: [
            {'name': 'internal_name', 'label': 'UI Label', 'type': 'choice', 'options': ['A', 'B'], 'default': 'A'},
            {'name': 'another_name', 'label': 'Another Label', 'type': 'entry', 'default': '100'}
        ]
        """
        pass

    @staticmethod
    def get_task_specific_options():
        """
        返回一个描述任务专属配置的列表，用于生成动态配置窗口。
        此方法是可选的。如果脚本没有专属配置，则无需实现此方法。
        返回格式: [
            {'name': 'internal_name', 'label': 'UI Label', 'type': 'checkbutton', 'default': True},
            {'name': 'multi_select', 'label': 'Multi Select Label', 'type': 'multicheck', 'options': ['opt1', 'opt2'], 'default': [0, 1]}
        ]
        """
        return []

    @abstractmethod
    def run(self, options):
        """
        脚本的主执行逻辑。
        :param options: 一个字典，包含用户在GUI中设置的所有配置项的值。
        :return: 脚本执行的状态，如 "COMPLETED", "STOPPED", "ERROR"。
        """
        pass

    def log(self, message):
        """通过回调函数将日志打印到GUI。"""
        if self.logger:
            self.logger(str(message))

    def is_stop_requested(self):
        """检查停止事件是否被触发。脚本循环中应频繁调用此方法。"""
        return self.stop_event.is_set()
