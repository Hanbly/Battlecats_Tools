# scripts/薄荷系列/BoHe_ANCIENT_script.py
from scripts.legend_base_script import LegendaryScriptBase
from common.utils import if_image_on_screen, adb_press_and_release, tap_cats_in_fight, ordered_fight_strategy, \
    BoHe_confidence_threshold, legend_positions_order_default


class ConsumeScript(LegendaryScriptBase):
    template_name = "BoHe_ancient"
    activity_name = "古代貓薄荷關卡"
    find_activity_confidence = BoHe_confidence_threshold

    @staticmethod
    def get_name():
        return "進化的猫薄荷 -- 古代貓薄荷關卡"

    @staticmethod
    def get_description():
        return "请先在 【地图界面】 选择需要消耗的道具\n        之后于 【主界面】 启动脚本"

    @staticmethod
    def get_task_specific_options():
        options = LegendaryScriptBase.get_task_specific_options()

        options.insert(3, {
            'name': 'enter_EXpart_enabled',
            'label': '是否进入EX关卡',
            'type': 'checkbutton',
            'default': True
        })
        return options

    def _handle_post_battle(self, options, adb_path, device_serial, image_folder, package_name):
        enter_EXpart_enabled = options.get('enter_EXpart_enabled', True)
        position_order = options.get('position_order', legend_positions_order_default)

        if if_image_on_screen(adb_path, device_serial, "BoHe_aEXpart", image_folder + "legend/",
                              confidence_threshold=0.7):
            if enter_EXpart_enabled:
                adb_press_and_release(729, 703, adb_path, device_serial)
                positions_to_tap = ordered_fight_strategy(position_order)
                while not if_image_on_screen(adb_path, device_serial, "return_map", image_folder,
                                             confidence_threshold=0.7):
                    if self.is_stop_requested():
                        break
                    tap_cats_in_fight(positions_to_tap, adb_path, device_serial)
            else:
                adb_press_and_release(1189, 712, adb_path, device_serial)