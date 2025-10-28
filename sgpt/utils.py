import os
import platform
import shlex
import subprocess
from tempfile import NamedTemporaryFile
from typing import Any, Callable

import typer
from click import BadParameter, UsageError

from sgpt.__version__ import __version__
from sgpt.config import SHELL_GPT_CONFIG_PATH
from sgpt.integration import bash_integration, zsh_integration


def get_edited_prompt() -> str:
    """
    Opens the user's default editor to let them
    input a prompt, and returns the edited text.

    :return: String prompt.
    """
    with NamedTemporaryFile(suffix=".txt", delete=False) as file:
        # Create file and store path.
        file_path = file.name
    editor = os.environ.get("EDITOR", "vim")
    # This will write text to file using $EDITOR.
    os.system(f"{editor} {file_path}")
    # Read file when editor is closed.
    with open(file_path, "r", encoding="utf-8") as file:
        output = file.read()
    os.remove(file_path)
    if not output:
        raise BadParameter("无法从 $EDITOR 得到有效的 PROMPT")
    return output

def extract_provider(file_path: str) -> str:
    """
    Directly use the content of text file to provide prompt

    :return: String prompt.
    """
    if not os.path.isfile(file_path):
        raise BadParameter(f"文件路径 '{file_path}' 不是有效文件")
    if not os.access(file_path,os.R_OK):
        raise BadParameter(f"文件 '{file_path}' 不可读")
    # Read file when editor is closed.
    with open(file_path, "r", encoding="utf-8") as file:
        output = file.read()
    if not output:
        raise BadParameter("无法从 $EDITOR 得到有效的 PROMPT")
    return output

def open_provider(file_path: str) -> str:
    """
    Opens the text file by editor to provide prompt

    :return: String prompt.
    """
    if not os.path.isfile(file_path):
        raise BadParameter(f"文件路径 '{file_path}' 不是有效文件")
    if not os.access(file_path,os.R_OK):
        raise BadParameter(f"文件 '{file_path}' 不可读")
    editor = os.environ.get("EDITOR", "vim")
    # This will write text to file using $EDITOR.
    os.system(f"{editor} {file_path}")
    # Read file when editor is closed.
    with open(file_path, "r", encoding="utf-8") as file:
        output = file.read()
    if not output:
        raise BadParameter("无法从 $EDITOR 得到有效的 PROMPT")
    return output

def run_command(command: str) -> None:
    """
    Runs a command in the user's shell.
    It is aware of the current user's $SHELL.
    :param command: A shell command to run.
    """
    if platform.system() == "Windows":
        is_powershell = len(os.getenv("PSModulePath", "").split(os.pathsep)) >= 3
        full_command = (
            f'powershell.exe -Command "{command}"'
            if is_powershell
            else f'cmd.exe /c "{command}"'
        )
    else:
        shell = os.environ.get("SHELL", "/bin/sh")
        full_command = f"{shell} -c {shlex.quote(command)}"

    os.system(full_command)


def option_callback(func: Callable) -> Callable:  # type: ignore
    def wrapper(cls: Any, value: str) -> None:
        if not value:
            return
        func(cls, value)
        raise typer.Exit()

    return wrapper


@option_callback
def install_shell_integration(*_args: Any) -> None:
    """
    Installs shell integration. Currently only supports ZSH and Bash.
    Allows user to get shell completions in terminal by using hotkey.
    Replaces current "buffer" of the shell with the completion.
    """
    # TODO: Add support for Windows.
    # TODO: Implement updates.
    shell = os.getenv("SHELL", "")
    if "zsh" in shell:
        typer.echo("Installing ZSH integration...")
        with open(os.path.expanduser("~/.zshrc"), "a", encoding="utf-8") as file:
            file.write(zsh_integration)
    elif "bash" in shell:
        typer.echo("Installing Bash integration...")
        with open(os.path.expanduser("~/.bashrc"), "a", encoding="utf-8") as file:
            file.write(bash_integration)
    else:
        raise UsageError("ShellGPT 仅能与 ZSH 或 Bash进行集成。")

    typer.echo("完成！重启你的终端以应用更改。")


@option_callback
def get_sgpt_version(*_args: Any) -> None:
    """
    Displays the current installed version of ShellGPT
    """
    typer.echo(f"ShellGPT {__version__}")


def subprocess_exec_command(command:str) -> str:
    """
    Executes the previous command in the shell and analyze it.
    """
    result=subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True
    )
    res=f"运行命令：{command}\n标准输出：{result.stdout}\n标准错误输出：{result.stderr}\n返回码：{result.returncode}"
    return res

@option_callback
def edit_config(*_args: Any)->None:
    """
    Edit the config file
    """
    try:
        os.system(f"{os.environ.get('EDITOR', 'vim')} {SHELL_GPT_CONFIG_PATH}")
    except Exception as e:
        typer.echo(f"无法打开配置文件：{e}")


def set_file_immutable(file_path):
    """
    设置文件不可变属性（Linux/Unix系统）
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件 {file_path} 不存在")

        # 设置不可变属性
        subprocess.run(['sudo','chattr','+i',file_path],check=True,capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"设置文件不可变失败: {e}")
    except FileNotFoundError as e:
        print(f"文件不存在: {e}")


def remove_file_immutable(file_path):
    """
    移除文件不可变属性
    """
    try:
        subprocess.run(['sudo','chattr','-i',file_path],check=True,capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"移除文件不可变属性失败: {e}")