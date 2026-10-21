# 附录A 来源与事实边界

以下一手资料于 2026-10-21 获取并阅读。源码仓库的 `book/sources.json` 记录完整 URL、快照摘要、使用章节与支撑范围；原站 HTML、论文和模型权重不随书再分发。引用用于解释机制，实验结果来自随书代码实际运行，两者不能互相替代。

## SQLite FTS5

[SQLite FTS5 Extension](https://www.sqlite.org/fts5.html) 用于核对虚拟表、默认 Unicode 分词器、MATCH 与 BM25 辅助函数。快照 SHA-256：`de3092630358518a6869bf047055b3938e18b476e3fbc54f4e2146d1e593497f`。文档属于可更新页面，摘要固定本次阅读快照，不代表上游永久版本。

本书自己选择预生成中文双字词项、词项 OR 查询、候选上限和 ACL SQL。它们不是 SQLite 文档推荐的通用企业检索方案，也不是对 SQLite 隔离能力的完整安全审计。

## SQLite 事务

[Transaction](https://www.sqlite.org/lang_transaction.html) 支撑读写事务、单写者与 `BEGIN IMMEDIATE` 的说明。快照 SHA-256：`b65dc308fd9e0ce471844c97366a4f5ad3a1f42833a3b19486ad7d6555a8e24e`。本书实际只测试单进程教学实现，没有把文档中的并发机制转换为自己的并发压测结果。

## RRF 原始论文

Gordon V. Cormack、Charles L. A. Clarke、Stefan Buettcher，2009，[Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)。PDF SHA-256：`5c1f9f1fe0d80f67d82041bbe151ea17437bc7a7d9a920564cf122d1b09eafb5`。

使用其按名次倒数求和的公式，以及论文中固定六十的参数背景。论文数据集与本书的八篇构造文档不同，不移用其提升幅度、显著性或比较结论。

## BGE 原模型与社区导出

[BAAI/bge-small-zh-v1.5 模型卡](https://huggingface.co/BAAI/bge-small-zh-v1.5/blob/7999e1d3359715c523056ef9478215996d62a620/README.md)，提交 `7999e1d3359715c523056ef9478215996d62a620`，快照 SHA-256：`c48a4eeea77f6b1d38b48ec1c5b8d4f86d5550cc43fa345a0db1b2ca1d082369`。用于核对模型身份、MIT 声明、CLS 池化、归一化与中文检索指令。

[Xenova/bge-small-zh-v1.5 导出说明](https://huggingface.co/Xenova/bge-small-zh-v1.5/blob/75c43b069aac4d136ba6bc1122f995fedcfd2781/README.md)，提交 `75c43b069aac4d136ba6bc1122f995fedcfd2781`，快照 SHA-256：`cb22054df1a98f7ee9d5b281d023e67c27cc316e1733baf03fc994d95c3048ab`。本书使用其量化 ONNX 文件，明确标注社区导出，不将其称为原始全精度分发物。

文档可以说明如何使用模型，不能代替本书的真实推理。运行依赖、权重摘要和实际逐条排名见附录B与保存的 JSON 报告。
