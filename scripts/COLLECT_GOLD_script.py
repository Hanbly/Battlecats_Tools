# scripts/COLLECT_GOLD_script.py
import time
from datetime import datetime
from .base_script import ScriptBase
from common.utils import (if_image_on_screen, refresh_power, roll_screen,
                          gold_positions_order_default, ordered_fight_strategy, adb_tap)


class ConsumeScript(ScriptBase):

    @staticmethod
    def get_name():
        return "主线关卡 -- 自动刷金宝"

    @staticmethod
    def get_description():
        return ("请先在 【地图界面】 选择起始的关卡\n        "
                "请先把每一章节的【首关】刷成金宝，并选中【第二关】开始运行脚本")

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
                'label': '运行关数',
                'type': 'entry',
                'default': '48'
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
                'name': 'collect_all_gold_enabled',
                'label': '开启全金宝收集:\n(关闭用于推主线)',
                'type': 'checkbutton',
                'default': True  # 默认开启
            },
            {
                'name': 'position_order',
                'label': '战斗出喵策略',
                'type': 'ordered_multicheck',
                'options': troop_labels,
                'default': gold_positions_order_default,  # 默认全部勾选
                'columns': 6  # 自定义每行列数
            }
        ]

    def run(self, options):
        # 1. 从 options 字典中获取所有配置
        server = options.get('server')
        roll_start = [950, 438]
        roll_left_end = [750, 438]
        roll_right_end = [1150, 438]
        duration_ms = 300
        try:
            max_loops = int(options.get('max_loops', 1000))
        except (ValueError, TypeError):
            max_loops = 0

        adb_path = options.get('adb_path')
        device_serial = options.get('device_serial')

        # 获取专属配置，并提供安全的默认值
        refresh_power_enabled = options.get('refresh_power_enabled', True)
        use_power_recover_enabled = options.get('use_power_recover_enabled', False)
        collect_all_gold_enabled = options.get('collect_all_gold_enabled', True)
        position_order = options.get('position_order', gold_positions_order_default)
        if not isinstance(position_order, list):  # 安全检查
            position_order = gold_positions_order_default

        # 2. 根据配置设置动态参数
        if server == '台服':
            package_name = "jp.co.ponos.battlecatstw"
            image_folder = "images_tw/"
        else:  # 日服
            package_name = "jp.co.ponos.battlecats"
            image_folder = "images_jp/"

        self.log(f"脚本 '{self.get_name()}' 已启动。")
        self.log(f"配置: 服务器={server}, 最大关数={max_loops if max_loops > 0 else '无限'}")
        self.log(f"专属配置: "
                 f"刷新统率力={'开启' if refresh_power_enabled else '关闭'}, "
                 f"全金宝收集={collect_all_gold_enabled}, "
                 f"出喵策略={position_order}")

        # 3. 核心逻辑
        i = 0
        time_start = datetime.now()

        while not self.is_stop_requested():
            if 0 < max_loops <= i:
                self.log(f"\n已完成设定的 {max_loops} 关任务，脚本自动停止。")
                return "COMPLETED"

            # 使用 self.log 替代 print
            self.log("-" * 30)
            self.log(f"第 {i + 1} 关开始...")

            # 记录运行时间
            time_delta = datetime.now() - time_start
            deltaH, rem = divmod(time_delta.seconds, 3600)
            deltaM, deltaS = divmod(rem, 60)
            self.log(f"已运行: {time_delta.days}天 {deltaH:02d}时 {deltaM:02d}分 {deltaS:02d}秒")

            # 主逻辑
            try:
                while not self.is_stop_requested():
                    chose_ok = False
                    if collect_all_gold_enabled:
                        if (not chose_ok) and (
                                not if_image_on_screen(adb_path, device_serial, "gold_left", image_folder, confidence_threshold=0.9)):
                            roll_screen(adb_path, device_serial,
                                        roll_start[0], roll_start[1],
                                        roll_right_end[0], roll_right_end[1],
                                        duration_ms)  # 换上一关
                            self.log("\n上一关无金宝，进行回调重刷。")
                            time.sleep(0.75)
                            break

                        if (not chose_ok) and (
                                if_image_on_screen(adb_path, device_serial, "gold", image_folder, confidence_threshold=0.9)):
                            roll_screen(adb_path, device_serial,
                                        roll_start[0], roll_start[1],
                                        roll_left_end[0], roll_left_end[1],
                                        duration_ms=300)  # 换下一关
                            i += 1
                            time.sleep(0.75)
                            break
                    else:
                        time.sleep(0.75)

                    adb_tap(1627, 765, adb_path, device_serial)

                    # 判断统率力
                    time.sleep(0.5)
                    if if_image_on_screen(adb_path, device_serial, "power_limited", image_folder,
                                          confidence_threshold=0.7):

                        if (not refresh_power_enabled) and (not use_power_recover_enabled):
                            self.log("\n由于同时限制使用白魔法或首领旗回复统率力，脚本自动停止。")
                            return "STOPPED"

                        if use_power_recover_enabled:
                            adb_tap(729, 712, adb_path, device_serial)
                            time.sleep(0.5)
                            adb_tap(1627, 765, adb_path, device_serial)
                        else:
                            refresh_power(self.driver, package_name, image_folder, adb_path, device_serial)
                            time.sleep(1.5)
                            adb_tap(1627, 765, adb_path, device_serial)

                    # 等待返回地图
                    positions_to_tap = ordered_fight_strategy(position_order)
                    find_return = False
                    while not find_return and not if_image_on_screen(adb_path, device_serial, "return_map", image_folder,
                                                                     confidence_threshold=0.7):
                        for pos in positions_to_tap:
                            if if_image_on_screen(adb_path, device_serial, "return_map", image_folder, confidence_threshold=0.7):
                                find_return = True
                                break
                            adb_tap(pos[0], pos[1], adb_path, device_serial)
                            time.sleep(0.25)
                    adb_tap(1861, 57, adb_path, device_serial)
                    adb_tap(1861, 57, adb_path, device_serial)
                    adb_tap(1861, 57, adb_path, device_serial)
                    time.sleep(1)

                    if not collect_all_gold_enabled:
                        i += 1
                        break

            except Exception as e:
                print(f"错误发生: {e}")

        self.log("脚本因用户请求而停止。")
        return "STOPPED"
