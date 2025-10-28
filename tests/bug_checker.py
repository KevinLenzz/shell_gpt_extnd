from tests.utils import cmd_args


def BugChecker(result,dict_arguments):
    print("=== 异常详情 ===")
    print(f"异常类型: {type(result.exception).__name__}")
    print(f"异常信息: {str(result.exception)}")

    # 获取退出码（如果是SystemExit）
    if isinstance(result.exception,SystemExit):
        print(f"退出码: {result.exception.code}")

    # 打印完整的堆栈跟踪
    if result.exc_info:
        import traceback
        print("完整堆栈跟踪:")
        traceback.print_exception(*result.exc_info)
    else:
        import traceback
        print("当前堆栈:")
        traceback.print_stack()

    # 打印相关上下文信息
    print(f"退出码: {result.exit_code}")
    print(f"标准输出: {result.stdout}")
    print(f"标准错误: {result.stderr}")
    print(f"命令行参数: {cmd_args(**dict_arguments)}")