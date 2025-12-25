"""Utilities for working with Ollama models"""

import platform
import subprocess
import requests
import time
from typing import List
import questionary
from colorama import Fore, Style
import os
from . import docker

# Constants
DEFAULT_OLLAMA_SERVER_URL = "http://localhost:11434"


def _get_ollama_base_url() -> str:
    """Return the configured Ollama base URL, trimming any trailing slash."""
    url = os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_SERVER_URL)
    if not url:
        url = DEFAULT_OLLAMA_SERVER_URL
    return url.rstrip("/")


def _get_ollama_endpoint(path: str) -> str:
    """Build a full Ollama API endpoint from the configured base URL."""
    base = _get_ollama_base_url()
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base}{path}"


OLLAMA_DOWNLOAD_URL = {"darwin": "https://ollama.com/download/darwin", "windows": "https://ollama.com/download/windows", "linux": "https://ollama.com/download/linux"}  # macOS  # Windows  # Linux
INSTALLATION_INSTRUCTIONS = {"darwin": "curl -fsSL https://ollama.com/install.sh | sh", "windows": "# Download from https://ollama.com/download/windows and run the installer", "linux": "curl -fsSL https://ollama.com/install.sh | sh"}


def is_ollama_installed() -> bool:
    """Check if Ollama is installed on the system."""
    system = platform.system().lower()

    if system == "darwin" or system == "linux":  # macOS or Linux
        try:
            result = subprocess.run(["which", "ollama"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return result.returncode == 0
        except Exception:
            return False
    elif system == "windows":  # Windows
        try:
            result = subprocess.run(["where", "ollama"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
            return result.returncode == 0
        except Exception:
            return False
    else:
        return False  # Unsupported OS


def is_ollama_server_running() -> bool:
    """Check if the Ollama server is running."""
    endpoint = _get_ollama_endpoint("/api/tags")
    try:
        response = requests.get(endpoint, timeout=2)
        return response.status_code == 200
    except requests.RequestException:
        return False


def get_locally_available_models() -> List[str]:
    """Get a list of models that are already downloaded locally."""
    if not is_ollama_server_running():
        return []

    try:
        endpoint = _get_ollama_endpoint("/api/tags")
        response = requests.get(endpoint, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [model["name"] for model in data["models"]] if "models" in data else []
        return []
    except requests.RequestException:
        return []


def start_ollama_server() -> bool:
    """Start the Ollama server if it's not already running."""
    if is_ollama_server_running():
        print(f"{Fore.GREEN}Ollama 服务器已在运行{Style.RESET_ALL}")
        return True

    system = platform.system().lower()

    try:
        if system == "darwin" or system == "linux":  # macOS or Linux
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        elif system == "windows":  # Windows
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        else:
            print(f"{Fore.RED}不支持的操作系统: {system}{Style.RESET_ALL}")
            return False

        # Wait for server to start
        for _ in range(10):  # Try for 10 seconds
            if is_ollama_server_running():
                print(f"{Fore.GREEN}Ollama 服务器启动成功{Style.RESET_ALL}")
                return True
            time.sleep(1)

        print(f"{Fore.RED}启动 Ollama 服务器失败，等待服务器可用超时{Style.RESET_ALL}")
        return False
    except Exception as e:
        print(f"{Fore.RED}启动 Ollama 服务器时出错: {e}{Style.RESET_ALL}")
        return False


def install_ollama() -> bool:
    """Install Ollama on the system."""
    system = platform.system().lower()
    if system not in OLLAMA_DOWNLOAD_URL:
        print(f"{Fore.RED}不支持自动安装的操作系统: {system}{Style.RESET_ALL}")
        print(f"请访问 https://ollama.com/download 手动安装 Ollama")
        return False

    if system == "darwin":  # macOS
        print(f"{Fore.YELLOW}Mac 版 Ollama 可以通过应用程序下载{Style.RESET_ALL}")

        # Default to offering the app download first for macOS users
        if questionary.confirm("是否要下载 Ollama 应用程序?", default=True).ask():
            try:
                import webbrowser

                webbrowser.open(OLLAMA_DOWNLOAD_URL["darwin"])
                print(f"{Fore.YELLOW}请下载并安装应用程序，然后重新启动此程序{Style.RESET_ALL}")
                print(f"{Fore.CYAN}安装后，您可能需要先打开一次 Ollama 应用程序才能继续{Style.RESET_ALL}")

                # Ask if they want to try continuing after installation
                if questionary.confirm("您是否已安装 Ollama 应用程序并至少打开过一次?", default=False).ask():
                    # Check if it's now installed
                    if is_ollama_installed() and start_ollama_server():
                        print(f"{Fore.GREEN}Ollama 已正确安装并正在运行！{Style.RESET_ALL}")
                        return True
                    else:
                        print(f"{Fore.RED}未检测到 Ollama 安装，请在安装 Ollama 后重新启动此应用程序{Style.RESET_ALL}")
                        return False
                return False
            except Exception as e:
                print(f"{Fore.RED}无法打开浏览器: {e}{Style.RESET_ALL}")
                return False
        else:
            # Only offer command-line installation as a fallback for advanced users
            if questionary.confirm("是否要尝试命令行安装? (适合高级用户)", default=False).ask():
                print(f"{Fore.YELLOW}正在尝试命令行安装...{Style.RESET_ALL}")
                try:
                    install_process = subprocess.run(["bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                    if install_process.returncode == 0:
                        print(f"{Fore.GREEN}Ollama 已通过命令行成功安装{Style.RESET_ALL}")
                        return True
                    else:
                        print(f"{Fore.RED}命令行安装失败，请使用应用程序下载方式{Style.RESET_ALL}")
                        return False
                except Exception as e:
                    print(f"{Fore.RED}命令行安装时出错: {e}{Style.RESET_ALL}")
                    return False
            return False
    elif system == "linux":  # Linux
        print(f"{Fore.YELLOW}正在安装 Ollama...{Style.RESET_ALL}")
        try:
            # Run the installation command as a single command
            install_process = subprocess.run(["bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if install_process.returncode == 0:
                print(f"{Fore.GREEN}Ollama 安装成功{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.RED}Ollama 安装失败，错误: {install_process.stderr}{Style.RESET_ALL}")
                return False
        except Exception as e:
            print(f"{Fore.RED}Ollama 安装时出错: {e}{Style.RESET_ALL}")
            return False
    elif system == "windows":  # Windows
        print(f"{Fore.YELLOW}Windows 不支持自动安装{Style.RESET_ALL}")
        print(f"请从以下地址下载并安装 Ollama: {OLLAMA_DOWNLOAD_URL['windows']}")

        # Ask if they want to open the download page
        if questionary.confirm("是否要在浏览器中打开 Ollama 下载页面?").ask():
            try:
                import webbrowser

                webbrowser.open(OLLAMA_DOWNLOAD_URL["windows"])
                print(f"{Fore.YELLOW}安装完成后，请重新启动此应用程序{Style.RESET_ALL}")

                # Ask if they want to try continuing after installation
                if questionary.confirm("您是否已安装 Ollama?", default=False).ask():
                    # Check if it's now installed
                    if is_ollama_installed() and start_ollama_server():
                        print(f"{Fore.GREEN}Ollama 已正确安装并正在运行！{Style.RESET_ALL}")
                        return True
                    else:
                        print(f"{Fore.RED}未检测到 Ollama 安装，请在安装 Ollama 后重新启动此应用程序{Style.RESET_ALL}")
                        return False
            except Exception as e:
                print(f"{Fore.RED}无法打开浏览器: {e}{Style.RESET_ALL}")
        return False

    return False


def download_model(model_name: str) -> bool:
    """Download an Ollama model."""
    if not is_ollama_server_running():
        if not start_ollama_server():
            return False

    print(f"{Fore.YELLOW}正在下载模型 {model_name}...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}这可能需要一些时间，取决于您的网络速度和模型大小{Style.RESET_ALL}")
    print(f"{Fore.CYAN}下载正在后台进行，请耐心等待...{Style.RESET_ALL}")

    try:
        # Use the Ollama CLI to download the model
        process = subprocess.Popen(
            ["ollama", "pull", model_name],
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,  # Redirect stderr to stdout to capture all output
            text=True,
            bufsize=1,  # Line buffered
            encoding='utf-8',  # Explicitly use UTF-8 encoding
            errors='replace'   # Replace any characters that cannot be decoded
        )
        
        # Show some progress to the user
        print(f"{Fore.CYAN}下载进度:{Style.RESET_ALL}")

        # For tracking progress
        last_percentage = 0
        last_phase = ""
        bar_length = 40

        while True:
            output = process.stdout.readline()
            if output == "" and process.poll() is not None:
                break
            if output:
                output = output.strip()
                # Try to extract percentage information using a more lenient approach
                percentage = None
                current_phase = None

                # Example patterns in Ollama output:
                # "downloading: 23.45 MB / 42.19 MB [================>-------------] 55.59%"
                # "downloading model: 76%"
                # "pulling manifest: 100%"

                # Check for percentage in the output
                import re

                percentage_match = re.search(r"(\d+(\.\d+)?)%", output)
                if percentage_match:
                    try:
                        percentage = float(percentage_match.group(1))
                    except ValueError:
                        percentage = None

                # Try to determine the current phase (downloading, extracting, etc.)
                phase_match = re.search(r"^([a-zA-Z\s]+):", output)
                if phase_match:
                    current_phase = phase_match.group(1).strip()

                # If we found a percentage, display a progress bar
                if percentage is not None:
                    # Only update if there's a significant change (avoid flickering)
                    if abs(percentage - last_percentage) >= 1 or (current_phase and current_phase != last_phase):
                        last_percentage = percentage
                        if current_phase:
                            last_phase = current_phase

                        # Create a progress bar
                        filled_length = int(bar_length * percentage / 100)
                        bar = "█" * filled_length + "░" * (bar_length - filled_length)

                        # Build the status line with the phase if available
                        phase_display = f"{Fore.CYAN}{last_phase.capitalize()}{Style.RESET_ALL}: " if last_phase else ""
                        status_line = f"\r{phase_display}{Fore.GREEN}{bar}{Style.RESET_ALL} {Fore.YELLOW}{percentage:.1f}%{Style.RESET_ALL}"

                        # Print the status line without a newline to update in place
                        print(status_line, end="", flush=True)
                else:
                    # If we couldn't extract a percentage but have identifiable output
                    if "download" in output.lower() or "extract" in output.lower() or "pulling" in output.lower():
                        # Don't print a newline for percentage updates
                        if "%" in output:
                            print(f"\r{Fore.GREEN}{output}{Style.RESET_ALL}", end="", flush=True)
                        else:
                            print(f"{Fore.GREEN}{output}{Style.RESET_ALL}")

        # Wait for the process to finish
        return_code = process.wait()

        # Ensure we print a newline after the progress bar
        print()

        if return_code == 0:
            print(f"{Fore.GREEN}模型 {model_name} 下载成功！{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}下载模型 {model_name} 失败，请检查网络连接并重试{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"\n{Fore.RED}下载模型 {model_name} 时出错: {e}{Style.RESET_ALL}")
        return False


def ensure_ollama_and_model(model_name: str) -> bool:
    """Ensure Ollama is installed, running, and the requested model is available."""
    ollama_url = _get_ollama_base_url()
    env_override = os.environ.get("OLLAMA_BASE_URL")

    # If an explicit base URL is provided (including Docker defaults), use the remote workflow
    if env_override or ollama_url.startswith("http://ollama:") or ollama_url.startswith("http://host.docker.internal:"):
        return docker.ensure_ollama_and_model(model_name, ollama_url)

    # Regular flow for environments that rely on the local Ollama install
    # Check if Ollama is installed
    if not is_ollama_installed():
        print(f"{Fore.YELLOW}您的系统未安装 Ollama{Style.RESET_ALL}")
        
        # Ask if they want to install it
        if questionary.confirm("是否要安装 Ollama?").ask():
            if not install_ollama():
                return False
        else:
            print(f"{Fore.RED}使用本地模型需要 Ollama{Style.RESET_ALL}")
            return False
    
    # Make sure the server is running
    if not is_ollama_server_running():
        print(f"{Fore.YELLOW}正在启动 Ollama 服务器...{Style.RESET_ALL}")
        if not start_ollama_server():
            return False
    
    # Check if the model is already downloaded
    available_models = get_locally_available_models()
    if model_name not in available_models:
        print(f"{Fore.YELLOW}模型 {model_name} 本地不可用{Style.RESET_ALL}")
        
        # Ask if they want to download it
        model_size_info = ""
        if "70b" in model_name:
            model_size_info = " 这是一个大型模型 (可能有几GB)，下载可能需要较长时间"
        elif "34b" in model_name or "8x7b" in model_name:
            model_size_info = " 这是一个中型模型 (1-2 GB)，下载可能需要几分钟"
        
        if questionary.confirm(f"是否要下载模型 {model_name}?{model_size_info} 下载将在后台进行").ask():
            return download_model(model_name)
        else:
            print(f"{Fore.RED}需要该模型才能继续{Style.RESET_ALL}")
            return False
    
    return True


def delete_model(model_name: str) -> bool:
    """Delete a locally downloaded Ollama model."""
    # Check if we're running in Docker
    in_docker = os.environ.get("OLLAMA_BASE_URL", "").startswith("http://ollama:") or os.environ.get("OLLAMA_BASE_URL", "").startswith("http://host.docker.internal:")
    
    # In Docker environment, delegate to docker module
    if in_docker:
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
        return docker.delete_model(model_name, ollama_url)
        
    # Non-Docker environment
    if not is_ollama_server_running():
        if not start_ollama_server():
            return False
    
    print(f"{Fore.YELLOW}正在删除模型 {model_name}...{Style.RESET_ALL}")
    
    try:
        # Use the Ollama CLI to delete the model
        process = subprocess.run(["ollama", "rm", model_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if process.returncode == 0:
            print(f"{Fore.GREEN}模型 {model_name} 删除成功{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}删除模型 {model_name} 失败，错误: {process.stderr}{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}删除模型 {model_name} 时出错: {e}{Style.RESET_ALL}")
        return False


# Add this at the end of the file for command-line usage
if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Ollama 模型管理器")
    parser.add_argument("--check-model", help="检查模型是否存在，如需要则下载")
    args = parser.parse_args()

    if args.check_model:
        print(f"正在确保 Ollama 已安装且模型 {args.check_model} 可用...")
        result = ensure_ollama_and_model(args.check_model)
        sys.exit(0 if result else 1)
    else:
        print("未指定操作，使用 --check-model 检查模型是否存在")
        sys.exit(1)
