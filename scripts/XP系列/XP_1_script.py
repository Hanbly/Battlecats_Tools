# scripts/XP系列/XP_1_script.py
from scripts.legend_base_script import LegendaryScriptBase


class ConsumeScript(LegendaryScriptBase):
    template_name = "XP_1"
    activity_name = "游擊戰經驗值喵！"
    find_activity_confidence = 0.6

    @staticmethod
    def get_name():
        return "经验XP速刷1 -- 游擊戰經驗值喵！"

    @staticmethod
    def get_description():
        return "请先在 【地图界面】 选择需要消耗的道具\n        之后于 【主界面】 启动脚本"
