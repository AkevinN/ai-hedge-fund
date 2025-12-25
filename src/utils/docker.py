"""在 Docker 环境中使用 Ollama 模型的工具"""

import requests
import time
from colorama import Fore, Style
import questionary

def ensure_ollama_and_model(model_name: str, ollama_url: str) -> bool:
    """确保 Ollama 模型在目标 Ollama 端点可用"""
    print(f"{Fore.CYAN}使用 Ollama 端点: {ollama_url}{Style.RESET_ALL}")

    # 步骤 1: 检查 Ollama 服务是否可用
    if not is_ollama_available(ollama_url):
        return False

    # 步骤 2: 检查模型是否已可用
    available_models = get_available_models(ollama_url)
    if model_name in available_models:
        print(f"{Fore.GREEN}模型 {model_name} 在 Docker Ollama 容器中可用{Style.RESET_ALL}")
        return True

    # 步骤 3: 模型不可用 - 询问用户是否要下载
    print(f"{Fore.YELLOW}模型 {model_name} 在 Docker Ollama 容器中不可用{Style.RESET_ALL}")

    if not questionary.confirm(f"是否要下载 {model_name}?").ask():
        print(f"{Fore.RED}没有该模型无法继续{Style.RESET_ALL}")
        return False

    # 步骤 4: 下载模型
    return download_model(model_name, ollama_url)


def is_ollama_available(ollama_url: str) -> bool:
    """检查 Docker 环境中 Ollama 服务是否可用"""
    try:
        response = requests.get(f"{ollama_url}/api/version", timeout=5)
        if response.status_code == 200:
            return True

        print(f"{Fore.RED}无法连接到 Ollama 服务: {ollama_url}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}确保 Ollama 服务在您的 Docker 环境中运行{Style.RESET_ALL}")
        return False
    except requests.RequestException as e:
        print(f"{Fore.RED}连接 Ollama 服务时出错: {e}{Style.RESET_ALL}")
        return False


def get_available_models(ollama_url: str) -> list:
    """获取 Docker 环境中可用模型列表"""
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return [m["name"] for m in models]

        print(f"{Fore.RED}从 Ollama 服务获取可用模型失败。状态码: {response.status_code}{Style.RESET_ALL}")
        return []
    except requests.RequestException as e:
        print(f"{Fore.RED}获取可用模型时出错: {e}{Style.RESET_ALL}")
        return []


def download_model(model_name: str, ollama_url: str) -> bool:
    """在 Docker 环境中下载模型"""
    print(f"{Fore.YELLOW}正在下载模型 {model_name} 到 Docker Ollama 容器...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}这可能需要一些时间，请耐心等待{Style.RESET_ALL}")

    # 步骤 1: 发起下载
    try:
        response = requests.post(f"{ollama_url}/api/pull", json={"name": model_name}, timeout=10)
        if response.status_code != 200:
            print(f"{Fore.RED}启动模型下载失败。状态码: {response.status_code}{Style.RESET_ALL}")
            if response.text:
                print(f"{Fore.RED}错误: {response.text}{Style.RESET_ALL}")
            return False
    except requests.RequestException as e:
        print(f"{Fore.RED}启动下载请求时出错: {e}{Style.RESET_ALL}")
        return False

    # 步骤 2: 监控下载进度
    print(f"{Fore.CYAN}下载已启动。定期检查完成情况...{Style.RESET_ALL}")

    total_wait_time = 0
    max_wait_time = 1800  # 最长等待 30 分钟
    check_interval = 10  # 每 10 秒检查一次

    while total_wait_time < max_wait_time:
        # 检查模型是否已下载
        available_models = get_available_models(ollama_url)
        if model_name in available_models:
            print(f"{Fore.GREEN}模型 {model_name} 下载成功{Style.RESET_ALL}")
            return True

        # 再次检查前等待
        time.sleep(check_interval)
        total_wait_time += check_interval

        # 每分钟打印一次状态消息
        if total_wait_time % 60 == 0:
            minutes = total_wait_time // 60
            print(f"{Fore.CYAN}下载进行中... (已过 {minutes} 分钟){Style.RESET_ALL}")

    # 如果到达这里，说明已超时
    print(f"{Fore.RED}等待模型下载完成超时，已等待 {max_wait_time // 60} 分钟{Style.RESET_ALL}")
    return False


def delete_model(model_name: str, ollama_url: str) -> bool:
    """在 Docker 环境中删除模型"""
    print(f"{Fore.YELLOW}正在从 Docker 容器中删除模型 {model_name}...{Style.RESET_ALL}")

    try:
        response = requests.delete(f"{ollama_url}/api/delete", json={"name": model_name}, timeout=10)
        if response.status_code == 200:
            print(f"{Fore.GREEN}模型 {model_name} 删除成功{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}删除模型失败。状态码: {response.status_code}{Style.RESET_ALL}")
            if response.text:
                print(f"{Fore.RED}错误: {response.text}{Style.RESET_ALL}")
            return False
    except requests.RequestException as e:
        print(f"{Fore.RED}删除模型时出错: {e}{Style.RESET_ALL}")
        return False 