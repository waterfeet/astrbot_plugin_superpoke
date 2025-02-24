from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register

from astrbot.api import logger
from astrbot.api.message_components import Poke,Plain
# from astrbot.core.platform.astrbot_message import AstrBotMessage
# from astrbot.core.star.star import StarMetadata
from astrbot.core.star.star_handler import star_handlers_registry, StarHandlerMetadata
from astrbot.core.star.filter.command import CommandFilter
from astrbot.core.star.filter.command_group import CommandGroupFilter
import yaml
import os

@register("superpoke", "waterfeet", "这是 AstrBot 的超级戳一戳插件", "1.0.0", "https://gitee.com/waterfeet/astrbot_plugin_superpoke")
class MyPlugin(Star):
    Superpoke_Command = ""
    # plugin_store_path = "./data/plugins/astrbot_plugin_superpoke"
    plugin_store_path = "./data/plugins/astrbot_plugin_superpoke"
    def __init__(self, context: Context):
        super().__init__(context)
       # 读取 YAML 文件
        if os.path.exists(os.path.join(self.plugin_store_path, "superPokedata.yaml")):
            with open(os.path.join(self.plugin_store_path, "superPokedata.yaml"), "r", encoding='utf-8') as file:
                loaded_data = yaml.safe_load(file)
            if loaded_data['Superpoke_Command'] != "":
                self.Superpoke_Command = loaded_data['Superpoke_Command']
    
    @filter.command("superpoke")        # oper1:help/set  oper2:插件名称  oper3：指令名称
    async def plugin(self, event: AstrMessageEvent, oper1: str = None, oper2: str = None):
        if oper1 is None or oper1 == "help":
            superpoke_help_info = "超级戳一戳功能简介：\n"
            superpoke_help_info += "\n使用 superpoke set <插件名> <指令名>\n即可通过戳一戳调用其他插件相应功能"
            superpoke_help_info += "\n使用 allhelps\n查看本bot安装的其他插件中所有的指令"
            event.set_result(MessageEventResult().message(f"{superpoke_help_info}").use_t2i(False))
        else:
            if oper1 == "set":
                # 获取插件帮助
                plugins = self.context.get_all_stars()
                for plugin in plugins:
                    if plugin is None:
                        return
                    command_handlers = []
                    command_names = []
                    for handler in star_handlers_registry:
                        assert isinstance(handler, StarHandlerMetadata)
                        if handler.handler_module_path != plugin.module_path:
                            continue
                        for filter_ in handler.event_filters:
                            if isinstance(filter_, CommandFilter):
                                command_handlers.append(handler)
                                command_names.append(filter_.command_name)
                                break
                            elif isinstance(filter_, CommandGroupFilter):
                                command_handlers.append(handler)
                                command_names.append(filter_.group_name)
                                
                    if len(command_handlers) > 0:
                        for i in range(len(command_handlers)):
                            if f"{command_names[i]}" == oper2:
                                self.Superpoke_Command = oper2
                                data = {
                                    "Superpoke_Command": self.Superpoke_Command
                                }
                                # 保存数据到 YAML 文件
                                with open(os.path.join(self.plugin_store_path, "superPokedata.yaml"), "w", encoding="utf-8") as file:
                                    yaml.dump(data, file, allow_unicode=True, default_flow_style=False)
                                event.set_result(MessageEventResult().message("戳一戳指令设置成功").use_t2i(False))
                                break
                if self.Superpoke_Command != oper2:
                    event.set_result(MessageEventResult().message("未找到此指令。").use_t2i(False))
                return

    

    @filter.command("allhelps")        # oper1:help/set  oper2:插件名称  oper3：指令名称
    async def plugin_help(self, event: AstrMessageEvent):
        ret = ""
        for plugin in self.context.get_all_stars():
            if plugin is None:
                continue
            # 获取插件帮助
            help_msg = plugin.star_cls.__doc__ if plugin.star_cls.__doc__ else "帮助信息: 未提供"
            help_msg += f"\n\n作者: {plugin.author}\n版本: {plugin.version}"
            command_handlers = []
            command_names = []
            for handler in star_handlers_registry:
                assert isinstance(handler, StarHandlerMetadata)
                if handler.handler_module_path != plugin.module_path:
                    continue
                for filter_ in handler.event_filters:
                    if isinstance(filter_, CommandFilter):
                        command_handlers.append(handler)
                        command_names.append(filter_.command_name)
                        break
                    elif isinstance(filter_, CommandGroupFilter):
                        command_handlers.append(handler)
                        command_names.append(filter_.group_name)
                        
            if len(command_handlers) > 0:
                help_msg += "\n\n指令列表：\n"
                for i in range(len(command_handlers)):
                    help_msg += f"{command_names[i]}: {command_handlers[i].desc}\n"
                    
            help_msg += "\nTip: 指令的触发需要添加唤醒前缀，默认为 /。\n\n------------------\n\n"
            
            ret += f"插件 {plugin.name} 帮助信息：\n" + help_msg
        ret += "更多帮助信息请查看插件仓库 README。"
        event.set_result(MessageEventResult().message(ret).use_t2i(False))

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def getpoke(self, event: AstrMessageEvent):
        for comp in event.message_obj.message:
            if isinstance(comp, Poke):
                logger.info("检测到戳一戳")
                # 具体功能
                if self.Superpoke_Command != "":
                    str = self.Superpoke_Command
                    event.message_obj.message.clear()
                    event.message_obj.message.append( Plain(str) )
                    event.message_obj.message_str = str
                    event.message_str = str
                    self.context.get_event_queue().put_nowait(event)
                event.should_call_llm(True)
                return