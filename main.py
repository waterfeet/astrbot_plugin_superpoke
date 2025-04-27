import random
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register

from astrbot.api import logger
from astrbot.api.message_components import Poke,Plain
from astrbot.core.star.star_handler import star_handlers_registry, StarHandlerMetadata
from astrbot.core.star.filter.command import CommandFilter
from astrbot.core.star.filter.command_group import CommandGroupFilter
import yaml
import os
import json

@register("superpoke", "waterfeet", "这是 AstrBot 的超级戳一戳插件", "1.0.0", "https://gitee.com/waterfeet/astrbot_plugin_superpoke")
class MyPlugin(Star):
    Superpoke_Command = ""
    plugin_store_path = "./data/plugins/astrbot_plugin_superpoke"
    def __init__(self, context: Context):
        super().__init__(context)
        self.commands = []  # 新的数据结构：[{"command": str, "weight": int}]
        self.admins = self._load_admins()  # 加载管理员列表
        # 创建插件数据目录
        os.makedirs(self.plugin_store_path, exist_ok=True)
        
        # 加载YAML数据
        self._load_commands()
    
    def _load_admins(self):
        """加载管理员列表"""
        try:
            with open(os.path.join('data', 'cmd_config.json'), 'r', encoding='utf-8-sig') as f:
                config = json.load(f)
                return config.get('admins_id', [])
        except Exception as e:
            self.context.logger.error(f"加载管理员列表失败: {str(e)}")
            return []
        
    def is_admin(self, user_id):
        """检查用户是否为管理员"""
        return str(user_id) in self.admins    
    def _load_commands(self):
        """加载指令数据"""
        yaml_path = os.path.join(self.plugin_store_path, "superPokedata.yaml")
        try:
            if os.path.exists(yaml_path):
                with open(yaml_path, "r", encoding='utf-8') as file:
                    data = yaml.safe_load(file) or {}
                self.commands = data.get('commands', [])
                # 数据格式校验
                if not all(isinstance(cmd.get('command'), str) and isinstance(cmd.get('weight', 1), int) for cmd in self.commands):
                    raise ValueError("Invalid command format")
        except Exception as e:
            self.context.logger.error(f"加载指令数据失败: {str(e)}")
            self.commands = []

    def _save_commands(self):
        """保存指令数据"""
        yaml_path = os.path.join(self.plugin_store_path, "superPokedata.yaml")
        try:
            data = {'commands': self.commands}
            with open(yaml_path, "w", encoding="utf-8") as file:
                yaml.dump(data, file, allow_unicode=True, default_flow_style=False)
        except Exception as e:
            self.context.logger.error(f"保存指令数据失败: {str(e)}")
    
    
    def DoResp(self, event: AstrMessageEvent):
        if not self.commands:
            return
        
        # 计算总权重
        total_weight = sum(cmd['weight'] for cmd in self.commands)
        if total_weight <= 0:
            return
        
        # 生成随机选择
        rand = random.uniform(0, total_weight)
        current = 0
        for cmd in self.commands:
            current += cmd['weight']
            if rand <= current:
                selected_cmd = cmd['command']
                break
        
        # 处理消息
        if event.session.message_type.name == 'GROUP_MESSAGE':
            astrbot_config = self.context.get_config()
            if wake_prefix := astrbot_config.get("wake_prefix", []):
                selected_cmd = wake_prefix[0] + selected_cmd
        
        # 构造消息
        event.message_obj.message.clear()
        event.message_obj.message.append(Plain(selected_cmd))
        event.message_obj.message_str = selected_cmd
        event.message_str = selected_cmd
        self.context.get_event_queue().put_nowait(event)
        event.should_call_llm(True)


    @filter.command("superpoke_help")
    async def superpoke_help(self, event: AstrMessageEvent):
        help_info = [
            "超级戳一戳功能指南：",
            "👉 当前指令列表：",
            *[f"{i+1}. {cmd['command']} (权重：{cmd['weight']})" for i, cmd in enumerate(self.commands)],
            "\n管理命令：",
            "• superpoke_add [指令] [权重] - 添加新指令（支持空格）",
            "• superpoke_del [序号] - 删除指定指令",
            "• superpoke_weight [序号] [新权重] - 修改指令权重",  # 新增帮助项
            "• superpoke_list - 显示当前指令列表",
            "• superpoke_help - 显示帮助信息"
        ]
        return event.plain_result('\n'.join(help_info))

    @filter.command("superpoke_list")
    async def superpoke_list(self, event: AstrMessageEvent):
        if not self.commands:
            return event.plain_result("当前没有配置任何指令")
        
        list_info = ["当前配置的指令："]
        list_info.extend([f"{i+1}. {cmd['command']} (权重：{cmd['weight']})" for i, cmd in enumerate(self.commands)])
        return event.plain_result('\n'.join(list_info))


    @filter.command("allhelps")        # oper1:help/set  oper2:插件名称  oper3：指令名称
    async def allhelps(self, event: AstrMessageEvent):
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
                    help_msg += f"【{command_names[i]}】{command_handlers[i].desc}\n"
                    
            help_msg += "\n\n------------------\n\n"
            
            ret += f"插件 {plugin.name} 帮助信息：\n" + help_msg
        ret += "更多帮助信息请查看插件仓库 README。"
        event.set_result(MessageEventResult().message(ret).use_t2i(False))
        return


    @filter.command("superpoke_add")
    async def superpoke_add(self, event: AstrMessageEvent):
        """添加新指令格式：superpoke_add [指令（支持空格）] [权重(可选)]"""
        if not self.is_admin(str(event.get_sender_id())):
            return event.plain_result("❌ 只有管理员才能使用此指令")
        
        # 解析原始参数
        raw_args = event.get_message_str().split()[1:]
        if not raw_args:
            return event.plain_result("❌ 使用方法：superpoke_add [指令] [权重(可选)]")
        
        # 智能分离指令和权重
        weight = 1
        if len(raw_args) >= 1:
            # 从后往前查找数字作为权重
            try:
                potential_weight = int(raw_args[-1])
                weight = max(1, min(potential_weight, 100))  # 限制权重范围1-100
                command_parts = raw_args[:-1]  # 剩下的部分作为指令
            except ValueError:
                # 最后不是数字，整个作为指令
                command_parts = raw_args
                weight = 1
        
        if not command_parts:
            return event.plain_result("❌ 指令内容不能为空")
        
        new_command = " ".join(command_parts)
        
        # 检查重复
        if any(cmd['command'] == new_command for cmd in self.commands):
            return event.plain_result("❌ 该指令已存在")
        
        self.commands.append({'command': new_command, 'weight': weight})
        self._save_commands()
        return event.plain_result(f"✅ 成功添加指令：{new_command} 权重：{weight}")


    @filter.command("superpoke_del")
    async def superpoke_del(self, event: AstrMessageEvent):
        """删除指令格式：superpoke_del [序号]"""
        if not self.is_admin(str(event.get_sender_id())):
            return event.plain_result("❌ 只有管理员才能使用此指令")
        
        try:
            index = int(event.get_message_str().split()[1]) - 1
            if 0 <= index < len(self.commands):
                removed = self.commands.pop(index)
                self._save_commands()
                return event.plain_result(f"✅ 已删除指令：{removed['command']}")
            return event.plain_result("❌ 无效的序号")
        except (IndexError, ValueError):
            return event.plain_result("❌ 使用方法：superpoke_del [序号]")
        
    @filter.command("superpoke_weight")
    async def superpoke_weight(self, event: AstrMessageEvent):
        """修改权重格式：superpoke_weight [序号] [新权重]"""
        if not self.is_admin(str(event.get_sender_id())):
            return event.plain_result("❌ 只有管理员才能使用此指令")
        
        args = event.get_message_str().split()[1:]
        try:
            if len(args) != 2:
                raise ValueError
                
            index = int(args[0]) - 1
            new_weight = max(1, min(int(args[1]), 100))  # 限制1-100
            
            if 0 <= index < len(self.commands):
                self.commands[index]['weight'] = new_weight
                self._save_commands()
                cmd = self.commands[index]['command']
                return event.plain_result(f"✅ 已更新指令：{cmd}\n新权重：{new_weight}")
            raise IndexError
        except (ValueError, IndexError):
            return event.plain_result("❌ 使用方法：superpoke_weight [序号] [新权重(1-100)]")
        
    @filter.event_message_type(filter.EventMessageType.ALL)
    async def getpoke(self, event: AstrMessageEvent):
        for comp in event.message_obj.message:
            if isinstance(comp, Poke):
                bot_id = event.message_obj.raw_message.get('self_id')
                if comp.qq != bot_id:
                    return
                logger.info("检测到戳一戳")
                self.DoResp(event)
                return
            