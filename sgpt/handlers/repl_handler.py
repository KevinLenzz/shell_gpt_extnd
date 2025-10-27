from typing import Any

import typer
from click import Abort
from rich import print as rich_print
from rich.rule import Rule

from ..role import DefaultRoles, SystemRole
from ..utils import run_command
from .chat_handler import ChatHandler
from .default_handler import DefaultHandler


class ReplHandler(ChatHandler):
    def __init__(self, chat_id: str, role: SystemRole, markdown: bool) -> None:
        super().__init__(chat_id, role, markdown)

    @classmethod
    def _get_multiline_input(cls) -> str:
        multiline_input = ""
        while (user_input := typer.prompt("...", prompt_suffix="")) != '"""':
            multiline_input += user_input + "\n"
        return multiline_input

    @classmethod
    def _testmode_get_multiline_input(cls,lines: list,i: int) -> str:
        multiline_input=""
        while (user_input:=lines[i])!='"""':
            print(">>> "+user_input)
            multiline_input+=user_input+"\n"
            i+=1
        return multiline_input,i+1

    def handle(self, init_prompt: str, **kwargs: Any) -> None:  # type: ignore
        if self.initiated:
            rich_print(Rule(title="Chat History", style="bold magenta"))
            self.show_messages(self.chat_id, self.markdown)
            rich_print(Rule(style="bold magenta"))

        info_message = (
            "进入 REPL 模式, 按 Ctrl+C 来退出."
            if not self.role.name == DefaultRoles.SHELL.value
            else (
                "进入 REPL 模式, 输入 [e] 来执行命令 "
                "或者 [d] 来描述命令, 按 Ctrl+C 来退出."
            )
        )
        typer.secho(info_message, fg="yellow")
        full_completion=""
        if init_prompt:
            rich_print(Rule(title="Input", style="bold purple"))
            typer.echo(init_prompt)
            rich_print(Rule(style="bold purple"))
            init_lines=init_prompt.split("\n")
            i=0
            row=len(init_lines)
            while i<row:
                prompt=init_lines[i]
                print(">>> "+prompt)
                i+=1
                if prompt=='"""':
                    prompt,i=self._testmode_get_multiline_input(init_lines,i)
                if prompt=="exit()":
                    raise typer.Exit()
                if self.role.name==DefaultRoles.SHELL.value and prompt=="e":
                    typer.echo()
                    run_command(full_completion)
                    typer.echo()
                    rich_print(Rule(style="bold magenta"))
                elif self.role.name==DefaultRoles.SHELL.value and prompt=="d":
                    DefaultHandler(
                        DefaultRoles.DESCRIBE_SHELL.get_role(),self.markdown
                    ).handle(prompt=full_completion,**kwargs)
                else:
                    full_completion=super().handle(prompt=prompt,**kwargs)
            init_prompt=""
        while True:
            # Infinite loop until user exits with Ctrl+C.
            prompt=typer.prompt(">>>",prompt_suffix=" ")
            if prompt=='"""':
                prompt=self._get_multiline_input()
            if prompt=="exit()":
                raise typer.Exit()
            if init_prompt:
                prompt=f"{init_prompt}\n\n\n{prompt}"
                init_prompt=""
            if self.role.name==DefaultRoles.SHELL.value and prompt=="e":
                typer.echo()
                run_command(full_completion)
                typer.echo()
                rich_print(Rule(style="bold magenta"))
            elif self.role.name==DefaultRoles.SHELL.value and prompt=="d":
                DefaultHandler(
                    DefaultRoles.DESCRIBE_SHELL.get_role(),self.markdown
                ).handle(prompt=full_completion,**kwargs)
            else:
                full_completion=super().handle(prompt=prompt,**kwargs)
