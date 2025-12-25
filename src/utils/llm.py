"""LLM 辅助函数"""

import json
from pydantic import BaseModel
from src.llm.models import get_model, get_model_info
from src.utils.progress import progress
from src.graph.state import AgentState


def call_llm(
    prompt: any,
    pydantic_model: type[BaseModel],
    agent_name: str | None = None,
    state: AgentState | None = None,
    max_retries: int = 3,
    default_factory=None,
) -> BaseModel:
    """
    使用重试逻辑进行 LLM 调用，处理支持和不支持 JSON 的模型

    参数:
        prompt: 发送给 LLM 的提示
        pydantic_model: 用于结构化输出的 Pydantic 模型类
        agent_name: 可选的代理名称，用于进度更新和模型配置提取
        state: 可选的状态对象，用于提取代理特定的模型配置
        max_retries: 最大重试次数（默认: 3）
        default_factory: 可选的工厂函数，用于在失败时创建默认响应

    返回:
        指定 Pydantic 模型的实例
    """

    # 如果提供了 state 和 agent_name，提取模型配置
    if state and agent_name:
        model_name, model_provider = get_agent_model_config(state, agent_name)
    else:
        # 未提供 state 或 agent_name 时使用系统默认值
        model_name = "gpt-4.1"
        model_provider = "OPENAI"

    # 从状态中提取 API 密钥（如果可用）
    api_keys = None
    if state:
        request = state.get("metadata", {}).get("request")
        if request and hasattr(request, 'api_keys'):
            api_keys = request.api_keys

    model_info = get_model_info(model_name, model_provider)
    llm = get_model(model_name, model_provider, api_keys)

    # 对于不支持 JSON 的模型，我们可以使用结构化输出
    if not (model_info and not model_info.has_json_mode()):
        llm = llm.with_structured_output(
            pydantic_model,
            method="json_mode",
        )

    # 使用重试调用 LLM
    for attempt in range(max_retries):
        try:
            # 调用 LLM
            result = llm.invoke(prompt)

            # 对于不支持 JSON 的模型，需要手动提取和解析 JSON
            if model_info and not model_info.has_json_mode():
                parsed_result = extract_json_from_response(result.content)
                if parsed_result:
                    return pydantic_model(**parsed_result)
            else:
                return result

        except Exception as e:
            if agent_name:
                progress.update_status(agent_name, None, f"错误 - 重试 {attempt + 1}/{max_retries}")

            if attempt == max_retries - 1:
                print(f"LLM 调用在 {max_retries} 次尝试后失败: {e}")
                # 如果提供了 default_factory 则使用它，否则创建基本默认值
                if default_factory:
                    return default_factory()
                return create_default_response(pydantic_model)

    # 由于上面的重试逻辑，这里永远不应该被执行到
    return create_default_response(pydantic_model)


def create_default_response(model_class: type[BaseModel]) -> BaseModel:
    """基于模型字段创建安全的默认响应"""
    default_values = {}
    for field_name, field in model_class.model_fields.items():
        if field.annotation == str:
            default_values[field_name] = "分析出错，使用默认值"
        elif field.annotation == float:
            default_values[field_name] = 0.0
        elif field.annotation == int:
            default_values[field_name] = 0
        elif hasattr(field.annotation, "__origin__") and field.annotation.__origin__ == dict:
            default_values[field_name] = {}
        else:
            # 对于其他类型（如 Literal），尝试使用第一个允许的值
            if hasattr(field.annotation, "__args__"):
                default_values[field_name] = field.annotation.__args__[0]
            else:
                default_values[field_name] = None

    return model_class(**default_values)


def extract_json_from_response(content: str) -> dict | None:
    """从 Markdown 格式的响应中提取 JSON"""
    try:
        json_start = content.find("```json")
        if json_start != -1:
            json_text = content[json_start + 7 :]  # 跳过 ```json
            json_end = json_text.find("```")
            if json_end != -1:
                json_text = json_text[:json_end].strip()
                return json.loads(json_text)
    except Exception as e:
        print(f"从响应中提取 JSON 时出错: {e}")
    return None


def get_agent_model_config(state, agent_name):
    """
    从状态中获取特定代理的模型配置
    如果代理特定配置不可用，则回退到全局模型配置
    始终返回有效的 model_name 和 model_provider 值
    """
    request = state.get("metadata", {}).get("request")

    if request and hasattr(request, 'get_agent_model_config'):
        # 获取代理特定的模型配置
        model_name, model_provider = request.get_agent_model_config(agent_name)
        # 确保我们有有效的值
        if model_name and model_provider:
            return model_name, model_provider.value if hasattr(model_provider, 'value') else str(model_provider)

    # 回退到全局配置（系统默认值）
    model_name = state.get("metadata", {}).get("model_name") or "gpt-4.1"
    model_provider = state.get("metadata", {}).get("model_provider") or "OPENAI"

    # 如有必要，将枚举转换为字符串
    if hasattr(model_provider, 'value'):
        model_provider = model_provider.value

    return model_name, model_provider
