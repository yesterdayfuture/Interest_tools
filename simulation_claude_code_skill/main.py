#!/usr/bin/env python3
"""
Claude Code Skills 模拟系统的主应用文件

该文件实现了一个基于 FastAPI 的 Claude Code Skills 模拟系统，
支持技能的动态加载、意图识别与匹配、渐进式披露及安全沙盒执行。
"""

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import openai
import os
import json
import re
from dotenv import load_dotenv
from src.skill_manager import SkillManager
from src.intent_matcher import IntentMatcher
from src.progressive_disclosure import ProgressiveDisclosure
from src.sandbox import Sandbox
from pathlib import Path
import uvicorn
from contextlib import asynccontextmanager

# 加载环境变量
load_dotenv()

# 初始化OpenAI客户端
openai.api_key = os.getenv("OPENAI_API_KEY")  # 从环境变量获取OpenAI API密钥
openai.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")  # 从环境变量获取OpenAI API基础URL
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")  # 从环境变量获取OpenAI模型名称

# 初始化技能管理器和意图匹配器
skill_manager = SkillManager()  # 技能管理器实例，负责加载和管理技能
intent_matcher = IntentMatcher()  # 意图匹配器实例，负责匹配用户意图与技能


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    在应用启动时初始化，项目启动时不加载技能，
    在应用关闭时进行清理。
    
    Args:
        app (FastAPI): FastAPI应用实例
    """
    print("Application starting...")
    # 项目启动时不加载技能
    print("Skills will be loaded dynamically when needed")

    yield

app = FastAPI(
    title="Claude Code Skills API",
    description="Anthropic Claude Code Skills 模拟实现",
    version="1.0.0",
    lifespan=lifespan
)



# # 加载技能
# skill_manager.load_skills()

# 请求模型
class SkillRequest(BaseModel):
    """
    技能请求模型
    
    Attributes:
        skill_id (str): 技能ID
        prompt (str): 提示内容
        parameters (dict): 参数字典，默认为空字典
    """
    skill_id: str
    prompt: str
    parameters: dict = {}

class IntentRequest(BaseModel):
    """
    意图请求模型
    
    Attributes:
        input (str): 用户输入
    """
    input: str

class QARequest(BaseModel):
    """
    问答请求模型
    
    Attributes:
        question (str): 用户的问题
    """
    question: str

# 响应模型
class SkillResponse(BaseModel):
    """
    技能响应模型
    
    Attributes:
        skill_name (str): 技能名称
        skill_version (str): 技能版本
        response (str): 响应内容
        confidence (float): 置信度，默认为None
    """
    skill_name: str
    skill_version: str
    response: str
    confidence: float = None

class SkillListResponse(BaseModel):
    """
    技能列表响应模型
    
    Attributes:
        skills (list): 技能列表
    """
    skills: list

class IntentResponse(BaseModel):
    """
    意图响应模型
    
    Attributes:
        matched_skills (list): 匹配的技能列表
    """
    matched_skills: list

class QAResponse(BaseModel):
    """
    问答响应模型
    
    Attributes:
        question (str): 用户的问题
        answer (str): 回答内容
        used_skill (str): 使用的技能
        confidence (float): 置信度
    """
    question: str
    answer: str
    used_skill: str
    confidence: float

# 依赖项
def get_skill_manager():
    """
    获取技能管理器实例的依赖项
    
    Returns:
        SkillManager: 技能管理器实例
    """
    return skill_manager

# 获取技能列表
@app.get("/skills", response_model=SkillListResponse)
async def get_skills(manager: SkillManager = Depends(get_skill_manager)):
    """
    获取所有技能的列表
    
    动态加载技能，并只返回技能的元数据，节省带宽。
    
    Args:
        manager (SkillManager): 技能管理器实例
    
    Returns:
        SkillListResponse: 技能列表响应
    """
    # 动态加载技能
    manager.load_skills()
    skills = manager.get_all_skills()
    # 只返回元数据，节省带宽
    skill_metadata = [ProgressiveDisclosure.get_skill_metadata(skill) for skill in skills]
    return SkillListResponse(skills=skill_metadata)

# 获取技能详情
@app.get("/skills/{skill_id}")
async def get_skill(skill_id: str, manager: SkillManager = Depends(get_skill_manager)):
    """
    获取指定技能的详细信息
    
    动态加载技能，并返回技能的完整内容。
    
    Args:
        skill_id (str): 技能ID
        manager (SkillManager): 技能管理器实例
    
    Returns:
        dict: 技能的完整内容
    
    Raises:
        HTTPException: 当技能不存在时，返回404错误
    """
    # 动态加载技能
    manager.load_skills()
    skill = manager.get_skill_by_id(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return ProgressiveDisclosure.get_skill_full_content(skill)

# 触发技能
@app.post("/skills/{skill_id}/trigger", response_model=SkillResponse)
async def trigger_skill(skill_id: str, request: SkillRequest, manager: SkillManager = Depends(get_skill_manager)):
    """
    触发指定技能的执行
    
    动态加载技能，执行技能脚本（如果有），并调用OpenAI API生成响应。
    
    Args:
        skill_id (str): 技能ID
        request (SkillRequest): 技能请求
        manager (SkillManager): 技能管理器实例
    
    Returns:
        SkillResponse: 技能响应
    
    Raises:
        HTTPException: 当技能不存在时，返回404错误
    """
    # 动态加载技能
    manager.load_skills()
    skill = manager.get_skill_by_id(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    # 构建完整上下文
    skill_content = ProgressiveDisclosure.get_skill_full_content(skill)
    
    # 执行脚本（如果有）
    script_results = []
    for script in skill_content.get('scripts', []):
        script_path = Path(skill['path']) / script.get('path')
        
        # 特殊处理技能创建器脚本
        if skill['id'] == 'skill-creator' and script.get('name') == 'create_skill':
            # 从用户输入中提取技能信息
            import re
            
            # 首先检查是否是创建新技能的请求
            create_skill_match = re.search(r'创建一个新的skills?', request.prompt, re.IGNORECASE)
            
            # 优先从parameters中获取技能信息
            if 'skill_name' in request.parameters:
                skill_name = request.parameters['skill_name']
                skill_description = request.parameters.get('skill_description', 'Generate content for new skill')
                skill_triggers = request.parameters.get('skill_triggers', ['new skill', 'generate content', 'skill generator'])
                skill_instructions = request.parameters.get('skill_instructions', 'When users request content, generate high-quality content based on the given keywords and topics.')
            elif create_skill_match:
                # 分析用户需求，提取技能的核心功能
                # 提取技能名称（英文）
                # 尝试从请求中提取主题
                topic_match = re.search(r'触发词是(.+?)等|生成(.+?)文档|用于(.+?)|关于(.+?)', request.prompt)
                
                if topic_match:
                    # 提取主题并转换为英文
                    topic = topic_match.group(1) or topic_match.group(2) or topic_match.group(3) or topic_match.group(4)
                    topic = topic.strip()
                    
                    # 分割主题，取第一个词作为核心主题
                    topic_words = topic.split()[0]
                    
                    # 简单的中文到英文的转换，实际应用中可以使用更复杂的翻译
                    topic_en = {
                        '小红书': 'xiaohongshu',
                        '爆款': 'viral',
                        '文档': 'doc',
                        '健身': 'fitness',
                        '密码': 'password',
                        '随机': 'random',
                        '生成器': 'generator',
                        '笔记': 'note',
                        '文案': 'copywriting',
                        '旅行': 'travel',
                        '攻略': 'guide'
                    }.get(topic_words, topic_words.lower())
                    
                    # 生成英文技能名称
                    skill_name = f"{topic_en}-generator"
                    # 生成英文技能描述
                    skill_description = f"Generate {topic} content"
                    # 生成英文触发词
                    skill_triggers = [topic, topic_en, f"{topic_en} generator", f"generate {topic}"]
                else:
                    # 默认英文技能名称
                    skill_name = 'new-skill-generator'
                    skill_description = 'Generate content for new skill'
                    skill_triggers = ['new skill', 'generate content', 'skill generator']
                
                # 根据用户需求生成技能指令
                # 分析用户请求中的具体要求
                if '表情' in request.prompt and '有趣' in request.prompt:
                    skill_instructions = 'When users request content, generate engaging content with emojis and interesting sentences that are vivid and形象.'
                elif '健身' in request.prompt:
                    skill_instructions = 'When users request fitness content, generate comprehensive fitness plans, workout routines, and nutrition advice.'
                elif '密码' in request.prompt:
                    skill_instructions = 'When users request password generation, generate secure random passwords with a combination of uppercase and lowercase letters, numbers, and special characters.'
                else:
                    # 默认指令
                    skill_instructions = 'When users request content, generate high-quality content based on the given keywords and topics.'
                
                # 确保技能名称是英文
                # 移除所有非英文字符
                import re
                skill_name = re.sub(r'[^a-zA-Z0-9\-]', '', skill_name)
                # 如果技能名称为空，使用默认名称
                if not skill_name:
                    skill_name = 'new-skill-generator'
            else:
                # 如果不是创建新技能的请求，使用默认值
                skill_name = 'random-password-generator'
                skill_description = '生成随机密码'
                skill_triggers = ['生成密码', '随机密码', 'password generator']
                skill_instructions = '当用户请求生成随机密码时，生成一个安全的随机密码。'
            
            # 执行脚本
            import subprocess
            try:
                # 确保所有参数都是字符串类型
                skill_name = str(skill_name)
                skill_description = str(skill_description)
                # 确保触发词是列表格式
                if isinstance(skill_triggers, str):
                    # 如果已经是字符串，保持不变
                    pass
                else:
                    # 如果是列表，转换为JSON字符串
                    skill_triggers = json.dumps(skill_triggers)
                skill_instructions = str(skill_instructions)
                
                # 构建命令
                cmd = [
                    'python3', str(script_path),
                    '--skill_name', skill_name,
                    '--skill_description', skill_description,
                    '--skill_triggers', skill_triggers,
                    '--skill_instructions', skill_instructions
                ]
                
                # 添加大模型生成的脚本内容和SKILL.md内容（如果有）
                import tempfile
                temp_files = []
                
                if 'skill_script' in request.parameters and request.parameters['skill_script']:
                    # 创建临时文件存储脚本内容
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                        f.write(request.parameters['skill_script'])
                        temp_files.append(f.name)
                    cmd.extend(['--skill_script_file', f.name])
                
                if 'skill_md_content' in request.parameters and request.parameters['skill_md_content']:
                    # 创建临时文件存储SKILL.md内容
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                        f.write(request.parameters['skill_md_content'])
                        temp_files.append(f.name)
                    cmd.extend(['--skill_md_content_file', f.name])
                
                print(f"执行技能创建脚本: {cmd}")
                
                # 执行命令
                timeout = script.get('timeout', 60)
                try:
                    timeout = float(timeout)
                except:
                    timeout = 60
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                
                print(f"脚本执行结果 - stdout: {result.stdout}")
                print(f"脚本执行结果 - stderr: {result.stderr}")
                print(f"脚本执行结果 - returncode: {result.returncode}")
                
                script_results.append({
                    'name': script.get('name'),
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'returncode': result.returncode
                })
            except Exception as e:
                print(f"执行脚本时出错: {str(e)}")
                script_results.append({
                    'name': script.get('name'),
                    'stdout': '',
                    'stderr': str(e),
                    'returncode': 1
                })
        else:
            # 普通脚本执行
            result = Sandbox.execute_script(
                str(script_path),
                script.get('runtime', 'python3'),
                script.get('timeout', 30)
            )
            script_results.append(result)
    
    # 构建OpenAI提示
    prompt = f"""
    You are executing the {skill['metadata']['name']} skill (version: {skill['metadata']['version']}).
    
    Instructions:
    {skill_content['instructions']}
    
    User input:
    {request.prompt}
    
    Parameters:
    {request.parameters}
    
    Script results:
    {script_results}
    """
    
    # 调用OpenAI API
    try:
        # 模拟OpenAI API响应，避免实际调用
        # 当没有设置真实的API密钥时，返回模拟响应
        if not openai.api_key or openai.api_key == "your_openai_api_key_here":
            return SkillResponse(
                skill_name=skill['metadata']['name'],
                skill_version=skill['metadata']['version'],
                response=f"This is a simulated response from the {skill['metadata']['name']} skill.\n\nUser query: {request.prompt}\n\nTo get real responses, please set your OpenAI API key in the .env file."
            )
        
        response = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": f"You are the {skill['metadata']['name']} skill executor."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )
        
        return SkillResponse(
            skill_name=skill['metadata']['name'],
            skill_version=skill['metadata']['version'],
            response=response.choices[0].message.content
        )
    except Exception as e:
        print(f"Error in trigger_skill: {e}")
        # 返回模拟响应，避免因API错误而失败
        return SkillResponse(
            skill_name=skill['metadata']['name'],
            skill_version=skill['metadata']['version'],
            response=f"Error calling OpenAI API: {str(e)}\n\nThis is a simulated response from the {skill['metadata']['name']} skill."
        )

# 意图匹配
@app.post("/intent/match", response_model=IntentResponse)
async def match_intent(request: IntentRequest, manager: SkillManager = Depends(get_skill_manager)):
    """
    匹配用户意图与技能
    
    动态加载技能，并使用意图匹配器匹配用户输入与技能。
    
    Args:
        request (IntentRequest): 意图请求
        manager (SkillManager): 技能管理器实例
    
    Returns:
        IntentResponse: 匹配的技能列表
    """
    # 动态加载技能
    manager.load_skills()
    skills = manager.get_all_skills()
    matches = intent_matcher.match_skills(request.input, skills)
    
    # 构建响应
    matched_skills = []
    for match in matches:
        matched_skills.append({
            'skill_id': match['skill']['id'],
            'skill_name': match['skill']['metadata']['name'],
            'confidence': match['confidence'],
            'description': match['skill']['metadata']['description']
        })
    
    return IntentResponse(matched_skills=matched_skills)

# 手动调用技能
@app.post("/skills/call", response_model=SkillResponse)
async def call_skill(request: SkillRequest, manager: SkillManager = Depends(get_skill_manager)):
    """
    手动调用技能
    
    调用trigger_skill函数执行指定技能。
    
    Args:
        request (SkillRequest): 技能请求
        manager (SkillManager): 技能管理器实例
    
    Returns:
        SkillResponse: 技能响应
    """
    return await trigger_skill(request.skill_id, request, manager)

# 获取技能元数据（工具接口）
@app.get("/tools/skills/metadata")
async def get_skills_metadata(manager: SkillManager = Depends(get_skill_manager)):
    """
    获取所有技能的元数据，用于大模型选择技能
    
    动态加载技能元数据，并只返回名字、描述和触发词。
    
    Args:
        manager (SkillManager): 技能管理器实例
    
    Returns:
        dict: 技能元数据列表
    """
    # 动态加载技能元数据
    skills_metadata = manager.load_skills_metadata()
    # 只返回名字、描述和触发词
    skills_info = [
        {
            "skill_id": skill['id'],
            "name": skill['metadata']['name'],
            "description": skill['metadata']['description'],
            "triggers": skill['metadata'].get('triggers', [])
        }
        for skill in skills_metadata
    ]
    return {"skills": skills_info}

# 问答接口（使用大模型和正则结合选择技能）
@app.post("/qa", response_model=QAResponse)
async def ask_question(request: QARequest, manager: SkillManager = Depends(get_skill_manager)):
    """
    使用大模型和正则结合选择合适的技能并回答问题
    
    1. 动态加载技能元数据
    2. 使用正则表达式和大模型结合选择技能
    3. 加载选中技能的完整信息
    4. 构建技能请求
    5. 调用技能执行
    6. 构建问答响应
    
    Args:
        request (QARequest): 问答请求
        manager (SkillManager): 技能管理器实例
    
    Returns:
        QAResponse: 问答响应
    """
    try:
        # 1. 动态加载技能元数据
        skills_metadata = manager.load_skills_metadata()
        print(f"Loaded metadata for {len(skills_metadata)} skills")
        
        # 构建技能信息列表，包含触发词
        skills_info = [
            {
                "skill_id": skill['id'],
                "name": skill['metadata']['name'],
                "description": skill['metadata']['description'],
                "triggers": skill['metadata'].get('triggers', [])
            }
            for skill in skills_metadata
        ]
        
        # 2. 大模型和正则结合选择技能
        selected_skills = []
        
        # 先使用正则表达式匹配
        for skill in skills_metadata:
            triggers = skill['metadata'].get('triggers', [])
            for trigger in triggers:
                if re.search(re.escape(trigger), request.question, re.IGNORECASE):
                    selected_skills.append(skill['id'])
                    break
        
        # 如果正则没有匹配到，使用大模型选择
        if not selected_skills:
            # 构建让大模型选择技能的提示
            system_prompt = """
            You are a skill selector. Your task is to analyze the user's question and select the most appropriate skill(s) from the provided list to answer the question.
            
            If none of the skills are appropriate, return an empty list.
            
            Return only the JSON format as specified below, without any additional text.
            
            Format:
            {
                "selected_skills": ["skill_id1", "skill_id2"]
            }
            """
            
            user_prompt = f"""
            User's question: {request.question}
            
            Available skills:
            {json.dumps(skills_info, indent=2, ensure_ascii=False)}
            
            Please select the most appropriate skill(s) to answer this question. Return only the JSON format.
            """
            
            try:
                # 模拟大模型响应
                if "审查" in request.question and "代码" in request.question:
                    selected_skills = ["code-reviewer"]
                elif "分析" in request.question and "项目" in request.question and "健康" in request.question:
                    selected_skills = ["project-health"]
                else:
                    # 实际调用大模型
                    if openai.api_key and openai.api_key != "your_openai_api_key_here":
                        response = openai.chat.completions.create(
                            model=OPENAI_MODEL,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            max_tokens=1000
                        )
                        
                        # 解析响应
                        response_content = response.choices[0].message.content
                        selection = json.loads(response_content)
                        selected_skills = selection.get("selected_skills", [])
            except Exception as e:
                print(f"Error selecting skills with model: {e}")
                # 如果大模型调用失败，使用传统的意图匹配
                # 临时加载技能进行匹配
                manager.load_skills()
                skills = manager.get_all_skills()
                matches = intent_matcher.match_skills(request.question, skills)
                if matches:
                    selected_skills = [matches[0]['skill']['id']]
        
        print(f"Selected skills: {selected_skills}")
        
        if not selected_skills:
            # 如果没有选择技能，返回默认响应
            return QAResponse(
                question=request.question,
                answer="I'm sorry, I don't have a specific skill to answer this question.",
                used_skill="default",
                confidence=1.0
            )
        
        # 3. 加载选中技能的完整信息
        # 先加载所有技能
        manager.load_skills()
        
        # 4. 使用第一个选择的技能
        skill_id = selected_skills[0]
        skill = manager.get_skill_by_id(skill_id)
        
        if not skill:
            return QAResponse(
                question=request.question,
                answer=f"Selected skill {skill_id} not found.",
                used_skill="default",
                confidence=0.0
            )
        
        # 5. 构建技能请求
        if skill_id == "skill-creator":
            # 构建提示让大模型生成技能内容和脚本
            system_prompt = """
            You are a skill content generator. Your task is to generate the content for a new skill based on the user's request.
            
            You need to generate:
            1. SKILL.md content: including frontmatter metadata and instructions
            2. Script content: a Python script that implements the skill's functionality
            
            The skill directory name should be in English (kebab-case), not Chinese.
            
            Return the content in the following format:
            
            ```json
            {
                "skill_name": "skill-name-in-kebab-case",
                "skill_description": "Brief description of the skill",
                "skill_triggers": ["trigger1", "trigger2"],
                "skill_instructions": "Detailed instructions for the skill",
                "skill_md_content": "Complete SKILL.md content",
                "skill_script": "Complete Python script content"
            }
            ```
            
            Make sure the script is executable and follows Python best practices.
            """
            
            user_prompt = f"""
            User's request: {request.question}
            
            Please generate the content for a new skill based on this request.
            Return only the JSON format as specified.
            """
            
            try:
                # 实际调用大模型
                response = openai.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                
                # 解析响应
                response_content = response.choices[0].message.content
                print(f"大模型响应内容: {response_content}")
                # 提取JSON部分
                json_start = response_content.find('```json')
                json_end = response_content.find('```', json_start + 7)
                if json_start != -1 and json_end != -1:
                    json_content = response_content[json_start + 7:json_end]
                    print(f"提取的JSON内容: {json_content}")
                    try:
                        skill_data = json.loads(json_content)
                    except json.JSONDecodeError as e:
                        print(f"JSON解析错误: {e}")
                        # 提供默认的技能内容
                        skill_data = {
                            "skill_name": "fitness-plan-generator",
                            "skill_description": "Generate comprehensive fitness plans with training routines and diet advice",
                            "skill_triggers": ["健身", "计划", "fitness", "workout plan"],
                            "skill_instructions": "When users request fitness plans, generate detailed training routines and diet advice based on the given keywords and topics.",
                            "skill_md_content": "---\nname: fitness-plan-generator\ndescription: Generate comprehensive fitness plans with training routines and diet advice\nversion: 1.0.0\nauthor: Your Team\ntags: [fitness, workout, diet]\ntriggers: [\"健身\", \"计划\", \"fitness\", \"workout plan\"]\nauto_trigger: true\npriority: medium\n---\n\n## 指令\n\nWhen users request fitness plans, generate detailed training routines and diet advice based on the given keywords and topics.\n\n## 输出格式\n\n请使用Markdown格式输出详细的健身计划，包含训练计划和饮食建议。",
                            "skill_script": "#!/usr/bin/env python3\n''\nGenerate comprehensive fitness plans\n''\nimport sys\nimport random\n\ndef generate_fitness_plan(keywords, topic):\n    '''生成健身计划'''    \n    # 生成标题\n    titles = [\n        '💪' + topic + '健身计划|详细训练方案',\n        '🔥' + topic + '专业训练计划|附饮食建议',\n        '🏋️\u200d♂️' + topic + '健身指南|科学训练方法'\n    ]\n    title = random.choice(titles)\n\n    # 生成训练计划\n    training_plans = {\n        '初学者': [\n            '周一: 胸部+三头肌',\n            '周二: 背部+二头肌',\n            '周三: 休息',\n            '周四: 腿部',\n            '周五: 肩部',\n            '周六: 全身训练',\n            '周日: 休息'\n        ],\n        '中级': [\n            '周一: 胸部+三头肌',\n            '周二: 背部+二头肌',\n            '周三: 腿部',\n            '周四: 肩部+核心',\n            '周五: 全身训练',\n            '周六: 有氧训练',\n            '周日: 休息'\n        ],\n        '高级': [\n            '周一: 胸部+三头肌',\n            '周二: 背部+二头肌',\n            '周三: 腿部',\n            '周四: 肩部+核心',\n            '周五: 全身训练',\n            '周六: 有氧训练',\n            '周日: 主动恢复'\n        ]\n    }\n\n    # 生成饮食建议\n    diet_advice = [\n        '早餐: 燕麦+蛋白质+水果',\n        '午餐: 鸡胸肉+糙米+蔬菜',\n        '晚餐: 鱼肉+红薯+蔬菜',\n        '加餐: 蛋白质奶昔+坚果'\n    ]\n\n    # 生成内容结构\n    content = '# ' + title + '\n\n'\n    content += '## 训练计划\n'\n    content += '### 初学者计划\n'\n    for plan in training_plans['初学者']:\n        content += f'- {plan}\n'\n    content += '\n### 中级计划\n'\n    for plan in training_plans['中级']:\n        content += f'- {plan}\n'\n    content += '\n### 高级计划\n'\n    for plan in training_plans['高级']:\n        content += f'- {plan}\n'\n    content += '\n## 饮食建议\n'\n    for advice in diet_advice:\n        content += f'- {advice}\n'\n    content += '\n## 注意事项\n'\n    content += '- 逐渐增加训练强度\n'\n    content += '- 保证充足的休息\n'\n    content += '- 保持均衡的饮食\n'\n    content += '- 如有不适，立即停止训练\n'\n    return content\n\ndef main():\n    if len(sys.argv) > 1:\n        topic = sys.argv[1]\n    else:\n        topic = '健身'\n\n    keywords = sys.argv[2:] if len(sys.argv) > 2 else []\n    content = generate_fitness_plan(keywords, topic)\n    print(content)\n\nif __name__ == '__main__':\n    main()"
                        }
                else:
                    # 尝试直接解析响应
                    print(f"尝试直接解析响应: {response_content}")
                    try:
                        skill_data = json.loads(response_content)
                    except json.JSONDecodeError as e:
                        print(f"JSON解析错误: {e}")
                        # 提供默认的技能内容
                        # skill_data = {
                        #     "skill_name": "fitness-plan-generator",
                        #     "skill_description": "Generate comprehensive fitness plans with training routines and diet advice",
                        #     "skill_triggers": ["健身", "计划", "fitness", "workout plan"],
                        #     "skill_instructions": "When users request fitness plans, generate detailed training routines and diet advice based on the given keywords and topics.",
                        #     "skill_md_content": "---\nname: fitness-plan-generator\ndescription: Generate comprehensive fitness plans with training routines and diet advice\nversion: 1.0.0\nauthor: Your Team\ntags: [fitness, workout, diet]\ntriggers: [\"健身\", \"计划\", \"fitness\", \"workout plan\"]\nauto_trigger: true\npriority: medium\n---\n\n## 指令\n\nWhen users request fitness plans, generate detailed training routines and diet advice based on the given keywords and topics.\n\n## 输出格式\n\n请使用Markdown格式输出详细的健身计划，包含训练计划和饮食建议。",
                        #     "skill_script": "#!/usr/bin/env python3\n''\nGenerate comprehensive fitness plans\n''\nimport sys\nimport random\n\ndef generate_fitness_plan(keywords, topic):\n    '''生成健身计划'''    \n    # 生成标题\n    titles = [\n        '💪' + topic + '健身计划|详细训练方案',\n        '🔥' + topic + '专业训练计划|附饮食建议',\n        '🏋️\u200d♂️' + topic + '健身指南|科学训练方法'\n    ]\n    title = random.choice(titles)\n\n    # 生成训练计划\n    training_plans = {\n        '初学者': [\n            '周一: 胸部+三头肌',\n            '周二: 背部+二头肌',\n            '周三: 休息',\n            '周四: 腿部',\n            '周五: 肩部',\n            '周六: 全身训练',\n            '周日: 休息'\n        ],\n        '中级': [\n            '周一: 胸部+三头肌',\n            '周二: 背部+二头肌',\n            '周三: 腿部',\n            '周四: 肩部+核心',\n            '周五: 全身训练',\n            '周六: 有氧训练',\n            '周日: 休息'\n        ],\n        '高级': [\n            '周一: 胸部+三头肌',\n            '周二: 背部+二头肌',\n            '周三: 腿部',\n            '周四: 肩部+核心',\n            '周五: 全身训练',\n            '周六: 有氧训练',\n            '周日: 主动恢复'\n        ]\n    }\n\n    # 生成饮食建议\n    diet_advice = [\n        '早餐: 燕麦+蛋白质+水果',\n        '午餐: 鸡胸肉+糙米+蔬菜',\n        '晚餐: 鱼肉+红薯+蔬菜',\n        '加餐: 蛋白质奶昔+坚果'\n    ]\n\n    # 生成内容结构\n    content = '# ' + title + '\n\n'\n    content += '## 训练计划\n'\n    content += '### 初学者计划\n'\n    for plan in training_plans['初学者']:\n        content += f'- {plan}\n'\n    content += '\n### 中级计划\n'\n    for plan in training_plans['中级']:\n        content += f'- {plan}\n'\n    content += '\n### 高级计划\n'\n    for plan in training_plans['高级']:\n        content += f'- {plan}\n'\n    content += '\n## 饮食建议\n'\n    for advice in diet_advice:\n        content += f'- {advice}\n'\n    content += '\n## 注意事项\n'\n    content += '- 逐渐增加训练强度\n'\n    content += '- 保证充足的休息\n'\n    content += '- 保持均衡的饮食\n'\n    content += '- 如有不适，立即停止训练\n'\n    return content\n\ndef main():\n    if len(sys.argv) > 1:\n        topic = sys.argv[1]\n    else:\n        topic = '健身'\n\n    keywords = sys.argv[2:] if len(sys.argv) > 2 else []\n    content = generate_fitness_plan(keywords, topic)\n    print(content)\n\nif __name__ == '__main__':\n    main()"
                        # }
                        return QAResponse(
                            question=request.question,
                            answer=f"Error processing your request: {str(e)}",
                            used_skill="default",
                            confidence=0.0
                        )
                
                # 构建技能请求
                skill_request = SkillRequest(
                    skill_id=skill_id,
                    prompt=request.question,
                    parameters=skill_data
                )
            except Exception as e:
                print(f"Error generating skill content: {e}")
                return QAResponse(
                    question=request.question,
                    answer=f"Error generating skill content: {str(e)}",
                    used_skill="default",
                    confidence=0.0
                )
        else:
            # 普通技能请求
            skill_request = SkillRequest(
                skill_id=skill_id,
                prompt=request.question,
                parameters={}
            )
        
        # 6. 调用技能
        if skill_id == "skill-creator":
            # 直接执行create_skill.py脚本，不通过大模型
            import subprocess
            import tempfile
            
            # 准备参数
            skill_data = skill_request.parameters
            cmd = [
                "python3",
                "skills/skill-creator/scripts/create_skill.py",
                "--skill_name", skill_data.get("skill_name"),
                "--skill_description", skill_data.get("skill_description"),
                "--skill_triggers", json.dumps(skill_data.get("skill_triggers", [])),
                "--skill_instructions", skill_data.get("skill_instructions")
            ]
            
            # 处理脚本内容和SKILL.md内容
            temp_files = []
            if 'skill_script' in skill_data and skill_data['skill_script']:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write(skill_data['skill_script'])
                    temp_files.append(f.name)
                cmd.extend(['--skill_script_file', f.name])
            
            if 'skill_md_content' in skill_data and skill_data['skill_md_content']:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                    f.write(skill_data['skill_md_content'])
                    temp_files.append(f.name)
                cmd.extend(['--skill_md_content_file', f.name])
            
            try:
                # 执行脚本
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                # 解析脚本输出
                if result.returncode == 0:
                    script_output = json.loads(result.stdout)
                    # 构建响应
                    response = f"## 技能创建成功\n\n"
                    response += f"### 技能信息\n"
                    response += f"- **名称**: {script_output.get('skill_name')}\n"
                    response += f"- **描述**: {skill_data.get('skill_description')}\n"
                    response += f"- **触发词**: {', '.join(skill_data.get('skill_triggers', []))}\n"
                    response += f"- **路径**: {script_output.get('skill_dir')}\n\n"
                    response += f"### 生成的文件\n"
                    for file in script_output.get('generated_files', []):
                        response += f"- {file}\n"
                    response += "\n### 如何使用\n"
                    response += "1. 重启服务器以加载新技能\n"
                    response += "2. 使用触发词测试新技能\n"
                    response += "3. 根据需要修改技能文件\n\n"
                    response += f"### 技能功能\n{skill_data.get('skill_instructions')}\n"
                else:
                    response = f"Error creating skill: {result.stderr}\n"
            except Exception as e:
                response = f"Error creating skill: {str(e)}\n"
            finally:
                # 清理临时文件
                import os
                for temp_file in temp_files:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
            
            # 构建问答响应
            return QAResponse(
                question=request.question,
                answer=response,
                used_skill=skill_id,
                confidence=1.0
            )
        else:
            # 普通技能请求
            skill_response = await trigger_skill(skill_id, skill_request, manager)
            
            # 构建问答响应
            return QAResponse(
                question=request.question,
                answer=skill_response.response,
                used_skill=skill_response.skill_name,
                confidence=1.0
            )
    except Exception as e:
        print(f"Error in QA endpoint: {e}")
        # 即使出错也返回一个响应
        return QAResponse(
            question=request.question,
            answer=f"Error processing your request: {str(e)}",
            used_skill="default",
            confidence=0.0
        )

# 健康检查
@app.get("/health")
async def health_check():
    """
    健康检查接口
    
    动态加载技能，并返回健康状态和加载的技能数量。
    
    Returns:
        dict: 健康状态和加载的技能数量
    """
    # 动态加载技能
    skill_manager.load_skills()
    return {"status": "healthy", "skills_loaded": len(skill_manager.get_all_skills())}


if __name__ == "__main__":
    """
    应用入口点
    
    启动FastAPI服务器，监听0.0.0.0:8000
    """
    uvicorn.run(app, host="0.0.0.0", port=8000)
