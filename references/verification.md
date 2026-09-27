# 验证协议

Python 3.10+，依赖 `requirements.txt`。优先已有捆绑环境；不在脚本中静默安装软件。导出还需 Word 或转换器，渲染需 Poppler/宿主渲染器。

```sh
python scripts/extract_sources.py --paper paper.pdf --template template.docx --out work/sources
python scripts/prepare_template.py --input template.docx --output work/template-clean.docx
```

`--paper` 可重复。提取生成逐页 TXT、`sources.json` 和模板段落/表格/XML文本；扫描件和提取乱码仍需另行读取。水印脚本默认匹配两种 James 字样，可重复 `--phrase` 覆盖默认列表；报告记录匹配数及改动包部件。不同任务使用不同输出目录。

## 自动检查

在任务目录写 `requirements.json`；源路径相对该 JSON 解析：

```json
{
  "required_text": ["这篇论文需要解决什么问题", "0.7962"],
  "expected_urls": ["https://arxiv.org/abs/2302.02352"],
  "forbidden_text": ["James科研小班课", "James的科研小班课"],
  "sources": [{"path": "paper.pdf", "sha256": "源文件实际SHA256"}],
  "expected_pages": 14
}
```

示例数字仅说明字段，不带入下一篇。要求列表覆盖全部模板题目及关键正文/表格/可抽取公式，`sources` 包括原论文及原模板。

```sh
python scripts/verify_pdf.py output.pdf --requirements work/requirements.json --report work/qa.json
```

自动失败退出 1；自动通过但视觉审阅缺失/过期/不完整退出 2，`ready_for_delivery` 为 false。报告写出当前 PDF SHA-256。

## 视觉审阅记录

全部最终页面实际查看后再写 `visual-review.json`：

```json
{
  "pdf_sha256": "最终PDF实际SHA256",
  "pages_reviewed": [1, 2, 3],
  "issues": []
}
```

页码必须正好覆盖实际所有页，不能未看就填“通过”。图片水印/公式尤其依赖视觉审阅。

```sh
python scripts/verify_pdf.py output.pdf --requirements work/requirements.json --visual-review work/visual-review.json --report work/qa-final.json
```

所有检查通过才退出 0。PDF 一旦改动旧视觉记录立即失效。脚本不证明事实正确，也不代替逐页查看；加密、扫描件或抽取乱码应换读取方式，不能跳过检查冒充完成。
