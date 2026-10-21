# 来源记录

获取与阅读日期：2026-10-21。完整 URL、使用范围与本次快照 SHA-256 见 `book/sources.json`。快照仅本地核查，不进入 Git 或下载包。

1. SQLite FTS5 官方说明：读取默认 unicode61、虚拟表、MATCH 和 bm25 段落。确认 bm25 小值更好；中文预处理、过滤 SQL 和候选策略是本书实现选择。网页更新不代表本书测试了所有新能力。
2. SQLite Transaction 官方说明：读取读快照、单写者、BEGIN IMMEDIATE、SQLITE_BUSY。用于说明事务边界，没有替代并发压测。
3. Cormack/Clarke/Buettcher 2009 RRF 原论文：读取公式与 k=60 选择背景，未移用其数据集的效果或统计结论。
4. BAAI/bge-small-zh-v1.5 固定提交模型卡：读取 MIT 声明、CLS/L2、短查询指令与相似度非通用阈值说明。
5. Xenova/bge-small-zh-v1.5 固定提交导出卡：明确社区 ONNX 分发。本书下载的是量化导出，运行文件 SHA-256 另记在报告中，不声称使用原始全精度权重。

作者构造的 8 篇制度和 13 条查询独立于这些资料，是教学数据，没有真实企业来源、独立盲测或模型排行榜用途。实际报告保留在 `lab/evidence/`，所有事实与权限结论限于这些输入和命名测试。
