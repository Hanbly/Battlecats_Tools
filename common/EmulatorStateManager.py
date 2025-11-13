class EmulatorStateManager:
    def __init__(self):
        self.emulator_type = 'unknown'  # 默认为未知

    def set_emulator_by_window_title(self, window_title):
        if window_title is None:
            self.emulator_type = 'unknown'
            return

        title_lower = window_title.lower()
        if '雷电' in title_lower:
            self.emulator_type = 'leidian'
        elif 'mumu' or 'MuMu' or 'Android Device' in title_lower:
            self.emulator_type = 'mumu'
        # 您可以在这里添加更多模拟器的判断，例如 '夜神'
        # elif '夜神' or 'Android Device' in title_lower:
        #     self.emulator_type = 'yeshen'
        else:
            self.emulator_type = 'other'  # 其他或未知类型

    def is_leidian(self):
        return self.emulator_type == 'leidian'

