import importlib
import inspect
import json
import os
import re
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from queue import Queue
from tkinter import ttk, scrolledtext, Menu, font, messagebox, Toplevel

from appium import webdriver
from appium.options.android import UiAutomator2Options

from common.utils import resource_path, get_today_count, refresh_power, start_appium, stop_appium, \
    calculate_activity_earliest_timezone_value, change_time_zone, recover_time_zone, week_day_kv, \
    activities_start_kv, run_adb_command, TIMEZONE_KEYS, g_original_timezone, handle_timezone_key
from scripts.base_script import ScriptBase


class App:
    device_serial = None
    device_ver = None

    app_package = "jp.co.ponos.battlecatstw"
    app_activity = "jp.co.ponos.battlecatstw.MyActivity"

    capabilities = {
        "platformName": "Android",
        "automationName": "UiAutomator2",
        "platformVersion": device_ver,
        "deviceName": device_serial,
        "packageName": app_package,
        "appActivity": app_activity,
        "noReset": True,
        "appium:skipDeviceInitialization": True,
        "appium:newCommandTimeout": 3600
    }

    ports_to_check = [16384, 62001]

    def __init__(self, root):
        self.root = root
        self.root.title("Hanbly猫战工具集 ver2.1.2")
        self.root.geometry("800x900")

        self.adb_path = resource_path(os.path.join("PortableAppium", "platform-tools", "adb.exe"))
        self.running_emulators = {}
        self.name_to_serial_map = {}

        self.scripts = {}
        self.stop_event = threading.Event()
        self.driver = None
        self.log_queue = Queue()
        self.script_settings = {}
        self.current_script_class = None
        self.common_option_vars = {}
        self.specific_option_vars = {}

        self.config_dir = "configs"
        self.ensure_config_dir()

        self.setup_ui()
        self.load_scripts()
        self.populate_script_selector()
        self.process_log_queue()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.after(100, self.initial_emulator_check)

    def initial_emulator_check(self):
        emulators_dict = self.find_running_emulators()
        self.update_emulator_selector(emulators_dict)
        if not emulators_dict:
            messagebox.showwarning("提示", "当前未检测到已连接的安卓设备或模拟器。\n请开启后点击[刷新列表]重试。")

    def find_running_emulators(self):
        if not os.path.exists(self.adb_path):
            self.log_message(f"[错误] adb.exe 未在预期路径找到: {self.adb_path}")
            return {}

        self.log_message("正在准备ADB环境...")
        try:
            run_adb_command(self.adb_path, None, "kill-server")
            run_adb_command(self.adb_path, None, "start-server")
            time.sleep(1)
            self.log_message("ADB服务已重启。")
        except Exception as e:
            self.log_message(f"重启ADB服务失败: {e}，将尝试继续...")

        self.log_message("正在尝试连接常见模拟器端口...")
        for port in self.ports_to_check:
            run_adb_command(self.adb_path, None, f"connect 127.0.0.1:{port}")

        found_emulators = {}
        try:
            self.log_message("正在执行 'adb devices' 扫描设备...")
            output = run_adb_command(self.adb_path, None, "devices")
            self.log_message(f"--- adb devices 输出 ---\n{output}\n--------------------------")

            lines = output.strip().split('\n')[1:]
            active_devices = []
            for line in lines:
                parts = line.strip().split()
                if len(parts) == 2 and parts[1] == 'device':
                    serial = parts[0]
                    active_devices.append(serial)

            if not active_devices:
                self.log_message("未检测到任何处于 'device' 状态的设备。")
                return {}

            self.log_message(f"发现 {len(active_devices)} 个活动设备，正在获取详细信息...")

            for serial in active_devices:
                try:
                    model_cmd = "shell getprop ro.product.model"
                    brand_cmd = "shell getprop ro.product.brand"
                    version_cmd = "shell getprop ro.build.version.release"

                    model = run_adb_command(self.adb_path, serial, model_cmd).strip()
                    brand_prop = run_adb_command(self.adb_path, serial, brand_cmd).strip()
                    version = run_adb_command(self.adb_path, serial, version_cmd).strip()

                    brand_display = "未知设备"
                    if "leidian" in model.lower() or "ldplayer" in model.lower():
                        brand_display = "雷电模拟器"
                    elif "mumu" in model.lower() or "netease" in model.lower():
                        brand_display = "MuMu模拟器"
                    elif "nox" in model.lower():
                        brand_display = "夜神模拟器"
                    elif "samsung" in brand_prop.lower() or serial.startswith("127.0.0.1"):
                        brand_display = "MuMu模拟器"
                    elif serial.startswith("emulator-"):
                        brand_display = "雷电模拟器"

                    friendly_name = f"{brand_display} (型号:{model}) - 安卓 {version}"

                    found_emulators[serial] = {
                        "friendly_name": friendly_name,
                        "version": version
                    }
                    self.log_message(f"  -> 识别成功: {serial} -> {friendly_name}")

                except Exception as e:
                    found_emulators[serial] = {
                        "friendly_name": f"设备 ({serial}) - 查询信息失败",
                        "version": None
                    }
                    self.log_message(f"  -> 查询设备 {serial} 详细信息失败: {e}")

        except Exception as e:
            self.log_message(f"通过ADB查找设备失败: {e}")

        return found_emulators

    def update_emulator_selector(self, emulators_dict):
        self.running_emulators = emulators_dict
        self.name_to_serial_map = {v["friendly_name"]: k for k, v in emulators_dict.items()}
        friendly_names = list(self.name_to_serial_map.keys())
        current_friendly_selection = self.emulator_selector.get()
        self.emulator_selector['values'] = friendly_names

        if friendly_names:
            if current_friendly_selection in friendly_names:
                self.emulator_selector.set(current_friendly_selection)
            else:
                self.emulator_selector.set(friendly_names[0])
            self.on_emulator_selected()
        else:
            self.emulator_selector.set('')
            self.device_serial = None
            self.device_ver = None

    def on_emulator_selected(self, event=None):
        selected_name = self.emulator_selector.get()
        if not selected_name:
            return

        selected_serial = self.name_to_serial_map.get(selected_name)

        if selected_serial and selected_serial in self.running_emulators:
            device_info = self.running_emulators[selected_serial]
            self.device_ver = device_info["version"]
            self.device_serial = selected_serial

            self.capabilities["deviceName"] = self.device_serial
            self.capabilities["platformVersion"] = self.device_ver

            self.log_message(f"已切换目标设备: {selected_name}")
        else:
            self.log_message(f"切换设备失败：无法找到 {selected_name} 的详细信息。")
            self.device_serial = None
            self.device_ver = None

    def setup_ui(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        sys_functions_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="系统操作", menu=sys_functions_menu)
        sys_functions_menu.add_command(label="启动appium服务", command=start_appium)
        sys_functions_menu.add_command(label="终止appium服务", command=lambda: stop_appium(self.log_message))

        functions_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="常用功能", menu=functions_menu)
        functions_menu.add_command(label="查看今日统计", command=self.show_daily_count_window)
        functions_menu.add_command(label="单次刷新统率力", command=self.execute_refresh_power)
        functions_menu.add_command(label="查看活动时间段", command=self.show_activity_schedule_window)
        functions_menu.add_command(label="修改当前时区", command=self.show_change_timezone_window)

        config_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="配置选项", menu=config_menu)
        config_menu.add_command(label="打开统一配置窗口", command=self.open_unified_config_window)

        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        emulator_frame = ttk.LabelFrame(main_frame, text="〇、选择设备 (模拟器)", padding=(10, 5))
        emulator_frame.pack(fill=tk.X, pady=(0, 10))

        selector_frame = ttk.Frame(emulator_frame)
        selector_frame.pack(fill=tk.X, expand=True, pady=2)
        ttk.Label(selector_frame, text="设备列表:").pack(side=tk.LEFT, padx=(0, 5))
        self.emulator_selector = ttk.Combobox(selector_frame, state="readonly")
        self.emulator_selector.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.emulator_selector.bind("<<ComboboxSelected>>", self.on_emulator_selected)

        refresh_button = ttk.Button(selector_frame, text="刷新列表", command=self.initial_emulator_check)
        refresh_button.pack(side=tk.LEFT, padx=(5, 0))

        script_frame = ttk.LabelFrame(main_frame, text="一、选择脚本", padding=(10, 5))
        script_frame.pack(fill=tk.X, pady=(0, 10))
        self.script_selector = ttk.Combobox(script_frame, state="readonly", width=30, font=("Helvetica", 10))
        self.script_selector.pack(fill=tk.X, expand=True)
        self.script_selector.bind("<<ComboboxSelected>>", self.on_script_selected)
        self.script_desc_label = ttk.Label(script_frame, text="请先选择一个脚本...", wraplength=680, justify=tk.LEFT)
        self.script_desc_label.pack(fill=tk.X, pady=(5, 0))

        self.options_frame = ttk.LabelFrame(main_frame, text="二、脚本配置", padding=(10, 5))
        self.options_frame.pack(fill=tk.X, pady=(0, 10))
        self.common_options_frame = ttk.LabelFrame(self.options_frame, text="通用配置", padding=(10, 5))
        self.common_options_frame.pack(fill=tk.X, padx=5, pady=5)
        self.specific_options_frame = ttk.LabelFrame(self.options_frame, text="任务专属配置", padding=(10, 5))
        self.specific_options_frame.pack(fill=tk.X, padx=5, pady=5)

        control_frame = ttk.LabelFrame(main_frame, text="三、运行脚本", padding=(10, 5))
        control_frame.pack(fill=tk.BOTH, expand=True)

        self.run_button = ttk.Button(control_frame, text="开始运行", command=self.start_script_thread,
                                     state=tk.DISABLED)
        self.run_button.pack(pady=(0, 5))

        self.console_output = scrolledtext.ScrolledText(control_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.console_output.pack(expand=True, fill=tk.BOTH)

    def log_message(self, message):
        self.log_queue.put(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def process_log_queue(self):
        try:
            while not self.log_queue.empty():
                message = self.log_queue.get_nowait()
                self.console_output.insert(tk.END, message + '\n')
                self.console_output.see(tk.END)
        finally:
            self.root.after(100, self.process_log_queue)

    def load_scripts(self):
        scripts_dir_fs_path = resource_path("scripts")
        if not os.path.isdir(scripts_dir_fs_path):
            self.log_message(f"错误: 脚本目录不存在于 {scripts_dir_fs_path}")
            return
        app_root_path = os.path.dirname(scripts_dir_fs_path)
        if app_root_path not in sys.path:
            sys.path.insert(0, app_root_path)
        for root_dir, _, files in os.walk(scripts_dir_fs_path):
            for filename in files:
                if filename.endswith(".py") and filename not in ["__init__.py", "base_script.py"]:
                    full_file_path = os.path.join(root_dir, filename)
                    relative_path = os.path.relpath(full_file_path, app_root_path)
                    module_path_no_ext = os.path.splitext(relative_path)[0]
                    module_name = module_path_no_ext.replace(os.path.sep, '.')
                    try:
                        module = importlib.import_module(module_name)
                        for _, obj in inspect.getmembers(module, inspect.isclass):
                            if issubclass(obj, ScriptBase) and obj is not ScriptBase:
                                script_name = obj.get_name()
                                if script_name:
                                    self.scripts[script_name] = obj
                    except Exception as e:
                        self.log_message(f"加载模块 {module_name} 失败: {e}")

    def populate_script_selector(self):
        script_names = sorted(list(self.scripts.keys()))
        self.script_selector['values'] = script_names
        if script_names:
            self.script_selector.current(0)
            self.on_script_selected(None)

    def on_script_selected(self, event):
        script_name = self.script_selector.get()
        self.current_script_class = self.scripts.get(script_name)
        if not self.current_script_class:
            self.run_button.config(state=tk.DISABLED)
            return
        self.script_desc_label.config(text=f"描述: {self.current_script_class.get_description()}")
        self.load_and_merge_script_settings(script_name)
        self.rebuild_all_option_ui()
        self.run_button.config(state=tk.NORMAL)

    def load_and_merge_script_settings(self, script_name):
        script_class = self.scripts[script_name]
        defaults = {}
        for option_def in script_class.get_configurable_options():
            defaults[option_def['name']] = option_def.get('default')
        for option_def in script_class.get_task_specific_options():
            defaults[option_def['name']] = option_def.get('default')
        loaded_settings = self.load_settings_from_file(script_name)
        final_settings = {**defaults, **loaded_settings}
        self.script_settings[script_name] = final_settings

    def rebuild_all_option_ui(self):
        for frame in [self.common_options_frame, self.specific_options_frame]:
            for widget in frame.winfo_children():
                widget.destroy()
        self.common_option_vars.clear()
        self.specific_option_vars.clear()
        if not self.current_script_class:
            return
        for option_def in self.current_script_class.get_configurable_options():
            self.create_option_widget(self.common_options_frame, option_def, self.common_option_vars)
        specific_options_def = self.current_script_class.get_task_specific_options()
        if not specific_options_def:
            self.specific_options_frame.pack_forget()
        else:
            self.specific_options_frame.pack(fill=tk.X, padx=5, pady=5)
            for option_def in specific_options_def:
                self.create_option_widget(self.specific_options_frame, option_def, self.specific_option_vars)

    def _update_setting_from_ui(self, script_name, option_name, var):
        if script_name in self.script_settings:
            try:
                self.script_settings[script_name][option_name] = var.get()
            except tk.TclError:
                pass

    def create_option_widget(self, parent_frame, option_def, var_dict):
        script_name = self.current_script_class.get_name()
        current_settings = self.script_settings.get(script_name, {})
        name, label, opt_type = option_def['name'], option_def['label'], option_def['type']
        current_val = current_settings.get(name, option_def.get('default'))
        frame = tk.Frame(parent_frame)
        frame.pack(fill=tk.X, pady=2, padx=5)
        ttk.Label(frame, text=f"{label}:", width=35, anchor='w').pack(side=tk.LEFT)
        widget, var = None, None
        if opt_type == 'entry':
            var = tk.StringVar(value=current_val)
            widget = ttk.Entry(frame, textvariable=var)
        elif opt_type == 'choice':
            var = tk.StringVar(value=current_val)
            widget = ttk.Combobox(frame, textvariable=var, values=option_def.get('options', []), state="readonly")
        elif opt_type == 'checkbutton':
            var = tk.BooleanVar(value=current_val)
            widget = ttk.Checkbutton(frame, variable=var)
        elif opt_type in ['multicheck', 'ordered_multicheck']:
            sub_frame = ttk.Frame(frame)
            button_text = "点击设置"
            if isinstance(current_val, list):
                count = len(current_val)
                button_text = f"点击设置 - 已选 {count} 项"
                if opt_type == 'ordered_multicheck' and current_val:
                    display_list = [str(x) for x in current_val]
                    if len(display_list) > 5:
                        display_text = ' -> '.join(display_list[:5]) + '...'
                    else:
                        display_text = ' -> '.join(display_list)
                    button_text = f"点击设置\n顺序: {display_text}"
            widget = ttk.Button(sub_frame, text=button_text, command=self.open_unified_config_window)
            widget.pack(side=tk.LEFT)
        if widget:
            if opt_type not in ['multicheck', 'ordered_multicheck']:
                widget.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            else:
                sub_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        if var:
            var.trace_add("write",
                          lambda *args, sn=script_name, on=name, v=var: self._update_setting_from_ui(sn, on, v))
            var_dict[name] = var

    def start_script_thread(self):
        if not self.device_serial:
            messagebox.showerror("错误", "未选择任何设备，请先从顶部下拉列表中选择一个设备。")
            return
        self.stop_event.clear()
        self.run_button.config(text="停止运行", command=self.request_stop)
        self.script_selector.config(state=tk.DISABLED)
        script_name = self.current_script_class.get_name()
        final_options = self.script_settings.get(script_name, {}).copy()
        final_options['adb_path'] = self.adb_path
        final_options['device_serial'] = self.device_serial
        thread = threading.Thread(target=self.run_script_logic, args=(self.current_script_class, final_options),
                                  daemon=True)
        thread.start()

    def request_stop(self):
        self.log_message("收到停止请求，将在当前操作后安全退出...")
        self.stop_event.set()
        self.run_button.config(state=tk.DISABLED, text="正在停止...")

    def script_finished(self):
        self.run_button.config(state=tk.NORMAL, text="开始运行", command=self.start_script_thread)
        self.script_selector.config(state="readonly")
        if self.driver:
            try:
                self.driver.quit()
                self.log_message("Appium driver已安全关闭。")
            except Exception as e:
                self.log_message(f"关闭driver时出错: {e}")
            self.driver = None
        self.log_message("任务已结束。")

    def run_script_logic(self, script_class, options):
        server = options.get('server')
        if server == '台服':
            self.capabilities['packageName'] = "jp.co.ponos.battlecatstw"
        elif server == '日服':
            self.capabilities['packageName'] = "jp.co.ponos.battlecats"

        selected_name = "Unknown Device"
        if self.device_serial in self.running_emulators:
            selected_name = self.running_emulators[self.device_serial].get("friendly_name", self.device_serial)

        try:
            self.log_message(f"正在连接 Appium 服务器, 目标设备: {selected_name} (安卓 {self.device_ver})...")
            appium_options = UiAutomator2Options().load_capabilities(self.capabilities)
            self.driver = webdriver.Remote("http://localhost:4723", options=appium_options)
            self.log_message("设备连接成功！")
            script_instance = script_class(self.driver, self.stop_event, self.log_message)
            status = script_instance.run(options)
            self.log_message(f"脚本执行完毕，状态: {status}")
        except Exception as e:
            self.log_message(f"线程发生致命错误: {e}")
            import traceback
            self.log_message(traceback.format_exc())
        finally:
            self.root.after(0, self.script_finished)

    def execute_refresh_power(self):
        if not self.device_serial:
            messagebox.showerror("错误", "未选择设备，无法执行该操作。")
            return
        script_name = self.script_selector.get()
        if not script_name:
            messagebox.showerror("错误", "请先选择一个脚本以确定服务器配置。")
            return
        current_settings = self.script_settings.get(script_name, {})
        server = current_settings.get('server')
        if not server:
            messagebox.showerror("错误", "当前脚本配置中未找到服务器信息。")
            return
        local_caps = self.capabilities.copy()
        if server == '台服':
            local_caps['packageName'], image_folder = "jp.co.ponos.battlecatstw", "images_tw/"
        elif server == '日服':
            local_caps['packageName'], image_folder = "jp.co.ponos.battlecats", "images_jp/"
        else:
            return
        thread = threading.Thread(target=self._execute_refresh_power_task, args=(local_caps, image_folder), daemon=True)
        thread.start()

    def _execute_refresh_power_task(self, caps, image_folder):
        temp_driver = None
        selected_name = "Unknown Device"
        device_serial_for_task = caps.get("deviceName")
        if device_serial_for_task in self.running_emulators:
            selected_name = self.running_emulators[device_serial_for_task].get("friendly_name", device_serial_for_task)

        try:
            self.log_message(f"临时连接 Appium ({selected_name})...")
            appium_options = UiAutomator2Options().load_capabilities(caps)
            temp_driver = webdriver.Remote("http://localhost:4723", options=appium_options)
            self.log_message("临时连接成功！")
            refresh_power(temp_driver, caps['packageName'], image_folder, self.adb_path, self.device_serial,
                          app_default=True)
        except Exception as e:
            self.log_message(f"刷新统率力时出错: {e}")
            import traceback
            self.log_message(traceback.format_exc())
        finally:
            if temp_driver:
                temp_driver.quit()
                self.log_message("临时Appium driver已关闭。")

    def show_daily_count_window(self):
        script_name = self.script_selector.get()
        if not script_name:
            messagebox.showinfo("提示", "请先在下拉列表中选择一个脚本。")
            return
        count_window = Toplevel(self.root)
        count_window.title("今日统计")
        count_window.geometry("400x250")
        count_window.transient(self.root)
        count_window.grab_set()
        count = get_today_count(script_name)
        today_str = datetime.now().strftime('%Y-%m-%d')
        label_font = font.Font(family="Helvetica", size=14)
        info_text = f"日期: {today_str}\n\n今日已完成总轮数: {count}"
        info_label = tk.Label(count_window, text=info_text, font=label_font, pady=20)
        info_label.pack(expand=True)
        close_button = ttk.Button(count_window, text="关闭", command=count_window.destroy)
        close_button.pack(pady=10)

    def show_change_timezone_window(self):
        if not self.device_serial:
            messagebox.showerror("错误", "未选择设备，无法执行时区操作。")
            return
        window = Toplevel(self.root)
        window.title("时区修改")
        window.geometry("800x500")
        window.transient(self.root)
        window.grab_set()
        main_frame = ttk.Frame(window, padding="15")
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        left_frame = ttk.Frame(main_frame, padding="10")
        left_frame.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(0, 10))
        right_frame = ttk.Frame(main_frame, padding="10")
        right_frame.grid(row=0, column=1, rowspan=2, sticky="nsew")
        right_frame.grid_rowconfigure(2, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)
        bottom_frame = ttk.Frame(main_frame, padding="10")
        bottom_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        schedule_text = tk.Text(right_frame, wrap="word", height=10, font=("Helvetica", 10), borderwidth=1,
                                relief="solid", background="#ffffff")
        schedule_text.grid(row=2, column=0, sticky="nsew")
        schedule_text.tag_configure("highlight", background="#FFDDDD")
        schedule_text.config(state="disabled")
        status_label = ttk.Label(bottom_frame, text="请先选择一个时区")
        status_label.pack(side="left", padx=15, fill="x", expand=True)
        ttk.Label(left_frame, text="跳转至:", style="Header.TLabel").pack(pady=(0, 5), anchor='w')
        timezone_names = [tz for tz in TIMEZONE_KEYS]
        timezone_combo = ttk.Combobox(left_frame, values=timezone_names, state="readonly", width=30)
        timezone_combo.pack(pady=(0, 10), fill='x')
        jump_btn = ttk.Button(bottom_frame, text="点击跳转")
        jump_btn.pack(side="left", padx=5)
        restore_btn = ttk.Button(bottom_frame, text="恢复时区")
        restore_btn.pack(side="right", padx=5)

        def update_schedule_display(event=None):
            timezone_name = timezone_combo.get()
            if not timezone_name:
                return
            schedule_text.config(state="normal")
            schedule_text.delete("1.0", tk.END)
            schedule_text.tag_remove("highlight", "1.0", tk.END)
            header_font = font.Font(family="Helvetica", size=10, weight="bold")
            schedule_text.tag_configure("header", font=header_font)
            schedule_text.config(state="disabled")
            status_label.config(text=f"已选择: “{timezone_name}”", foreground="black")

        def handle_jump_timezone():
            jump_to = timezone_combo.get()
            jump_to = handle_timezone_key(jump_to)
            if not jump_to or not jump_to.strip():
                status_label.config(text="跳转失败：未选择时区。", foreground="red")
                return
            status_label.config(text=f"正在跳转至 {jump_to}...", foreground="blue")
            window.update_idletasks()
            success = change_time_zone(self.adb_path, self.device_serial, jump_to)
            status_label.config(text=f"已跳转至: {jump_to}" if success else "跳转失败！",
                                foreground="green" if success else "red")

        def handle_restore_timezone():
            restore_timezone = g_original_timezone
            if not restore_timezone or not restore_timezone.strip():
                status_label.config(text="恢复失败：未获取到原始时区。", foreground="red")
                return
            status_label.config(text=f"正在恢复至 {restore_timezone}...", foreground="blue")
            window.update_idletasks()
            success = recover_time_zone(self.adb_path, self.device_serial, restore_timezone)
            status_label.config(text=f"已恢复至: {restore_timezone}" if success else "恢复失败！",
                                foreground="green" if success else "red")

        timezone_combo.bind("<<ComboboxSelected>>", update_schedule_display)
        jump_btn.config(command=handle_jump_timezone)
        restore_btn.config(command=handle_restore_timezone)

    def show_activity_schedule_window(self):
        if not self.device_serial:
            messagebox.showerror("错误", "未选择设备，无法执行时区操作。")
            return
        window = Toplevel(self.root)
        window.title("活动时区计算器")
        window.geometry("800x500")
        window.transient(self.root)
        window.grab_set()
        style = ttk.Style(window)
        style.configure("TFrame", background="#f0f0f0")
        style.configure("TLabel", background="#f0f0f0", font=("Helvetica", 10))
        style.configure("Header.TLabel", font=("Helvetica", 12, "bold"))
        main_frame = ttk.Frame(window, padding="15")
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        original_timezone = run_adb_command(self.adb_path, self.device_serial, "shell getprop persist.sys.timezone")
        left_frame = ttk.Frame(main_frame, padding="10")
        left_frame.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(0, 10))
        ttk.Label(left_frame, text="选择活动:", style="Header.TLabel").pack(pady=(0, 5), anchor='w')
        activity_names = [act['act_name'] for act in activities_start_kv]
        activity_combo = ttk.Combobox(left_frame, values=activity_names, state="readonly", width=30)
        activity_combo.pack(pady=(0, 10), fill='x')
        right_frame = ttk.Frame(main_frame, padding="10")
        right_frame.grid(row=0, column=1, rowspan=2, sticky="nsew")
        right_frame.grid_rowconfigure(2, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)
        ttk.Label(right_frame, text="活动时间表", style="Header.TLabel").grid(row=0, column=0, pady=(0, 5), sticky='w')
        ttk.Separator(right_frame, orient='horizontal').grid(row=1, column=0, sticky='ew', pady=(0, 10))
        schedule_text = tk.Text(right_frame, wrap="word", height=10, font=("Helvetica", 10), borderwidth=1,
                                relief="solid", background="#ffffff")
        schedule_text.grid(row=2, column=0, sticky="nsew")
        schedule_text.tag_configure("highlight", background="#FFDDDD")
        schedule_text.config(state="disabled")
        bottom_frame = ttk.Frame(main_frame, padding="10")
        bottom_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        calculate_btn = ttk.Button(bottom_frame, text="计算目标时区")
        calculate_btn.pack(side="left", padx=5)
        jump_btn = ttk.Button(bottom_frame, text="跳转至目标时区")
        jump_btn.pack(side="left", padx=5)
        restore_btn = ttk.Button(bottom_frame, text="恢复时区")
        restore_btn.pack(side="right", padx=5)
        status_label = ttk.Label(bottom_frame, text="请先从左侧选择一个活动")
        status_label.pack(side="left", padx=15, fill="x", expand=True)

        def update_schedule_display(event=None):
            activity_name = activity_combo.get()
            if not activity_name: return
            activity_info = next((act for act in activities_start_kv if act.get('act_name') == activity_name), None)
            if not activity_info: return
            schedule_text.config(state="normal")
            schedule_text.delete("1.0", tk.END)
            schedule_text.tag_remove("highlight", "1.0", tk.END)
            header_font = font.Font(family="Helvetica", size=10, weight="bold")
            schedule_text.tag_configure("header", font=header_font)
            all_days = week_day_kv + [f"Day_{d:02}" for d in range(1, 32)]
            for day_key in all_days:
                if day_key in activity_info and activity_info[day_key]:
                    times = ", ".join(activity_info[day_key])
                    schedule_text.insert(tk.END, f"{day_key}:\n", "header")
                    schedule_text.insert(tk.END, f"  {times}\n\n")
            schedule_text.config(state="disabled")
            status_label.config(text=f"已选择: “{activity_name}”", foreground="black")

        def handle_calculate(jump_after_calc=False):
            activity_name = activity_combo.get()
            if not activity_name or activity_name == "请选择...":
                status_label.config(text="操作失败：请先选择一个活动！", foreground="red")
                return
            status_label.config(text=f"正在计算...", foreground="blue")
            window.update_idletasks()
            timezone, target_dt = calculate_activity_earliest_timezone_value(activity_name, self.adb_path,
                                                                             self.device_serial)
            if timezone and target_dt:
                status_text = f"计算完成！建议时区: {timezone}"
                status_label.config(text=status_text, foreground="green")
                if jump_after_calc:
                    status_label.config(text=f"{status_text} | 正在跳转...", foreground="blue")
                    window.update_idletasks()
                    success = change_time_zone(self.adb_path, self.device_serial, timezone)
                    status_label.config(text=f"时区已跳转至: {timezone}" if success else "时区跳转失败！",
                                        foreground="green" if success else "red")
            else:
                status_label.config(text=f"计算失败: 近期可能无此活动。", foreground="red")

        def handle_restore_timezone():
            if not original_timezone or not original_timezone.strip():
                status_label.config(text="恢复失败：未记录原始时区。", foreground="red")
                return
            status_label.config(text=f"正在恢复至 {original_timezone}...", foreground="blue")
            window.update_idletasks()
            success = recover_time_zone(self.adb_path, self.device_serial, original_timezone)
            status_label.config(text=f"已恢复至: {original_timezone}" if success else "恢复失败！",
                                foreground="green" if success else "red")

        activity_combo.bind("<<ComboboxSelected>>", update_schedule_display)
        calculate_btn.config(command=lambda: handle_calculate(jump_after_calc=False))
        jump_btn.config(command=lambda: handle_calculate(jump_after_calc=True))
        restore_btn.config(command=handle_restore_timezone)
        activity_combo.set("请选择...")
        if not original_timezone or not original_timezone.strip():
            status_label.config(text="警告: 未能获取原始时区", foreground="orange")
            restore_btn.config(state="disabled")
        else:
            status_label.config(text=f"已记录原始时区: {original_timezone}", foreground="gray")

    def open_unified_config_window(self):
        if not self.current_script_class:
            messagebox.showinfo("提示", "请先选择一个脚本。")
            return
        config_window = Toplevel(self.root)
        script_name = self.current_script_class.get_name()
        config_window.title(f"'{script_name}' 统一配置")
        config_window.transient(self.root)
        config_window.grab_set()
        main_frame = ttk.Frame(config_window, padding=20)
        main_frame.pack(expand=True, fill=tk.BOTH)
        temp_vars = {}
        common_defs = self.current_script_class.get_configurable_options()
        if common_defs:
            common_frame = ttk.LabelFrame(main_frame, text="通用配置", padding=10)
            common_frame.pack(fill='x', pady=10)
            for option_def in common_defs:
                self.create_popup_widget(common_frame, option_def, temp_vars)
        specific_defs = self.current_script_class.get_task_specific_options()
        if specific_defs:
            specific_frame = ttk.LabelFrame(main_frame, text="任务专属配置", padding=10)
            specific_frame.pack(fill='x', pady=10)
            for option_def in specific_defs:
                self.create_popup_widget(specific_frame, option_def, temp_vars)

        def save_and_close():
            current_settings = self.script_settings[script_name]
            for name, temp_var in temp_vars.items():
                if name in [opt['name'] for opt in specific_defs if opt['type'] == 'ordered_multicheck']:
                    current_settings[name] = temp_var
                elif isinstance(temp_var, list) and temp_var and isinstance(temp_var[0], tk.BooleanVar):
                    current_settings[name] = [i for i, var in enumerate(temp_var) if var.get()]
                else:
                    current_settings[name] = temp_var.get()
            self.save_settings_to_file(script_name, current_settings)
            self.log_message(f"为'{script_name}'保存了新配置到文件。")
            config_window.destroy()
            self.rebuild_all_option_ui()

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        ttk.Button(button_frame, text="保存并关闭", command=save_and_close).pack(side='left', padx=10)
        ttk.Button(button_frame, text="取消", command=config_window.destroy).pack(side='left', padx=10)

    def create_popup_widget(self, parent_frame, option_def, temp_var_dict):
        script_name = self.current_script_class.get_name()
        current_settings = self.script_settings.get(script_name, {})
        name, label, opt_type = option_def['name'], option_def['label'], option_def['type']
        current_val = current_settings.get(name, option_def.get('default'))

        if opt_type == 'ordered_multicheck':
            frame = tk.Frame(parent_frame)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=f"{label}:", width=30, anchor='w').pack(side=tk.LEFT)
            display_list = [str(x) for x in current_val]
            if len(display_list) > 5:
                display_text = ' -> '.join(display_list[:5]) + '...'
            else:
                display_text = ' -> '.join(display_list)
            btn_text = f"编辑序列 (当前: {display_text})"
            edit_btn = ttk.Button(frame, text=btn_text,
                                  command=lambda n=name, l=label, o=option_def['options'], c=current_val,
                                                 v=temp_var_dict: self.open_sequence_editor(n, l, o, c, v))
            edit_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            temp_var_dict[name] = list(current_val)
            return

        if opt_type == 'multicheck':
            frame = ttk.LabelFrame(parent_frame, text=label, padding=10)
            frame.pack(fill='x', pady=5)
            option_vars = []
            cols = option_def.get('columns', 6)
            for i, opt_label in enumerate(option_def['options']):
                var = tk.BooleanVar(value=(i in (current_val or [])))
                ttk.Checkbutton(frame, text=opt_label, variable=var).grid(row=i // cols, column=i % cols, sticky='w',
                                                                          padx=5, pady=2)
                option_vars.append(var)
            temp_var_dict[name] = option_vars
            return

        frame = tk.Frame(parent_frame)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text=f"{label}:", width=30, anchor='w').pack(side=tk.LEFT)
        var = None
        if opt_type == 'entry':
            var = tk.StringVar(value=current_val)
            ttk.Entry(frame, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        elif opt_type == 'choice':
            var = tk.StringVar(value=current_val)
            ttk.Combobox(frame, textvariable=var, values=option_def.get('options', []), state="readonly").pack(
                side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        elif opt_type == 'checkbutton':
            var = tk.BooleanVar(value=current_val)
            ttk.Checkbutton(frame, variable=var).pack(side=tk.LEFT, padx=5)
        if var:
            temp_var_dict[name] = var

    def open_sequence_editor(self, name, label, options, current_sequence, temp_var_dict):
        editor_window = Toplevel(self.root)
        editor_window.title(f"编辑 - {label}")
        editor_window.transient(self.root)
        editor_window.grab_set()
        sequence_in_editor = list(current_sequence)
        main_frame = ttk.Frame(editor_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        display_frame = ttk.LabelFrame(main_frame, text="当前序列", padding=5)
        display_frame.pack(fill='x', pady=(0, 10))
        sequence_var = tk.StringVar()

        def update_display():
            sequence_var.set(str(sequence_in_editor))

        display_label = ttk.Entry(display_frame, textvariable=sequence_var, state='readonly', font=("Consolas", 12))
        display_label.pack(fill='x', expand=True)
        button_frame = ttk.LabelFrame(main_frame, text="添加单位", padding=10)
        button_frame.pack(fill='x', pady=(0, 10))

        def add_to_sequence(index):
            sequence_in_editor.append(index)
            update_display()

        cols = 6
        for i, opt_label in enumerate(options):
            btn = ttk.Button(button_frame, text=opt_label, command=lambda idx=i: add_to_sequence(idx))
            btn.grid(row=i // cols, column=i % cols, sticky='ew', padx=2, pady=2)
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill='x', pady=(0, 10))

        def delete_last():
            if sequence_in_editor:
                sequence_in_editor.pop()
                update_display()

        def clear_all():
            sequence_in_editor.clear()
            update_display()

        ttk.Button(action_frame, text="删除最后一个", command=delete_last).pack(side='left', padx=5)
        ttk.Button(action_frame, text="清空序列", command=clear_all).pack(side='left', padx=5)
        save_cancel_frame = ttk.Frame(main_frame)
        save_cancel_frame.pack(fill='x', pady=(10, 0))

        def on_save():
            temp_var_dict[name][:] = sequence_in_editor
            editor_window.destroy()
            messagebox.showinfo("已保存", "出喵序列已更新。请关闭并重新打开统一配置窗口以查看更改。", parent=self.root)

        ttk.Button(save_cancel_frame, text="保存并关闭", command=on_save).pack(side='left', padx=10)
        ttk.Button(save_cancel_frame, text="取消", command=editor_window.destroy).pack(side='right', padx=10)
        update_display()

    def ensure_config_dir(self):
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

    def sanitize_filename(self, name):
        s = str(name).strip().replace(' ', '_')
        s = re.sub(r'(?u)[^-\w.]', '', s)
        return s if s else "unnamed_script"

    def get_config_path(self, script_name):
        safe_filename = self.sanitize_filename(script_name) + ".hanbly"
        return os.path.join(self.config_dir, safe_filename)

    def save_settings_to_file(self, script_name, settings):
        config_path = self.get_config_path(script_name)
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.log_message(f"[错误] 保存配置到 {config_path} 失败: {e}")

    def load_settings_from_file(self, script_name):
        config_path = self.get_config_path(script_name)
        if not os.path.exists(config_path):
            return {}
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                self.log_message(f"成功从 {config_path} 加载配置。")
                return settings
        except (json.JSONDecodeError, Exception) as e:
            self.log_message(f"[错误] 从 {config_path} 加载配置失败: {e}")
            return {}

    def on_closing(self):
        self.log_message("正在关闭程序，保存所有脚本配置...")
        for script_name, settings in self.script_settings.items():
            self.save_settings_to_file(script_name, settings)
        self.log_message("配置保存完毕。")
        self.root.destroy()


if __name__ == "__main__":
    import ctypes

    ctypes.windll.user32.SetProcessDPIAware()
    root = tk.Tk()
    app = App(root)
    root.mainloop()