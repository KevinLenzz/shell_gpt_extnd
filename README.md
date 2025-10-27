# ShellGPT
由AI大型语言模型（LLM）支持的命令行生产力工具。这个命令行工具提供了**shell命令、代码片段、文档**的简化生成，消除了对外部资源（如谷歌搜索）的需求。支持Linux、macOS、Windows，并与PowerShell、CMD、Bash、Zsh等所有主流Shell兼容。
https://github.com/TheR1D/shell_gpt/assets/16740832/9197283c-db6a-4b46-bfea-3eb776dd9093
# ShellGPT-Extend
非专用词已均汉化，默认api使用deepseek。在原项目上进行了扩展开发。
## 使用方法先看完原版教程
## 注意！！
不存在库源，请自行下载编译。
sgpt并不会一直有进程在后台挂载，而是每次使用后都自动关闭。
## 开发调试方法
在项目根目录下执行run文件（文件类型：shell脚本）来替代sgpt发布版本的sgpt [选项、参数]：
```shell
. run [选项、参数]
```

已把tests目录下的_integration_test.sh文件汉化，目前仅测试了deepseek。

测试之前先在tests目录下运行以下命令
```shell
. prepare
```
它会将本用户的sgpt配置中使用函数改为false（之后再运行一遍这个脚本可以改回来）

tests目录下运行
```shell
. devtest
```
测试接入的中文api是否功能齐全