import time
from abc import ABC
from datetime import datetime, timedelta

from common.utils import (if_image_on_screen, refresh_power, legend_positions_order_default,
                          ordered_fight_strategy, roll_and_find_spec_legend_activity, roll_some_length,
                          enter_legend_time, tap_cats_in_fight, long_roll_length, long_roll_time_ms, long_roll_counts,
                          calculate_activity_earliest_timezone_value, change_time_zone, recover_time_zone,
                          g_original_timezone, act_timeout_time, back_to_main_place_time,
                          run_adb_command, adb_press_and_release, click_press_and_release, find_and_click_image)
from scripts.base_script import ScriptBase


class LegendaryScriptBase(ScriptBase, ABC):
    template_name = None
    activity_name = None
    find_activity_confidence = 0.8

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
                'default': '0'
            }
        ]

    @staticmethod
    def get_task_specific_options():
        troop_labels = [
            "钱包升级", "喵1", "喵2", "喵3", "喵4", "喵5",
            "喵6", "喵7", "喵8", "喵9", "喵10", "猫炮发射"
        ]
        return [
            {
                'name': 'refresh_power_enabled',
                'label': '开启自动刷新统率力',
                'type': 'checkbutton',
                'default': True
            },
            {
                'name': 'use_power_recover_enabled',
                'label': '开启自动使用首领旗（若开启则优先使用）',
                'type': 'checkbutton',
                'default': False
            },
            {
                'name': 'change_timezone_enabled',
                'label': '开启自动转换时区',
                'type': 'checkbutton',
                'default': True
            },
            {
                'name': 'long_roll_times',
                'label': '长滚动次数:\n(如果长滚动略过'
                         '目标活动，则把值置0再使用)',
                'type': 'entry',
                'default': long_roll_counts
            },
            {
                'name': 'position_order',
                'label': '战斗出喵策略',
                'type': 'ordered_multicheck',
                'options': troop_labels,
                'default': legend_positions_order_default,
                'columns': 6
            }
        ]

    def check_timezone(self, adb_path, device_serial):
        self.log(f"[INFO] 正在为活动“{self.activity_name}”计算可用时区...")
        timezone, target_dt = calculate_activity_earliest_timezone_value(self.activity_name, adb_path, device_serial)
        tz_str_raw = run_adb_command(adb_path, device_serial, "shell date +%z")
        current_timezone_str = f"{int(tz_str_raw[:3]):+03d}:00" if tz_str_raw and len(tz_str_raw) == 5 else ""

        if timezone and target_dt:
            if timezone == current_timezone_str:
                self.log(f"[SUCCESS] 无需调整，活动正在进行中！(当前时区: {timezone})")
                return True
            else:
                self.log(f"[ERROR] 目前不处于活动中，请考虑开启 自动转换时区 或 手动调整！")
                return False
        else:
            self.log(f"[ERROR] 今天及前后一天内可能无“{self.activity_name}”活动。")
            return False

    def change_timezone(self, adb_path, device_serial):
        self.log(f"[INFO] 正在为活动“{self.activity_name}”计算可用时区...")
        timezone, target_dt = calculate_activity_earliest_timezone_value(self.activity_name, adb_path, device_serial)
        tz_str_raw = run_adb_command(adb_path, device_serial, "shell date +%z")
        current_timezone_str = f"{int(tz_str_raw[:3]):+03d}:00" if tz_str_raw and len(tz_str_raw) == 5 else ""

        if timezone and target_dt:
            if timezone == current_timezone_str:
                self.log(f"[SUCCESS] 无需调整，活动正在进行中！(当前时区: {timezone})")
                return True
            else:
                status_text = f"计算完成！准备调整时区至: {timezone}"
                self.log(f"[INFO] {status_text}")
                self.log(f"[INFO] 正在跳转至 {timezone}...")
                success = change_time_zone(adb_path, device_serial, timezone)
                if success:
                    self.log(f"[SUCCESS] 时区已成功跳转至: {timezone}")
                    return True
                else:
                    self.log(f"[ERROR] 时区跳转失败！")
                    return False
        else:
            self.log(f"[ERROR] 计算失败: 今天及前后一天内可能无“{self.activity_name}”活动。")
            return False

    def timezone_block(self, change_timezone_enabled, adb_path, device_serial):
        if change_timezone_enabled:
            status = self.change_timezone(adb_path, device_serial)
            if not status:
                recover_time_zone(adb_path, device_serial, g_original_timezone)
                self.log("[ERROR] 时区转换失败，脚本停止运行。")
                return False
        else:
            status = self.check_timezone(adb_path, device_serial)
            if not status:
                recover_time_zone(adb_path, device_serial, g_original_timezone)
                self.log("\n由于未开启自动转换时区，且目前未处于活动中，脚本停止运行。")
                return False
        return True

    def detect_legend_act_timeout(self, adb_path, device_serial, image_folder, change_timezone_enabled, long_roll_times,
                                  timing="start_fight"):
        time.sleep(1)
        if if_image_on_screen(adb_path, device_serial, "act_timeout", image_folder,
                              confidence_threshold=0.7, is_legend=True):
            if if_image_on_screen(adb_path, device_serial, "OK", image_folder, confidence_threshold=0.7):
                adb_press_and_release(1246, 685, adb_path, device_serial)
            time.sleep(act_timeout_time)
            if if_image_on_screen(adb_path, device_serial, "X", image_folder, confidence_threshold=0.7):
                click_press_and_release(adb_path, device_serial, "X", image_folder, confidence_threshold=0.7)
            if timing == "start_fight":
                adb_press_and_release(84, 990, adb_path, device_serial)
            elif timing == "return_map":
                pass
            time.sleep(back_to_main_place_time)
            if if_image_on_screen(adb_path, device_serial, "X", image_folder, confidence_threshold=0.7):
                click_press_and_release(adb_path, device_serial, "X", image_folder, confidence_threshold=0.7)
            if not self.timezone_block(change_timezone_enabled, adb_path, device_serial):
                return -1
            if not click_press_and_release(adb_path, device_serial, "start_game", image_folder,
                                           confidence_threshold=0.7):
                return -1
            time.sleep(enter_legend_time)
            roll_some_length(adb_path, device_serial, long_roll_length, long_roll_time_ms, long_roll_times)
            roll_and_find_spec_legend_activity(adb_path, device_serial, self.template_name,
                                               image_folder,
                                               confidence_threshold=self.find_activity_confidence)
            return 1
        return None

    def detect_legend_refresh_power(self, adb_path, device_serial, image_folder, package_name, refresh_power_enabled,
                                    use_power_recover_enabled, change_timezone_enabled, long_roll_times):
        time.sleep(0.5)
        if if_image_on_screen(adb_path, device_serial, "power_limited", image_folder,
                              confidence_threshold=0.7):
            if (not refresh_power_enabled) and (not use_power_recover_enabled):
                recover_time_zone(adb_path, device_serial, g_original_timezone)
                self.log("\n由于同时限制使用白魔法或首领旗回复统率力，脚本自动停止。")
                return -1
            if use_power_recover_enabled:
                adb_press_and_release(729, 712, adb_path, device_serial)
                return 1
            if not self.refresh_power_legend(package_name, image_folder, adb_path, device_serial,
                                             change_timezone_enabled):
                return -1
            time.sleep(enter_legend_time)
            roll_some_length(adb_path, device_serial, long_roll_length, long_roll_time_ms, long_roll_times)
            roll_and_find_spec_legend_activity(adb_path, device_serial, self.template_name, image_folder,
                                               confidence_threshold=self.find_activity_confidence)
            return 1
        return 0

    def refresh_power_legend(self, package_name, image_folder, adb_path, device_serial, change_timezone_enabled):
        refresh_power(self.driver, package_name, image_folder, adb_path, device_serial, is_legend=True)
        if not self.timezone_block(change_timezone_enabled, adb_path, device_serial):
            return False
        if not click_press_and_release(adb_path, device_serial, "start_game", image_folder, confidence_threshold=0.7):
            return False
        return True

    def _handle_post_battle(self, options, adb_path, device_serial, image_folder, package_name):
        pass

    def run(self, options):
        server = options.get('server')
        try:
            max_loops = int(options.get('max_loops', 1000))
        except (ValueError, TypeError):
            max_loops = 0
        adb_path = options.get('adb_path')
        device_serial = options.get('device_serial')
        refresh_power_enabled = options.get('refresh_power_enabled', True)
        use_power_recover_enabled = options.get('use_power_recover_enabled', False)
        change_timezone_enabled = options.get('change_timezone_enabled', True)
        long_roll_times = int(options.get('long_roll_times', long_roll_counts))
        position_order = options.get('position_order', legend_positions_order_default)
        if not isinstance(position_order, list):
            position_order = legend_positions_order_default

        if server == '台服':
            package_name = "jp.co.ponos.battlecatstw"
            image_folder = "images_tw/"
        else:
            package_name = "jp.co.ponos.battlecats"
            image_folder = "images_jp/"

        self.log(f"脚本 '{self.get_name()}' 已启动。")
        self.log(f"配置: 服务器={server}, 最大轮数={max_loops if max_loops > 0 else '无限'}")
        specific_options_log = []
        for key, val in options.items():
            if key not in ['server', 'max_loops', 'adb_path', 'device_serial']:
                specific_options_log.append(
                    f"{key}={'开启' if isinstance(val, bool) and val else ('关闭' if isinstance(val, bool) and not val else val)}")
        self.log(f"专属配置: {', '.join(specific_options_log)}")

        i = 0
        time_start = datetime.now()

        if not self.timezone_block(change_timezone_enabled, adb_path, device_serial):
            return "STOPPED"
        if not click_press_and_release(adb_path, device_serial, "start_game", image_folder, confidence_threshold=0.7):
            return "STOPPED"

        time.sleep(enter_legend_time)
        roll_some_length(adb_path, device_serial, long_roll_length, long_roll_time_ms, long_roll_times)
        roll_and_find_spec_legend_activity(adb_path, device_serial, self.template_name, image_folder,
                                           confidence_threshold=self.find_activity_confidence)

        while not self.is_stop_requested():
            if 0 < max_loops <= i:
                recover_time_zone(adb_path, device_serial, g_original_timezone)
                self.log(f"\n已完成设定的 {max_loops} 轮任务，脚本自动停止。")
                return "COMPLETED"

            self.log("-" * 30)
            self.log(f"第 {i + 1} 轮开始...")
            time_delta = datetime.now() - time_start
            deltaH, rem = divmod(time_delta.seconds, 3600)
            deltaM, deltaS = divmod(rem, 60)
            self.log(f"已运行: {time_delta.days}天 {deltaH:02d}时 {deltaM:02d}分 {deltaS:02d}秒")

            try:
                while not self.is_stop_requested():
                    timeout = datetime.now() + timedelta(seconds=15)
                    while not if_image_on_screen(adb_path, device_serial, "start_fight_map", image_folder,
                                                 confidence_threshold=0.7):
                        if datetime.now() > timeout:
                            break
                        time.sleep(0.5)
                    adb_press_and_release(1627, 765, adb_path, device_serial)

                    status = self.detect_legend_act_timeout(adb_path, device_serial, image_folder,
                                                            change_timezone_enabled, long_roll_times,
                                                            timing="start_fight")
                    if status == -1: return "STOPPED"
                    if status == 1: break

                    status = self.detect_legend_refresh_power(adb_path, device_serial, image_folder, package_name,
                                                              refresh_power_enabled, use_power_recover_enabled,
                                                              change_timezone_enabled, long_roll_times)
                    if status == -1: return "STOPPED"
                    if status == 1: continue

                    positions_to_tap = ordered_fight_strategy(position_order)
                    while not if_image_on_screen(adb_path, device_serial, "return_map", image_folder,
                                                 confidence_threshold=0.7):
                        if self.is_stop_requested():
                            break
                        tap_cats_in_fight(positions_to_tap, adb_path, device_serial)

                    self._handle_post_battle(options, adb_path, device_serial, image_folder, package_name)

                    adb_press_and_release(1861, 57, adb_path, device_serial)
                    adb_press_and_release(1861, 57, adb_path, device_serial)
                    adb_press_and_release(1861, 57, adb_path, device_serial)
                    time.sleep(1)

                    i += 1

                    status = self.detect_legend_act_timeout(adb_path, device_serial, image_folder,
                                                            change_timezone_enabled, long_roll_times,
                                                            timing="return_map")
                    if status == -1: return "STOPPED"
                    if status == 1: break
                    break
            except Exception as e:
                print(f"错误发生: {e}")

        recover_time_zone(adb_path, device_serial, g_original_timezone)
        self.log("脚本因用户请求而停止。")
        return "STOPPED"
