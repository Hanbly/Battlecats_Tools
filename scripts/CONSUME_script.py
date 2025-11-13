# scripts/CONSUME_script.py
import time
from datetime import datetime
from .base_script import ScriptBase
from common.utils import (if_image_on_screen, refresh_power, consume_positions_order_default, ordered_fight_strategy, adb_tap)


class ConsumeScript(ScriptBase):

    @staticmethod
    def get_name():
        return "加码多多 -- 快速消耗道具"

    @staticmethod
    def get_description():
        return "请先在 【地图界面】 选择需要消耗的道具类型\n        请将阵容提前更改为 第一只猫是【牛猫】或【狂乱牛猫】！\n        请将关卡调整至【世界篇1的第2关-香港】"

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
                'default': '1000'
            }
        ]

    @staticmethod
    def get_task_specific_options():
        # 定义此脚本的专属配置UI
        troop_labels = [
            "钱包升级", "喵1", "喵2", "喵3", "喵4", "喵5",
            "喵6", "喵7", "喵8", "喵9", "喵10", "猫炮发射"
        ]

        return [
            {
                'name': 'refresh_power_enabled',
                'label': '开启自动刷新统率力',
                'type': 'checkbutton',
                'default': True  # 默认开启
            },
            {
                'name': 'use_power_recover_enabled',
                'label': '开启自动使用首领旗（若开启则优先使用）',
                'type': 'checkbutton',
                'default': False
            },
            {
                'name': 'position_order',
                'label': '战斗出喵策略',
                'type': 'ordered_multicheck',
                'options': troop_labels,
                'default': consume_positions_order_default,  # 默认第一只
                'columns': 6  # 自定义每行列数
            }
        ]

    def run(self, options):
        # 1. 从 options 字典中获取所有配置
        server = options.get('server')
        try:
            max_loops = int(options.get('max_loops', 1000))
        except (ValueError, TypeError):
            max_loops = 0

        adb_path = options.get('adb_path')
        device_serial = options.get('device_serial')

        # 获取专属配置，并提供安全的默认值
        refresh_power_enabled = options.get('refresh_power_enabled', True)
        use_power_recover_enabled = options.get('use_power_recover_enabled', False)
        position_order = options.get('position_order', consume_positions_order_default)
        if not isinstance(position_order, list):  # 安全检查
            position_order = consume_positions_order_default

        # 2. 根据配置设置动态参数
        if server == '台服':
            package_name = "jp.co.ponos.battlecatstw"
            image_folder = "images_tw/"
        else:  # 日服
            package_name = "jp.co.ponos.battlecats"
            image_folder = "images_jp/"

        self.log(f"脚本 '{self.get_name()}' 已启动。")
        self.log(f"配置: 服务器={server}, 最大轮数={max_loops if max_loops > 0 else '无限'}")
        self.log(f"专属配置: 刷新统率力={'开启' if refresh_power_enabled else '关闭'}, 出喵策略={position_order}")

        # 3. 核心逻辑
        i = 0
        flag = 0
        time_start = datetime.now()

        while not self.is_stop_requested():
            if 0 < max_loops <= i:
                self.log(f"\n已完成设定的 {max_loops} 轮任务，脚本自动停止。")
                return "COMPLETED"

            # 使用 self.log 替代 print
            self.log("-" * 30)
            self.log(f"第 {i + 1} 轮开始...")

            # 记录运行时间
            time_delta = datetime.now() - time_start
            deltaH, rem = divmod(time_delta.seconds, 3600)
            deltaM, deltaS = divmod(rem, 60)
            self.log(f"已运行: {time_delta.days}天 {deltaH:02d}时 {deltaM:02d}分 {deltaS:02d}秒")

            # 主逻辑
            try:
                while not self.is_stop_requested():

                    # 开始战斗
                    if flag:
                        adb_tap(1627, 765, adb_path, device_serial)
                    else:
                        while not if_image_on_screen(adb_path, device_serial, "start_fight_map", image_folder, confidence_threshold=0.7):
                            time.sleep(0.5)
                        adb_tap(1627, 765, adb_path, device_serial)

                    # 判断统率力
                    time.sleep(0.5)
                    if if_image_on_screen(adb_path, device_serial, "power_limited", image_folder, confidence_threshold=0.7):

                        if (not refresh_power_enabled) and (not use_power_recover_enabled):
                            self.log("\n由于同时限制使用白魔法或首领旗回复统率力，脚本自动停止。")
                            return "STOPPED"

                        if use_power_recover_enabled:
                            adb_tap(729, 712, adb_path, device_serial)
                            continue

                        refresh_power(self.driver, package_name, image_folder, adb_path, device_serial)
                        continue

                    # 等待返回地图
                    positions_to_tap = ordered_fight_strategy(position_order)
                    while not if_image_on_screen(adb_path, device_serial, "start_fight_map", image_folder, confidence_threshold=0.7):
                        for pos in positions_to_tap:
                            adb_tap(pos[0], pos[1], adb_path, device_serial)
                        adb_tap(1861, 57, adb_path, device_serial)
                    i += 1
                    break

            except Exception as e:
                print(f"错误发生: {e}")

        self.log("脚本因用户请求而停止。")
        return "STOPPED"
