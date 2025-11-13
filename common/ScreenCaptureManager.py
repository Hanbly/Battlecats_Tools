# common/ScreenCaptureManager.py

import ctypes
import threading
import time
from ctypes import wintypes

import cv2
import numpy as np
import win32con
import win32gui
import win32ui

user32 = ctypes.windll.user32
user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
user32.PrintWindow.restype = wintypes.BOOL


def fast_screen_capture_hwnd(hwnd: int):
    """
    使用 ctypes 直接调用 User32.dll 中的 PrintWindow API 进行截图。
    这个函数现在是类的私有辅助函数，但逻辑保持健壮。
    """
    hwnd_dc, mfc_dc, save_dc, save_bitmap = None, None, None, None
    try:
        # 使用 GetClientRect 更准确，因为它不包含窗口标题栏和边框
        rect = win32gui.GetClientRect(hwnd)
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]

        if width <= 0 or height <= 0:
            return None

        hwnd_dc = win32gui.GetDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()

        save_bitmap = win32ui.CreateBitmap()
        save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(save_bitmap)

        # 标志 PW_CLIENTONLY (值为 1 或 2 都可以，通常用 2: PW_RENDERFULLCONTENT)
        # 这里使用 2 以确保捕获所有内容
        result = user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2)

        if result != 1:
            return None

        bmp_info = save_bitmap.GetInfo()
        bmp_str = save_bitmap.GetBitmapBits(True)

        img = np.frombuffer(bmp_str, dtype=np.uint8).reshape((bmp_info['bmHeight'], bmp_info['bmWidth'], 4))
        img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        return img_bgr

    except (win32ui.error, TypeError):
        # 捕获窗口句柄失效等错误
        return None
    finally:
        # 使用 finally 确保无论是否发生异常，资源都会被释放
        if save_bitmap:
            win32gui.DeleteObject(save_bitmap.GetHandle())
        if save_dc:
            save_dc.DeleteDC()
        if mfc_dc:
            mfc_dc.DeleteDC()
        if hwnd_dc:
            win32gui.ReleaseDC(hwnd, hwnd_dc)


class ScreenCaptureManager:
    """
    根据窗口标题特征，自动选择开发者预设的最佳截图API。
    - 默认使用速度最快的 'bitblt'。
    - 如果窗口标题包含特定关键字（如'雷电模拟器'），则自动切换到兼容性更好的 'printwindow'。
    """

    METHOD_BITBLT = 'bitblt'
    METHOD_PRINTWINDOW = 'printwindow'

    def __init__(self, window_title=None, class_name=None, target_child_class='RenderWindow', log_callback=None):
        self.log = log_callback if log_callback else print

        self.hwnd = None
        self.window_title = window_title
        self.class_name = class_name
        self.target_child_class = target_child_class
        self._find_window()

        if self.hwnd is None:
            raise Exception("未能找到指定的窗口或其渲染子窗口。请检查窗口标题/类名。")

        # 【核心逻辑】根据窗口标题，硬编码选择截图方法
        self._capture_method = self._dispatch_capture_method_by_title(window_title)

        self.latest_frame = None
        self.lock = threading.Lock()
        self.is_running = False
        self.capture_thread = None

    def _dispatch_capture_method_by_title(self, title):
        """
        [开发者配置区]
        根据窗口标题关键字，返回应该使用的截图方法。
        """
        if title is None:
            return self.METHOD_BITBLT  # 如果没有标题，默认使用最快的方法

        # 您可以在这里添加更多模拟器的关键字
        # 注意关键字的大小写，或者统一转换为小写进行比较
        title_lower = title.lower()
        if '雷电模拟器' in title:
            # 如果标题包含"雷电模拟器"，就使用printwindow
            return self.METHOD_PRINTWINDOW
        # 可以在这里添加更多判断，例如：
        # if '夜神' in title_lower:
        #     return self.METHOD_PRINTWINDOW

        # 对于所有其他情况（包括MuMu等），默认使用速度最快的bitblt
        return self.METHOD_BITBLT

    def _find_window(self):
        main_hwnd = win32gui.FindWindow(self.class_name, self.window_title)
        if not main_hwnd:
            self.log(f"警告: 无法找到主窗口 (标题='{self.window_title}', 类名='{self.class_name}')")
            return
        try:
            render_hwnd = win32gui.FindWindowEx(main_hwnd, 0, self.target_child_class, None)
            if render_hwnd:
                self.hwnd = render_hwnd
            else:
                self.hwnd = main_hwnd
        except Exception:
            self.hwnd = main_hwnd

    def _capture_with_bitblt(self):
        try:
            left, top, right, bot = win32gui.GetClientRect(self.hwnd)
            width, height = right - left, bot - top
            if width <= 0 or height <= 0:
                return None

            hwnd_dc = win32gui.GetWindowDC(self.hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()

            save_bitmap = win32ui.CreateBitmap()
            save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(save_bitmap)

            save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)

            bmp_str = save_bitmap.GetBitmapBits(True)
            img = np.frombuffer(bmp_str, dtype='uint8').reshape((height, width, 4))
            frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            win32gui.DeleteObject(save_bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(self.hwnd, hwnd_dc)
            return frame
        except Exception:
            return None

    def _capture_with_printwindow(self):
        hwnd_dc, mfc_dc, save_dc, save_bitmap = None, None, None, None
        try:
            rect = win32gui.GetClientRect(self.hwnd)
            width, height = rect[2], rect[3]
            if width <= 0 or height <= 0: return None

            hwnd_dc = win32gui.GetDC(self.hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            save_bitmap = win32ui.CreateBitmap()
            save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(save_bitmap)

            ctypes.windll.user32.PrintWindow(self.hwnd, save_dc.GetSafeHdc(), 2)

            bmp_str = save_bitmap.GetBitmapBits(True)
            img = np.frombuffer(bmp_str, dtype='uint8').reshape((height, width, 4))
            frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            return frame
        except Exception:
            return None
        finally:
            if save_bitmap:
                win32gui.DeleteObject(save_bitmap.GetHandle())
            if save_dc:
                save_dc.DeleteDC()
            if mfc_dc:
                mfc_dc.DeleteDC()
            if hwnd_dc:
                win32gui.ReleaseDC(self.hwnd, hwnd_dc)

    def capture_frame(self):
        if not self.hwnd or not win32gui.IsWindow(self.hwnd):
            self.log("错误：截图目标窗口句柄已失效。")
            self.stop()
            return None

        if self._capture_method == self.METHOD_BITBLT:
            return self._capture_with_bitblt()
        elif self._capture_method == self.METHOD_PRINTWINDOW:
            return self._capture_with_printwindow()

        return None

    def _capture_loop(self):
        while self.is_running:
            frame = self.capture_frame()
            if frame is not None:
                with self.lock:
                    self.latest_frame = frame
            else:
                time.sleep(0.5)
            time.sleep(0.01)

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()

    def stop(self):
        if not self.is_running: return
        self.is_running = False
        if self.capture_thread:
            self.capture_thread.join()

    def get_latest_frame(self):
        with self.lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None
