# 《企业知识库检索工程》交付记录

完成日期：2026-10-21。当前交付版本：**v1.0.1**。

## 公开入口

- 公开源码：https://github.com/Aias00/knowledge-retrieval-book
- 在线阅读：https://aias00.github.io/knowledge-retrieval-book/
- Pages EPUB：https://aias00.github.io/knowledge-retrieval-book/downloads/knowledge-retrieval-book.epub
- Release：https://github.com/Aias00/knowledge-retrieval-book/releases/tag/v1.0.1
- Release EPUB：https://github.com/Aias00/knowledge-retrieval-book/releases/download/v1.0.1/knowledge-retrieval-book.epub
- 成功 CI：https://github.com/Aias00/knowledge-retrieval-book/actions/runs/39580408519

书稿与产物源提交、Release tag 目标均为 `b97053a0942120576a8e8dcd8c55c54115ab926b`。本文件在随后一个仅文档提交中添加，不参与产品构建。

## 内容与真实实验

全书 16 章正文，正文汉字计数 **14,188**（只统计第 1–16 章 Markdown 中 U+3400–U+9FFF 字符）；另有前言、3 篇原创附录和 1 篇构建时生成的完整实验代码附录，共 **21 篇**。

正文覆盖文档身份/版本与来源、Markdown/限定 JSON 投影、NFC 和码点坐标、切分、真实 SQLite FTS5 与中文双字词项、词项向量、可选真实 BGE 本地向量、RRF、标题规则重排、摘录引用、事务更新、墓碑删除/旧事件重放、ACL 撤权与缓存引用复核、核心/模型实验、评估和生产边界。

实验语料为 `knowledge-fixture-v1`：8 篇作者构造文档，13 条查询（10 正例、3 负例），输入 JSON 有 manifest SHA-256。没有真实企业资料、独立盲测或统计总体结论。原始报告位于 `lab/evidence/`，来源清单与范围位于 `book/sources.json`。

| 表示与模式 | Recall@3 | MRR@3 | 负例空候选 | 当前权限断言违规 |
| --- | ---: | ---: | ---: | ---: |
| 词项计数：词面/向量/混合 | 0.9 | 0.9 | 各 3/3 | 各 0 |
| 量化 BGE：词面 | 0.9 | 0.9 | 3/3 | 0 |
| 量化 BGE：向量/混合 | 1.0 | 1.0 | 各 3/3 | 各 0 |

所有评估模式开启标题规则重排，先按文档去重再计算前三篇排名。差异来自 q07“旅馆住一夜能花多少钱”。这组小样例不证明普遍业务提升，混合没有超越最佳单通道。词项计数不是语义嵌入；所有回答都是原文摘录，`non_llm=True`，没有调用 LLM。

实际 demo 验证：退款 30 天更新为 14 天，旧数字不再命中、旧引用失效；Alice 撤权后新搜索和旧引用拒绝，Bob 保留访问；删除年假后活动索引不可见，旧版本重放被拒绝。引用从当前数据库重读，不能使用调用方伪造的文本。

## 真实模型的复现坐标

- 原模型：`BAAI/bge-small-zh-v1.5`；模型卡提交 `7999e1d3359715c523056ef9478215996d62a620`，卡中声明 MIT。
- 实际使用：`Xenova/bge-small-zh-v1.5` 社区量化 ONNX 导出，提交 `75c43b069aac4d136ba6bc1122f995fedcfd2781`。没有与原始全精度权重混称，没有再分发模型。
- `model_quantized.onnx`：24,010,842 字节，SHA-256 `15b717c382bcb518ba457b93ea6850ede7f4f1cd8937454aa06972366cd19bcc`。
- `tokenizer.json`：439,125 字节，SHA-256 `48cea5d44424912a6fd1ea647bf4fe50b55ab8b1e5879c3275f80e339e8fae26`。
- 本机 Python 3.12.15、SQLite 3.53.1、ONNX Runtime 1.31.0、NumPy 2.5.4、tokenizers 0.23.3。
- CPUExecutionProvider，单线程，CLS 池化、L2 归一化、512 维、最长 512 token；查询带中文检索指令，文档不带。余弦 0.40 是演示阈值，没有概率校准。

核心 22 条测试，本机加载上述真实模型后 **24 条全部通过**；CI 的 24 条中 **22 条核心通过、2 条模型明确跳过**，CI 不重复下载权重。额外只读审阅代理独立运行真实 24 条测试、demo 和词项评估，结果通过，并逐章核对实现与事实边界。

正式实验 ZIP 解包后实际运行过 24 条测试（含本机真实 ONNX）和生命周期 demo，全部通过。`lab/requirements-embedding.txt` 在包内，核心无第三方 Python 依赖；v1.0.1 ZIP 共 19 文件，包含 `lab/README.md` 与 LICENSE，根 README 不再作为出版输入，权重、虚拟环境和数据库不在包内。

## 出版验证与字节一致性

成功 CI 完成核心实验、21 篇源文/网页/EPUB 完整文字一致性、元数据/目录/封面/本地链接/搜索/实验包验证，EPUBCheck 5.4.0 **零错误、零警告**，以及浏览器交互检查。

部署后对公开 URL 再次运行浏览器验收：暗色系统下默认浅色、手动深色、跨标签主题同步、字号保留、搜索、原生目录、全部 21 篇在 320/390px 无横向溢出、无 JavaScript 阅读和翻页、禁用存储、下载和零脚本错误全部通过。桌面/手机正文与封面截图已目视检查。

| 产物 | 字节 | SHA-256 |
| --- | ---: | --- |
| EPUB | 112,945 | `9ccdece40866ff9039b6088b69a276b266e9d133e17d9f2acf98825f446aba2b` |
| 完整 Markdown | 139,684 | `2587cea75cf8006cd7f88dab97f260a420512bae175aef3f569694b3f676e82b` |
| 实验 ZIP | 25,352 | `87719c5ce56a40c5738f1633d9261fb86c7174cd905b317540060aecc359d9b8` |

Pages EPUB/Markdown/ZIP 均逐字节匹配成功 CI 的 `book-downloads` artifact；Release 从同一个 artifact 上传，重新下载 EPUB 后匹配 CI/Pages，ZIP 完整性通过。线上 CSS 与 JS 分别逐字节匹配 `web/style.css`、`web/app.js`。

Release 另含离线 HTML、来源/实验/验证/元数据 JSON、SHA256SUMS 与 EPUBCheck 日志。`SHA256SUMS` 针对 EPUB。精确交付 artifact 保存在本机 `/tmp/knowledge-retrieval-book-v101-ci/`；它与本地重新构建 EPUB 的时间元数据可能不同，不能互换成另一份字节产物。

## 明确边界与后续维护

没有实现 HTTP 身份认证、任意文档解析、PDF/OCR、ANN、学习重排、任意语义蕴含验证或生产吞吐压测。可信上下文由调用方提供；`status()` 属维护接口。共享 FTS 全局统计和时间侧信道没有审计。删除只保证当前活动索引不可见，不保证物理擦除/备份清除；撤权不能召回已交付信息。

工作流只在书稿、实验、脚本、主题、LICENSE 等产品输入变化时触发；仅更新根 README、研究记录或本交付文件不重建。后续变更应生成新版本，从成功 CI artifact 发布 Release，再核对 Pages/Release 字节，不重写已有 tag。
