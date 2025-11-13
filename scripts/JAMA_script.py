# scripts/JAMA_script.py
import time
import threading
from datetime import datetime, timedelta
from .base_script import ScriptBase

from common.ScreenCaptureManager import ScreenCaptureManager as SCM
from common.utils import (
    if_image_on_screen,
    if_image_on_screen_GDI,
    increment_today_count,
    refresh_time_rapid,
    adb_press_and_release,
    get_visible_window_titles
)


class JamaScript(ScriptBase):

    @staticmethod
    def get_name():
        return "加码多多 -- 压榨加码多多"

    @staticmethod
    def get_description():
        return ("通过修改系统时间来重复领取 【加码多多】 奖励。\n        "
                "请首先开启【防火墙】并启用一次【单次刷新统率力】（在【常用功能】中可启用）\n        "
                "请在【单次刷新统率力】后不要进入任何其它界面，直接进入加码多多\n        "
                "请在加码多多页面选好想刷的区域，之后停留在【是】出发前or不选择区域（脚本将自动选择【重复探险】）")

    @staticmethod
    def get_configurable_options():
        window_titles = get_visible_window_titles()

        default_title = ""
        if window_titles:
            default_title = window_titles[0]  # 默认选第一个
            for title in window_titles:
                # 尝试找到一个更可能是模拟器的标题作为默认选项
                if '雷电模拟器' in title or 'MuMu' in title or '夜神' in title:
                    default_title = title
                    break
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
            },
            {
                'name': 'window_title',
                'label': '模拟器窗口标题 (高效模式)',
                'type': 'choice',  # 改为下拉选择
                'default': default_title,
                'options': window_titles  # 将获取到的列表作为选项
            }
        ]

    @staticmethod
    def get_task_specific_options():
        return [
            {
                'name': 'kill_members_enabled',
                'label': '开启自动踢除队员',
                'type': 'checkbutton',
                'default': False
            },
            {
                'name': 'run_mod',
                'label': '运行模式',
                'type': 'choice',
                'options': ['兼容', '高效（兼容问题 & 潜在bug）'],
                'default': '兼容'
            }
        ]

    def kill_all_members_adb(self, image_folder, adb_path, device_serial):
        member_coords = if_image_on_screen(adb_path, device_serial, "member", image_folder, confidence_threshold=0.7)
        if member_coords:
            adb_press_and_release(member_coords[0], member_coords[1], adb_path, device_serial)
            time.sleep(0.25)
            adb_press_and_release(385, 747, adb_path, device_serial)
            time.sleep(0.25)
            adb_press_and_release(712, 773, adb_path, device_serial)
            time.sleep(0.25)
            adb_press_and_release(712, 773, adb_path, device_serial)

    def kill_all_members_gdi(self, capture_manager, image_folder, adb_path, device_serial):
        member_coords = if_image_on_screen_GDI(capture_manager, "member", image_folder, confidence_threshold=0.7)
        if member_coords:
            adb_press_and_release(member_coords[0], member_coords[1], adb_path, device_serial)
            time.sleep(0.25)
            adb_press_and_release(385, 747, adb_path, device_serial)
            time.sleep(0.25)
            adb_press_and_release(712, 773, adb_path, device_serial)
            time.sleep(0.25)
            adb_press_and_release(712, 773, adb_path, device_serial)

    def run(self, options):
        server = options['server']
        try:
            max_loops = int(options['max_loops'])
        except ValueError:
            max_loops = 0

        adb_path = options.get('adb_path')
        device_serial = options.get('device_serial')
        window_title = options.get('window_title')
        kill_members_enabled = options.get('kill_members_enabled', False)
        run_mod = options.get('run_mod', '兼容')

        if server == '台服':
            image_folder = "images_tw/"
        else:
            image_folder = "images_jp/"

        self.log(f"脚本 '{self.get_name()}' 已启动。")
        self.log(f"配置: 服务器={server}, 最大轮数={max_loops if max_loops > 0 else '无限'}")
        self.log(f"专属配置: 踢除队员={'开启' if kill_members_enabled else '关闭'}, 运行模式={run_mod}")

        capture_manager = None
        if run_mod == '高效（兼容问题 & 潜在bug）':
            if not window_title:
                self.log("[错误] 高效模式需要配置 '模拟器窗口标题'。")
                return "FAILED"
            try:
                capture_manager = SCM(window_title, log_callback=self.log)
                capture_manager.start()
                time.sleep(0.5)
                if capture_manager.get_latest_frame() is None:
                    self.log("错误：无法捕获到第一帧截图。请确保模拟器在前台且窗口标题正确。")
                    if capture_manager:
                        capture_manager.stop()
                    return "FAILED"
            except ValueError as e:
                self.log(f"[致命错误] 无法启动截图管理器: {e}")
                return "FAILED"

        i = 0
        time_start = datetime.now()
        single_time_start = datetime.now()

        try:
            while not self.is_stop_requested():
                single_time_usage = datetime.now() - single_time_start
                self.log(f"第 {i} 轮消耗时间 : {single_time_usage}")
                single_time_start = datetime.now()

                if 0 < max_loops <= i:
                    time_delta = datetime.now() - time_start
                    deltaH, rem = divmod(time_delta.seconds, 3600)
                    deltaM, deltaS = divmod(rem, 60)
                    self.log(f"本任务耗时: {time_delta.days}天 {deltaH:02d}时 {deltaM:02d}分 {deltaS:02d}秒")
                    self.log(f"\n已完成设定的 {max_loops} 轮任务，脚本自动停止。")
                    return "COMPLETED"

                if kill_members_enabled and (i % 2 == 0):
                    if run_mod == '兼容':
                        self.kill_all_members_adb(image_folder, adb_path, device_serial)
                    else:
                        self.kill_all_members_gdi(capture_manager, image_folder, adb_path, device_serial)

                # timeout = datetime.now() + timedelta(seconds=1)
                # while datetime.now() < timeout and not self.is_stop_requested():
                #     adb_press_and_release(1852, 155, adb_path, device_serial)

                found_yes = False
                timeout = datetime.now() + timedelta(seconds=10)
                if run_mod == '兼容':
                    while datetime.now() < timeout and not self.is_stop_requested():
                        found = if_image_on_screen(adb_path, device_serial, "YES", image_folder,
                                                   confidence_threshold=0.8)

                        if found:
                            if server == '台服':
                                adb_press_and_release(685, 730, adb_path, device_serial)
                                time.sleep(0.25)
                                adb_press_and_release(685, 730, adb_path, device_serial)
                            elif server == '日服':
                                adb_press_and_release(723, 740, adb_path, device_serial)
                                time.sleep(0.25)
                                adb_press_and_release(723, 740, adb_path, device_serial)
                            found_yes = True
                            break
                        else:
                            adb_press_and_release(1852, 155, adb_path, device_serial)
                else:
                    while datetime.now() < timeout and not self.is_stop_requested():
                        found = if_image_on_screen_GDI(capture_manager, "YES", image_folder, confidence_threshold=0.8)

                        if found:
                            if server == '台服':
                                adb_press_and_release(685, 730, adb_path, device_serial)
                                time.sleep(0.25)
                                adb_press_and_release(685, 730, adb_path, device_serial)
                            elif server == '日服':
                                adb_press_and_release(723, 740, adb_path, device_serial)
                                time.sleep(0.25)
                                adb_press_and_release(723, 740, adb_path, device_serial)
                            found_yes = True
                            break
                        else:
                            adb_press_and_release(1852, 155, adb_path, device_serial)

                if not found_yes:
                    self.log(f"警告: '{run_mod}' 模式下10秒内未找到'YES'按钮。")

                refresh_time_rapid(adb_path, device_serial)

                time.sleep(0.05)
                adb_press_and_release(1600, 146, adb_path, device_serial)
                time.sleep(0.05)
                adb_press_and_release(1600, 155, adb_path, device_serial)
                time.sleep(0.05)
                adb_press_and_release(1600, 155, adb_path, device_serial)
                time.sleep(0.05)
                adb_press_and_release(1600, 155, adb_path, device_serial)
                time.sleep(0.05)
                adb_press_and_release(1600, 155, adb_path, device_serial)
                time.sleep(0.05)
                adb_press_and_release(1600, 155, adb_path, device_serial)

                time.sleep(2)

                found_reward = False
                timeout = datetime.now() + timedelta(seconds=10)
                if run_mod == '兼容':
                    while datetime.now() < timeout:
                        found = if_image_on_screen(adb_path, device_serial, "rego", image_folder,
                                                   confidence_threshold=0.5)
                        if found:
                            adb_press_and_release(1450, 155, adb_path, device_serial)
                            found_reward = True
                            break
                        else:
                            adb_press_and_release(1450, 155, adb_path, device_serial)
                else:
                    while datetime.now() < timeout:
                        found = if_image_on_screen_GDI(capture_manager, "rego", image_folder,
                                                       confidence_threshold=0.5)
                        # found = if_image_on_screen_GDI(capture_manager, "reward_result", image_folder,
                        #                                confidence_threshold=0.7)
                        if found:
                            adb_press_and_release(1450, 155, adb_path, device_serial)
                            found_reward = True
                            break
                        else:
                            adb_press_and_release(1450, 155, adb_path, device_serial)

                if not found_reward:
                    self.log(f"警告: '{run_mod}' 模式下10秒内未找到'rego/reward_result'按钮。")

                # timeout = datetime.now() + timedelta(seconds=2)
                # while datetime.now() < timeout and not self.is_stop_requested():
                #     adb_press_and_release(1450, 155, adb_path, device_serial)

                i += 1
                increment_today_count(self.get_name())

        finally:
            if capture_manager:
                capture_manager.stop()

            if self.is_stop_requested():
                self.log("脚本因用户请求而停止。")
                return "STOPPED"

        return "COMPLETED"
