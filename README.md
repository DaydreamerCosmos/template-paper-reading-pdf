# template-paper-reading-pdf

按精读作业模板把研究论文整理成中文 PDF 的 Codex skill，默认每篇独立成册、无水印。

覆盖科学假设原文出处、方法与公式、实验口径、数据和代码、三句话贡献、研究方向与疑问，并要求最终逐页检查。包内不含原始论文、私人笔记、账号信息或特定机器路径。

## 使用

将本目录作为 `template-paper-reading-pdf` 技能目录安装到 Codex skills 目录；使用 skill-installer 时提供仓库/目录链接。重新加载技能后：

> 使用 $template-paper-reading-pdf 按模板精读这篇论文，注明科学假设的原文依据，生成无水印 PDF。

> 按模板阅读这些论文，每篇各自生成一份 PDF。

用户模板优先；没有时使用默认六题。这是工作流技能，不是 Template Gallery 的 artifact-template 包，也不是自动生成论文事实的独立程序。

## 内容与依赖

- `SKILL.md`：入口与完整流程。
- `references/`：证据、排版、验证指南，按需读取。
- `assets/default-questions.md`：默认六题。
- `scripts/`：输入提取、模板副本水印处理、Word 导出和 PDF 验证。
- `agents/openai.yaml`：展示信息与默认提示。

Python 3.10+、pypdf、lxml；Windows Word 导出需要 Microsoft Word，渲染可用 Poppler。优先使用宿主捆绑环境。

```sh
python -m pip install -r requirements.txt
python scripts/self_test.py
```

自检验证原件不变、定点水印处理、提取、PDF 文本/链接覆盖及过期视觉记录拒绝；不替代真实论文的事实与版面审阅。详见 `references/verification.md`。
