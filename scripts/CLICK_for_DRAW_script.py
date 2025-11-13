# scripts/CLICK_for_DRAW_script.py
import time
from datetime import datetime

from .base_script import ScriptBase
from common.utils import adb_tap


class JamaScript(ScriptBase):

    @staticmethod
    def get_name():
        return "抽奖 -- 自动抽银劵/招福"

    @staticmethod
    def get_description():
        return ("通过连续点击来重复抽取 【猫咪转蛋券】/ 【招福转蛋】 奖励。\n        "
                "请首先选择进入需要操作的【转蛋】页面\n        "
                "请在【转蛋结束】后及时停止运行\n        ")

    @staticmethod
    def get_configurable_options():
        return [
            {
                'name': 'server',
                'label': '游戏服务器',
                'type': 'choice',
                'default': '台服',
                'options': ['台服', '日服']
            },
            {
                'name': 'max_loops',
                'label': '运行轮数 (0为无限)',
                'type': 'entry',
                'default': '无需设置'
            }
        ]

    @staticmethod
    def get_task_specific_options():
        return []

    def run(self, options):
        server = options['server']
        try:
            max_loops = int(options['max_loops'])
        except ValueError:
            max_loops = 0

        adb_path = options.get('adb_path')
        device_serial = options.get('device_serial')

        self.log(f"脚本 '{self.get_name()}' 已启动。")
        self.log(f"配置: 服务器={server}, 最大轮数={max_loops if max_loops > 0 else '无限'}")

        # 3. 核心逻辑
        i = 0
        time_start = datetime.now()

        while not self.is_stop_requested():

            # 检测终止
            if 0 < max_loops <= i:
                time_delta = datetime.now() - time_start
                deltaH, rem = divmod(time_delta.seconds, 3600)
                deltaM, deltaS = divmod(rem, 60)
                self.log(f"本任务耗时: {time_delta.days}天 {deltaH:02d}时 {deltaM:02d}分 {deltaS:02d}秒")
                self.log(f"\n已完成设定的 {max_loops} 轮任务，脚本自动停止。")
                return "COMPLETED"

            adb_tap(1565, 906, adb_path, device_serial)  # 10连转蛋 & OK 按钮
            time.sleep(0.25)

            i += 1

        self.log("脚本因用户请求而停止。")
        return "STOPPED"
