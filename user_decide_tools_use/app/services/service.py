import openai
import json
import os
import shutil
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class ToolExecutionError(Exception):
    """工具执行错误"""
    pass


class OpenAIAgent:
    """集成 OpenAI 的 Agent"""

    def __init__(self, model_name: str, api_key: str, base_url: str = None):
        self.client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name
        self.tools = self._register_tools()

    def _register_tools(self) -> List[Dict]:
        """注册可用工具"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_file",
                    "description": "创建新文件，如果文件已存在会报错",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string", "description": "文件路径"},
                            "content": {"type": "string", "description": "文件内容"}
                        },
                        "required": ["filename", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "modify_file",
                    "description": "修改文件内容，完全替换原有内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string", "description": "文件路径"},
                            "content": {"type": "string", "description": "新的文件内容"}
                        },
                        "required": ["filename", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "读取文件内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string", "description": "文件路径"}
                        },
                        "required": ["filename"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_file",
                    "description": "删除文件",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string", "description": "文件路径"}
                        },
                        "required": ["filename"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_directory",
                    "description": "列出目录内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "目录路径，默认为当前目录", "default": "."}
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "move_file",
                    "description": "移动文件到指定位置",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string", "description": "源文件路径"},
                            "destination": {"type": "string", "description": "目标路径"}
                        },
                        "required": ["source", "destination"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "copy_file",
                    "description": "复制文件到指定位置",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string", "description": "源文件路径"},
                            "destination": {"type": "string", "description": "目标路径"}
                        },
                        "required": ["source", "destination"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "run_command",
                    "description": "执行系统命令（需要用户确认）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "要执行的命令"},
                            "timeout": {"type": "integer", "description": "超时时间（秒）", "default": 30}
                        },
                        "required": ["command"]
                    }
                }
            }
        ]

    def _requires_confirmation(self, tool_name: str) -> bool:
        """判断工具是否需要用户确认"""
        sensitive_tools = {
            "create_file", "modify_file", "delete_file",
            "run_command", "move_file", "copy_file"
        }
        return tool_name in sensitive_tools

    async def run_with_tools(self, user_message: str, task_manager, task_id: str) -> str:
        """带工具调用的 Agent 执行"""

        messages = [
            {
                "role": "system",
                "content": "你是一个AI助手，可以帮助用户完成各种任务。你可以使用工具来操作文件系统。对于创建、修改、删除文件等敏感操作，你会询问用户确认。"
            },
            {"role": "user", "content": user_message}
        ]

        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )

            message = response.choices[0].message

            if message.tool_calls:
                # 处理工具调用
                tool_results = []

                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    # 检查是否需要用户确认
                    if self._requires_confirmation(tool_name):
                        user_response = await task_manager._wait_for_confirmation(
                            task_id, tool_name, tool_args
                        )

                        if not user_response.get("approved"):
                            result = f"用户拒绝执行 {tool_name}"
                        else:
                            try:
                                result = await self._execute_tool(tool_name, tool_args)
                            except Exception as e:
                                result = f"执行 {tool_name} 时出错: {str(e)}"
                    else:
                        # 直接执行
                        try:
                            result = await self._execute_tool(tool_name, tool_args)
                        except Exception as e:
                            result = f"执行 {tool_name} 时出错: {str(e)}"

                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_name,
                        "content": result
                    })

                # 添加助手消息到历史
                messages.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
                })

                # 添加工具结果到历史
                for tr in tool_results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tr["tool_call_id"],
                        "content": tr["content"]
                    })

            else:
                # 没有工具调用，返回最终响应
                return message.content or "任务完成"

        return "达到最大迭代次数限制"

    async def _execute_tool(self, tool_name: str, tool_args: Dict) -> str:
        """实际执行工具"""
        if tool_name == "create_file":
            return await self._create_file(tool_args["filename"], tool_args["content"])
        elif tool_name == "modify_file":
            return await self._modify_file(tool_args["filename"], tool_args["content"])
        elif tool_name == "read_file":
            return await self._read_file(tool_args["filename"])
        elif tool_name == "delete_file":
            return await self._delete_file(tool_args["filename"])
        elif tool_name == "list_directory":
            path = tool_args.get("path", ".")
            return await self._list_directory(path)
        elif tool_name == "move_file":
            return await self._move_file(tool_args["source"], tool_args["destination"])
        elif tool_name == "copy_file":
            return await self._copy_file(tool_args["source"], tool_args["destination"])
        elif tool_name == "run_command":
            timeout = tool_args.get("timeout", 30)
            return await self._run_command(tool_args["command"], timeout)
        return f"未知工具: {tool_name}"

    async def _create_file(self, filename: str, content: str) -> str:
        """创建文件"""
        if os.path.exists(filename):
            raise ToolExecutionError(f"文件已存在: {filename}")

        # 确保目录存在
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)

        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        return f"文件创建成功: {filename}"

    async def _modify_file(self, filename: str, content: str) -> str:
        """修改文件"""
        if not os.path.exists(filename):
            raise ToolExecutionError(f"文件不存在: {filename}")

        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        return f"文件修改成功: {filename}"

    async def _read_file(self, filename: str) -> str:
        """读取文件"""
        if not os.path.exists(filename):
            raise ToolExecutionError(f"文件不存在: {filename}")

        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
        return f"文件内容:\n{content}"

    async def _delete_file(self, filename: str) -> str:
        """删除文件"""
        if not os.path.exists(filename):
            raise ToolExecutionError(f"文件不存在: {filename}")

        os.remove(filename)
        return f"文件删除成功: {filename}"

    async def _list_directory(self, path: str = ".") -> str:
        """列出目录内容"""
        if not os.path.exists(path):
            raise ToolExecutionError(f"路径不存在: {path}")

        items = os.listdir(path)
        result = []
        for item in items:
            full_path = os.path.join(path, item)
            item_type = "📁" if os.path.isdir(full_path) else "📄"
            result.append(f"{item_type} {item}")

        return f"目录 {path} 的内容:\n" + "\n".join(result)

    async def _move_file(self, source: str, destination: str) -> str:
        """移动文件"""
        if not os.path.exists(source):
            raise ToolExecutionError(f"源文件不存在: {source}")

        shutil.move(source, destination)
        return f"文件移动成功: {source} -> {destination}"

    async def _copy_file(self, source: str, destination: str) -> str:
        """复制文件"""
        if not os.path.exists(source):
            raise ToolExecutionError(f"源文件不存在: {source}")

        shutil.copy2(source, destination)
        return f"文件复制成功: {source} -> {destination}"

    async def _run_command(self, command: str, timeout: int = 30) -> str:
        """执行命令"""
        import subprocess

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            output = []
            if result.stdout:
                output.append(f"标准输出:\n{result.stdout}")
            if result.stderr:
                output.append(f"标准错误:\n{result.stderr}")

            output.append(f"返回码: {result.returncode}")

            return "\n".join(output)

        except subprocess.TimeoutExpired:
            raise ToolExecutionError(f"命令执行超时（{timeout}秒）")
        except Exception as e:
            raise ToolExecutionError(f"命令执行失败: {str(e)}")
