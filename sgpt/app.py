import os

# To allow users to use arrow keys in the REPL.
import readline  # noqa: F401
import sys

import typer
from click import BadArgumentUsage
from click.types import Choice
from prompt_toolkit import PromptSession

from sgpt.config import cfg,ROLE_STORAGE_PATH,CHAT_CACHE_PATH
from sgpt.function import get_openai_schemas
from sgpt.handlers.chat_handler import ChatHandler,ChatSession
from sgpt.handlers.default_handler import DefaultHandler
from sgpt.handlers.repl_handler import ReplHandler
from sgpt.llm_functions.init_functions import install_functions as inst_funcs
from sgpt.role import DefaultRoles, SystemRole
from sgpt.batch import BatchProcessor, process_batch_questions
from sgpt.utils import (
    get_edited_prompt,
    get_sgpt_version,
    install_shell_integration,
    run_command,
    subprocess_exec_command,
    open_provider,
    extract_provider,
    edit_config
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
        help="打开"+os.environ.get("EDITOR", "vim")+"以供给 prompt",
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
    sub_exec: str= typer.Option(
        None,
"--sub-exec",
        "-sx",
        help="在子进程执行命令并让sgpt分析",
        rich_help_panel="辅助选项",
    ),
    provide: str = typer.Option(
        None,
        help="使用现有文件提供prompt",
        rich_help_panel="应用选项",
    ),
    edit_config: bool = typer.Option(
        False,
        "--edit-config",
        help="编辑配置文件",
        callback=edit_config,
        rich_help_panel="选项",
    ),
    del_role: str = typer.Option(
        None,
        help="删除角色",
        rich_help_panel="角色选项",
    ),
    del_role_a: bool = typer.Option(
        False,
        "--del-role-a",
        help="删除所有角色",
        rich_help_panel="角色选项",
    ),
    del_chat: str = typer.Option(
        None,
        help="删除Chat",
        rich_help_panel="Chat选项",
    ),
    del_chat_a: bool = typer.Option(
        False,
"--del-chat-a",
        help="删除所有Chat",
        rich_help_panel="Chat选项",
    ),
    batch: str = typer.Option(
        None,
        "--batch",
        "-b",
        help="批量处理模式，从文件读取多个问题（支持TXT/JSON/CSV）\n结果会自动保存到同目录",
        rich_help_panel="批量选项",
    ),
    batch_output: str = typer.Option(
        None,
        "--batch-output",
        "-bo",
        help="批量处理结果输出文件路径",
        rich_help_panel="批量选项",
    ),
    batch_format: str = typer.Option(
        "txt",
        "--batch-format",
        "-bf",
        help="批量处理结果输出格式（txt/json/md）",
        rich_help_panel="批量选项",
    ),
    batch_no_print: bool = typer.Option(
False,
        "--batch-no-print",
        "-bnp",
        help="结果不保存到文件",
        rich_help_panel="批量选项",
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
    if sub_exec:
        prompt = f"{subprocess_exec_command(sub_exec)}\n\n将标准输出（如果有）和标准错误输出（如果有）美化并输出，分析以上命令及其结果，如果有错误就指出并纠正\n\n{prompt}"

    if del_role:
        SystemRole.get(del_role).delete()
    if del_role_a:
        typer.confirm(
            f'确定删除所有角色文件吗？',
            abort=True,
        )
        for item in ROLE_STORAGE_PATH.iterdir():
            if item.is_file():
                try:
                    item.unlink()
                    typer.echo(f"删除角色文件 {item} 成功")
                except OSError:
                    typer.echo(f"删除角色文件 {item} 失败")
        typer.echo(f"删除所有角色文件成功")
        raise typer.Exit
    if del_chat:
        ChatSession.invalidate(del_chat)
    if del_chat_a:
        typer.confirm(
            f'确定删除所有Chat文件吗？',
            abort=True,
        )
        for item in CHAT_CACHE_PATH.iterdir():
            if item.is_file():
                try:
                    item.unlink()
                    typer.echo(f"删除Chat文件 {item} 成功")
                except OSError:
                    typer.echo(f"删除Chat文件 {item} 失败")
        typer.echo(f"删除所有Chat文件成功")
        raise typer.Exit

    if show_chat:
        ChatHandler.show_messages(show_chat, md)

    # 批量处理模式
    if batch:
        from pathlib import Path
        from rich.console import Console

        console = Console()

        # 检查文件是否存在
        batch_file = Path(batch)
        if not batch_file.exists():
            raise BadArgumentUsage(f"批量处理文件不存在: {batch}")

        # 检查是否与其他模式冲突
        if chat or repl:
            raise BadArgumentUsage("--batch 不能与 --chat 或 --repl 一起使用")

        console.print(f"[cyan]📂 读取批量问题文件: {batch_file}[/cyan]")

        try:
            # 读取问题
            processor = BatchProcessor(Path(batch_output) if batch_output else None)
            questions = processor.read_questions_from_file(batch_file)

            console.print(f"[green]✓ 成功读取 {len(questions)} 个问题[/green]\n")

            # 确定使用的角色
            role_class = (
                DefaultRoles.check_get(shell, describe_shell, code)
                if not role
                else SystemRole.get(role)
            )

            # 创建处理器
            handler = DefaultHandler(role_class, md)

            # 批量处理
            processor = process_batch_questions(
                questions=questions,
                handler=handler,
                show_progress=not (code or shell),
                model=model,
                temperature=temperature,
                top_p=top_p,
                caching=cache,
                functions=(get_openai_schemas() or None) if functions else None,
                output=Path(batch_output) if batch_output else None
            )
            if batch_no_print:
                console.print(f"\n[bold yellow]结果已舍弃[/bold yellow]")
            else:
                # 保存结果
                output_file = processor.save_results(batch_format)

                # 打印摘要
                processor.print_summary()
                console.print(f"\n[bold green]✓ 结果已保存到: {output_file}[/bold green]")

        except Exception as e:
            console.print(f"[bold red]✗ 批量处理失败: {e}[/bold red]")
            raise typer.Exit(1)

        raise typer.Exit()

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

    if editor and provide:
        prompt = open_provider(provide)

    elif editor:
        prompt = get_edited_prompt()

    elif provide:
        prompt = extract_provider(provide)

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
