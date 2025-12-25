from functools import partial
from typing import Callable
from src.graph.state import AgentState

def create_agent_function(agent_function: Callable, agent_id: str) -> Callable[[AgentState], dict]:
    """
    从接受agent_id的agent函数创建一个新函数。

    :param agent_function: 要包装的agent函数。
    :param agent_id: 要传递给agent的ID。
    :return: 一个可以被LangGraph调用的新函数。
    """
    return partial(agent_function, agent_id=agent_id) 