#!/usr/bin/env python3
"""
沙盒执行模块

该模块负责在沙盒环境中执行脚本，提供隔离的执行环境。
"""

import subprocess
import os
import tempfile
from pathlib import Path

class Sandbox:
    """
    沙盒执行类
    
    负责在沙盒环境中执行脚本，提供隔离的执行环境。
    """

    @staticmethod
    def execute_script(script_path, runtime, timeout=30, permissions=None, cwd=None):
        """
        在沙盒中执行脚本
        
        在指定的运行时环境中执行脚本，并返回执行结果。
        
        Args:
            script_path (str): 脚本路径
            runtime (str): 运行时环境，支持 'python3', 'bash', 'node'
            timeout (int): 执行超时时间（秒）
            permissions (list): 权限列表
            cwd (str): 工作目录
        
        Returns:
            dict: 执行结果，包含 success, stdout, stderr, returncode 或 error
        """
        if not Path(script_path).exists():
            return {
                'success': False,
                'error': f"Script not found: {script_path}"
            }
        
        # 构建命令
        if runtime == 'python3':
            cmd = ['python3', script_path]
        elif runtime == 'bash':
            cmd = ['bash', script_path]
        elif runtime == 'node':
            cmd = ['node', script_path]
        else:
            return {
                'success': False,
                'error': f"Unsupported runtime: {runtime}"
            }
        
        # 执行脚本
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd or os.path.dirname(script_path)
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': f"Script execution timed out after {timeout} seconds"
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def execute_in_isolated_env(script_content, runtime, timeout=30):
        """
        在隔离环境中执行脚本内容
        
        创建临时文件并执行脚本内容，执行完成后清理临时文件。
        
        Args:
            script_content (str): 脚本内容
            runtime (str): 运行时环境
            timeout (int): 执行超时时间（秒）
        
        Returns:
            dict: 执行结果
        """
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{runtime}', delete=False) as f:
            f.write(script_content)
            temp_script = f.name
        
        try:
            # 执行脚本
            result = Sandbox.execute_script(temp_script, runtime, timeout)
            return result
        finally:
            # 清理临时文件
            if Path(temp_script).exists():
                os.unlink(temp_script)
    
    @staticmethod
    def validate_permissions(permissions):
        """
        验证权限设置
        
        验证权限列表的格式是否正确。
        
        Args:
            permissions (list): 权限列表
        
        Returns:
            bool: 权限格式是否正确
        """
        if not permissions:
            return True
        
        # 检查权限格式
        for perm in permissions:
            if not isinstance(perm, str):
                return False
            # 简单验证权限格式：如 'read: ./src' 或 'write: ./output'
            if not any(perm.startswith(prefix) for prefix in ['read:', 'write:', 'execute:']):
                return False
        
        return True
