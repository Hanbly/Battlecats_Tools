# scripts/COLLECT_ZOMBIE_script.py
import time
from datetime import datetime, timedelta
from .base_script import ScriptBase
from common.utils import (if_image_on_screen, refresh_power, roll_screen, roll_some_length, click_press_and_release,
                          gold_positions_order_default, ordered_fight_strategy, adb_tap, find_and_click_image,
                          long_roll_length, long_roll_time_ms, adb_press_and_release, tap_cats_in_fight)


class ConsumeScript(ScriptBase):

    @staticmethod
    def get_name():
        return "主线关卡 -- 自动刷不死入侵"

    @staticmethod
    def get_description():
        return ("请在 【主界面】 启动")

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
                'default': '0'
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
                'name': 'refresh_zombie_enabled',
                'label': '自动刷新不死关（请开启防火墙）',
                'type': 'checkbutton',
                'default': True
            },
            {
                'name': 'max_times',
                'label': '地图数量限制（从【世界一】开始计数）',
                'type': 'entry',
                'default': 3
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
        try:
            max_loops = int(options.get('max_loops', 1000))
        except (ValueError, TypeError):
            max_loops = 0

        adb_path = options.get('adb_path')
        device_serial = options.get('device_serial')

        # 获取专属配置，并提供安全的默认值
        refresh_power_enabled = options.get('refresh_power_enabled', True)
        use_power_recover_enabled = options.get('use_power_recover_enabled', False)
        refresh_zombie_enabled = options.get('refresh_zombie_enabled', True)
        max_times_default = int(options.get('max_times', 3))
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
                 f"出喵策略={position_order}")

        # 3. 核心逻辑
        i = 0
        start = True
        max_times = max_times_default
        time_start = datetime.now()

        while not self.is_stop_requested():
            if 0 < max_loops <= i:
                self.log(f"\n已完成设定的 {max_loops} 关任务，脚本自动停止。")
                return "COMPLETED"

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
                    enter_map_ok = False
                    click_press_and_release(adb_path, device_serial, "change_map", image_folder,
                                            confidence_threshold=0.7)
                    time.sleep(2)
                    if start:
                        roll_some_length(adb_path, device_serial, long_roll_length, long_roll_time_ms, 2,
                                         vertical=False)
                        start = False
                    while max_times:
                        if if_image_on_screen(adb_path, device_serial, "zombie_map", image_folder,
                                              confidence_threshold=0.7):
                            find_and_click_image(adb_path, device_serial, "zombie_map", image_folder,
                                                 confidence_threshold=0.7)
                            time.sleep(2)
                            click_press_and_release(adb_path, device_serial, "start_game", image_folder,
                                                    confidence_threshold=0.7)
                            enter_map_ok = True
                            break
                        else:
                            roll_screen(adb_path, device_serial,
                                        roll_start[0], roll_start[1],
                                        roll_left_end[0], roll_left_end[1],
                                        duration_ms=300)  # 换下一关
                            max_times -= 1
                            time.sleep(0.75)

                    if not enter_map_ok:
                        if refresh_zombie_enabled:
                            refresh_power(self.driver, package_name, image_folder, adb_path, device_serial,
                                          is_legend=True)  # is_legend=True 决定这一步不会点击开始游戏
                            start = True
                            max_times = max_times_default
                            continue
                        else:
                            adb_tap(85, 1000, adb_path, device_serial)  # 左下角的返回
                            start = True
                            max_times = max_times_default
                            continue

                    timeout = datetime.now() + timedelta(seconds=5)
                    while datetime.now() < timeout:
                        if if_image_on_screen(adb_path, device_serial, "zombie_inner", image_folder,
                                              confidence_threshold=0.7):
                            find_and_click_image(adb_path, device_serial, "zombie_inner", image_folder,
                                                 confidence_threshold=0.7)
                            chose_ok = True
                            time.sleep(4)
                            break
                        time.sleep(0.25)

                    if not chose_ok:
                        adb_tap(85, 1000, adb_path, device_serial)  # 左下角的返回
                        continue

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
                            time.sleep(1)
                            adb_tap(1627, 765, adb_path, device_serial)
                        elif refresh_power_enabled:
                            refresh_power(self.driver, package_name, image_folder, adb_path, device_serial,
                                          is_legend=True)  # is_legend=True 决定这一步不会点击开始游戏
                            start = True
                            max_times = max_times_default
                            continue

                    # 等待返回地图
                    positions_to_tap = ordered_fight_strategy(position_order)
                    while not if_image_on_screen(adb_path, device_serial, "return_map", image_folder,
                                                 confidence_threshold=0.7):
                        if self.is_stop_requested():
                            break
                        tap_cats_in_fight(positions_to_tap, adb_path, device_serial)

                    adb_press_and_release(1861, 57, adb_path, device_serial)  # 点击返回地图
                    adb_press_and_release(1861, 57, adb_path, device_serial)
                    adb_press_and_release(1861, 57, adb_path, device_serial)
                    time.sleep(2)
                    adb_tap(85, 1000, adb_path, device_serial)  # 左下角的返回
                    time.sleep(2)

                    i += 1

                    if max_times <= 0:
                        if refresh_power_enabled:
                            refresh_power(self.driver, package_name, image_folder, adb_path, device_serial,
                                          is_legend=True)  # is_legend=True 决定这一步不会点击开始游戏
                            start = True
                            max_times = max_times_default

            except Exception as e:
                print(f"错误发生: {e}")

        self.log("脚本因用户请求而停止。")
        return "STOPPED"
