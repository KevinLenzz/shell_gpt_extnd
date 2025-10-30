import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()


class BatchProcessor:
    """批量处理问题的处理器"""

    def __init__(self, output_path: Optional[Path] = None):
        """
        初始化批量处理器
        
        :param output_path: 输出文件路径，如果为None则自动生成
        """
        self.output_path = output_path or self._generate_output_path()
        self.results: List[Dict[str, str]] = []

    def _generate_output_path(self) -> Path:
        """生成默认的输出文件路径"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return Path(f"batch_results_{timestamp}.txt")

    def read_questions_from_file(self, file_path: Path) -> List[str]:
        """
        从文件读取问题列表
        
        支持的格式：
        - TXT: 每行一个问题
        - JSON: {"questions": ["问题1", "问题2"]} 或 [{"question": "问题1"}, ...]
        - CSV: 第一列为问题
        
        :param file_path: 问题文件路径
        :return: 问题列表
        """
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        suffix = file_path.suffix.lower()
        
        try:
            if suffix == ".txt":
                return self._read_txt(file_path)
            elif suffix == ".json":
                return self._read_json(file_path)
            elif suffix == ".csv":
                return self._read_csv(file_path)
            else:
                # 尝试作为文本文件读取
                return self._read_txt(file_path)
        except Exception as e:
            raise ValueError(f"读取文件失败: {e}")

    def _read_txt(self, file_path: Path) -> List[str]:
        """读取TXT格式的问题文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # 过滤空行和注释
        questions = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                questions.append(line)
        
        return questions

    def _read_json(self, file_path: Path) -> List[str]:
        """读取JSON格式的问题文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 支持两种格式
        if isinstance(data, dict) and "questions" in data:
            return data["questions"]
        elif isinstance(data, list):
            if all(isinstance(item, str) for item in data):
                return data
            elif all(isinstance(item, dict) and "question" in item for item in data):
                return [item["question"] for item in data]
        
        raise ValueError("JSON格式不正确，应为 {\"questions\": [...]} 或 [{\"question\": \"...\"}, ...]")

    def _read_csv(self, file_path: Path) -> List[str]:
        """读取CSV格式的问题文件"""
        import csv
        questions = []
        
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)  # 跳过表头（如果有）
            for row in reader:
                if row and row[0].strip():
                    questions.append(row[0].strip())
        
        return questions

    def add_result(self, question: str, answer: str, error: Optional[str] = None) -> None:
        """
        添加一个问题的处理结果
        
        :param question: 问题
        :param answer: 回答
        :param error: 错误信息（如果有）
        """
        self.results.append({
            "question": question,
            "answer": answer,
            "error": error or "",
            "timestamp": datetime.now().isoformat()
        })

    def save_results(self, format_type: str = "txt") -> Path:
        """
        保存结果到文件
        
        :param format_type: 输出格式，支持 'txt', 'json', 'md'
        :return: 输出文件路径
        """
        if format_type == "txt":
            return self._save_as_txt()
        elif format_type == "json":
            return self._save_as_json()
        elif format_type == "md":
            return self._save_as_markdown()
        else:
            raise ValueError(f"不支持的格式: {format_type}")

    def _save_as_txt(self) -> Path:
        """保存为TXT格式"""
        output_path = self.output_path.with_suffix(".txt")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"批量处理结果\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总问题数: {len(self.results)}\n")
            f.write(f"成功数: {sum(1 for r in self.results if not r['error'])}\n")
            f.write(f"失败数: {sum(1 for r in self.results if r['error'])}\n")
            f.write("=" * 80 + "\n\n")
            
            for idx, result in enumerate(self.results, 1):
                f.write(f"\n{'=' * 80}\n")
                f.write(f"问题 #{idx}\n")
                f.write(f"{'=' * 80}\n\n")
                f.write(f"【问题】\n{result['question']}\n\n")
                
                if result['error']:
                    f.write(f"【错误】\n{result['error']}\n\n")
                else:
                    f.write(f"【回答】\n{result['answer']}\n\n")
                
                f.write(f"时间: {result['timestamp']}\n")
        
        return output_path

    def _save_as_json(self) -> Path:
        """保存为JSON格式"""
        output_path = self.output_path.with_suffix(".json")
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "total": len(self.results),
                    "success": sum(1 for r in self.results if not r['error']),
                    "failed": sum(1 for r in self.results if r['error'])
                },
                "results": self.results
            }, f, ensure_ascii=False, indent=2)
        
        return output_path

    def _save_as_markdown(self) -> Path:
        """保存为Markdown格式"""
        output_path = self.output_path.with_suffix(".md")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# 批量处理结果\n\n")
            f.write(f"**生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**总问题数：** {len(self.results)}\n\n")
            f.write(f"**成功数：** {sum(1 for r in self.results if not r['error'])}\n\n")
            f.write(f"**失败数：** {sum(1 for r in self.results if r['error'])}\n\n")
            f.write("---\n\n")
            
            for idx, result in enumerate(self.results, 1):
                f.write(f"## 问题 #{idx}\n\n")
                f.write(f"**问题：**\n\n")
                f.write(f"```\n{result['question']}\n```\n\n")
                
                if result['error']:
                    f.write(f"**错误：**\n\n")
                    f.write(f"```\n{result['error']}\n```\n\n")
                else:
                    f.write(f"**回答：**\n\n")
                    f.write(f"{result['answer']}\n\n")
                
                f.write(f"*时间: {result['timestamp']}*\n\n")
                f.write("---\n\n")
        
        return output_path

    def print_summary(self) -> None:
        """打印处理摘要"""
        total = len(self.results)
        success = sum(1 for r in self.results if not r['error'])
        failed = sum(1 for r in self.results if r['error'])
        
        console.print("\n[bold green]批量处理完成！[/bold green]")
        console.print(f"总计: {total} | 成功: {success} | 失败: {failed}")
        
        if failed > 0:
            console.print("\n[yellow]失败的问题：[/yellow]")
            for idx, result in enumerate(self.results, 1):
                if result['error']:
                    console.print(f"  {idx}. {result['question'][:50]}...")
                    console.print(f"     错误: {result['error']}")


def process_batch_questions(
    questions: List[str],
    handler: Any,
    show_progress: bool = True,
    **kwargs: Any
) -> BatchProcessor:
    """
    批量处理问题
    
    :param questions: 问题列表
    :param handler: 处理器（DefaultHandler 或 ChatHandler）
    :param show_progress: 是否显示进度条
    :param kwargs: 传递给handler的参数
    :return: BatchProcessor实例
    """
    # 提取output参数并移除，避免传递给handler
    output_path = kwargs.pop("output", None)
    processor = BatchProcessor(output_path)
    if show_progress:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]处理问题中...", total=len(questions))

            for question in questions:
                try:
                    # 调用handler处理问题
                    answer = handler.handle(prompt=question, **kwargs)
                    processor.add_result(question, answer)
                except Exception as e:
                    processor.add_result(question, "", str(e))
                progress.advance(task)
    else:
        for idx, question in enumerate(questions, 1):
            console.print(f"\n[cyan]处理问题 {idx}/{len(questions)}...[/cyan]")
            try:
                answer = handler.handle(prompt=question, **kwargs)
                processor.add_result(question, answer)
            except Exception as e:
                processor.add_result(question, "", str(e))

    return processor
