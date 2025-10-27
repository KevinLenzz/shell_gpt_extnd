import os

# To allow users to use arrow keys in the REPL.
import readline  # noqa: F401
import sys

import typer
from click import BadArgumentUsage
from click.types import Choice
from prompt_toolkit import PromptSession

from sgpt.config import cfg
from sgpt.function import get_openai_schemas
from sgpt.handlers.chat_handler import ChatHandler
from sgpt.handlers.default_handler import DefaultHandler
from sgpt.handlers.repl_handler import ReplHandler
from sgpt.llm_functions.init_functions import install_functions as inst_funcs
from sgpt.role import DefaultRoles, SystemRole
from sgpt.utils import (
    get_edited_prompt,
    get_sgpt_version,
    install_shell_integration,
    run_command,
)


def main(
    prompt: str = typer.Argument(
        "",
        show_default=False,
        help="用于内容生成的您的输入",
        rich_help_panel="参数"
    ),
    model: str = typer.Option(
        cfg.get("DEFAULT_MODEL"),
        help="切换成指定模型",
        rich_help_panel="选项"
    ),
    temperature: float = typer.Option(
        0.0,
        min=0.0,
        max=2.0,
        help="温度（生成内容的随机性）",
        rich_help_panel="选项"
    ),
    top_p: float = typer.Option(
        1.0,
        min=0.0,
        max=1.0,
        help="核采样，模型会从累积概率大于等于指定阈值的候选词中进行随机选择",
        rich_help_panel="选项"
    ),
    md: bool = typer.Option(
        cfg.get("PRETTIFY_MARKDOWN") == "true",
        help="美化Markdown格式的输出",
        rich_help_panel="选项"
    ),
    shell: bool = typer.Option(
        False,
        "--shell",
        "-s",
        help="生成并执行shell命令",
        rich_help_panel="辅助选项",
    ),
    interaction: bool = typer.Option(
        cfg.get("SHELL_INTERACTION") == "true",
        help="使用交互模式的--shell选项",
        rich_help_panel="辅助选项",
    ),
    describe_shell: bool = typer.Option(
        False,
        "--describe-shell",
        "-d",
        help="描述一个shell命令",
        rich_help_panel="辅助选项",
    ),
    code: bool = typer.Option(
        False,
        "--code",
        "-c",
        help="仅生成代码",
        rich_help_panel="辅助选项",
    ),
    functions: bool = typer.Option(
        cfg.get("OPENAI_USE_FUNCTIONS") == "true",
        help="允许function调用",
        rich_help_panel="辅助选项",
    ),
    editor: bool = typer.Option(
        False,
        help="打开 $EDITOR 以供给 prompt",
        rich_help_panel="应用选项",
    ),
    cache: bool = typer.Option(
        True,
        help="缓存完整结果",
        rich_help_panel="选项",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        help="输出版本信息",
        callback=get_sgpt_version,
        rich_help_panel="选项",
    ),
    chat: str = typer.Option(
        None,
        help="依据 id 继续对话, " '使用 "temp" 进行快速会话',
        rich_help_panel="Chat选项",
    ),
    repl: str = typer.Option(
        None,
        help="启动REPL（读取-评估-打印循环）会话",
        rich_help_panel="Chat选项",
    ),
    show_chat: str = typer.Option(
        None,
        help="显示指定chat id的所有消息",
        rich_help_panel="Chat选项",
    ),
    list_chats: bool = typer.Option(
        False,
        "--list-chats",
        "-lc",
        help="列出所有现有chat id",
        callback=ChatHandler.list_ids,
        rich_help_panel="Chat选项",
    ),
    role: str = typer.Option(
        None,
        help="已对接模型的系统角色",
        rich_help_panel="选项",
    ),
    create_role: str = typer.Option(
        None,
        help="创建角色",
        callback=SystemRole.create,
        rich_help_panel="角色选项",
    ),
    show_role: str = typer.Option(
        None,
        help="显示角色",
        callback=SystemRole.show,
        rich_help_panel="角色选项",
    ),
    list_roles: bool = typer.Option(
        False,
        "--list-roles",
        "-lr",
        help="列出所有角色",
        callback=SystemRole.list,
        rich_help_panel="角色选项",
    ),
    install_integration: bool = typer.Option(
        False,
        help="安装shell集成（仅限ZSH和Bash）",
        callback=install_shell_integration,
        hidden=True,  # Hiding since should be used only once.
        rich_help_panel="选项",
    ),
    install_functions: bool = typer.Option(
        False,
        help="安装默认functions",
        callback=inst_funcs,
        hidden=True,  # Hiding since should be used only once.
        rich_help_panel="选项",
    ),
) -> None:
    stdin_passed = not sys.stdin.isatty()

    if stdin_passed:
        stdin = ""
        # TODO: This is very hacky.
        # In some cases, we need to pass stdin along with inputs.
        # When we want part of stdin to be used as a init prompt,
        # but rest of the stdin to be used as a inputs. For example:
        # echo "hello\n__sgpt__eof__\nThis is input" | sgpt --repl temp
        # In this case, "hello" will be used as a init prompt, and
        # "This is input" will be used as "interactive" input to the REPL.
        # This is useful to test REPL with some initial context.
        try:
            for line in sys.stdin:
                if "__sgpt__eof__" in line:
                    break
                stdin += line
        except EOFError:
            pass #使用源码进行测试
        prompt = f"{stdin}\n\n{prompt}" if prompt else stdin
        try:
            # Switch to stdin for interactive input.
            if os.name == "posix":
                sys.stdin = open("/dev/tty", "r")
            elif os.name == "nt":
                sys.stdin = open("CON", "r")
        except OSError:
            # Non-interactive shell.
            pass

    if show_chat:
        ChatHandler.show_messages(show_chat, md)

    if sum((shell, describe_shell, code)) > 1:
        raise BadArgumentUsage(
            "Only one of --shell, --describe-shell, and --code options can be used at a time."
        )

    if chat and repl:
        raise BadArgumentUsage("--chat and --repl options cannot be used together.")

    if editor and stdin_passed:
        raise BadArgumentUsage("--editor option cannot be used with stdin input.")

    if editor:
        prompt = get_edited_prompt()

    role_class = (
        DefaultRoles.check_get(shell, describe_shell, code)
        if not role
        else SystemRole.get(role)
    )

    function_schemas = (get_openai_schemas() or None) if functions else None

    if repl:
        # Will be in infinite loop here until user exits with Ctrl+C.
        ReplHandler(repl, role_class, md).handle(
            init_prompt=prompt,
            model=model,
            temperature=temperature,
            top_p=top_p,
            caching=cache,
            functions=function_schemas,
        )

    if chat:
        full_completion = ChatHandler(chat, role_class, md).handle(
            prompt=prompt,
            model=model,
            temperature=temperature,
            top_p=top_p,
            caching=cache,
            functions=function_schemas,
        )
    else:
        full_completion = DefaultHandler(role_class, md).handle(
            prompt=prompt,
            model=model,
            temperature=temperature,
            top_p=top_p,
            caching=cache,
            functions=function_schemas,
        )

    session: PromptSession[str] = PromptSession()

    while shell and interaction:
        option = typer.prompt(
            text="[E]xecute, [M]odify, [D]escribe, [A]bort",
            type=Choice(("e", "m", "d", "a", "y"), case_sensitive=False),
            default="e" if cfg.get("DEFAULT_EXECUTE_SHELL_CMD") == "true" else "a",
            show_choices=False,
            show_default=False,
        )
        if option in ("e", "y"):
            # "y" option is for keeping compatibility with old version.
            run_command(full_completion)
        elif option == "m":
            full_completion = session.prompt("", default=full_completion)
            continue
        elif option == "d":
            DefaultHandler(DefaultRoles.DESCRIBE_SHELL.get_role(), md).handle(
                full_completion,
                model=model,
                temperature=temperature,
                top_p=top_p,
                caching=cache,
                functions=function_schemas,
            )
            continue
        break


def entry_point() -> None:
    typer.run(main)


if __name__ == "__main__":
    entry_point()
