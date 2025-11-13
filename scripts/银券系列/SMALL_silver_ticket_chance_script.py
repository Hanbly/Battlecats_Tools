# scripts/银券系列/SMALL_silver_ticket_chance_script.py
from scripts.legend_base_script import LegendaryScriptBase


class ConsumeScript(LegendaryScriptBase):
    template_name = "cats_silver_chance"
    activity_name = "貓咪券機會"

    @staticmethod
    def get_name():
        return "银劵速刷 -- 猫咪券⭐机会"

    @staticmethod
    def get_description():
        return ("请先在 【地图界面】 选择需要消耗的道具\n        "
                "之后于 【主界面】 启动脚本\n        "
                "提示：由于【银劵】掉落几率低，可以选择先刷一些【宝物雷达】，并在运行前于【地图界面】选择消耗道具")

    @staticmethod
    def get_task_specific_options():
        # 获取基类的所有通用选项
        options = LegendaryScriptBase.get_task_specific_options()

        for option in options:
            if option['name'] == 'position_order':
                option['default'] = [6, 10, 1]
                break

        return options
