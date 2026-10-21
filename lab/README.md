# 随书检索实验

在仓库根目录以 `python -m lab...` 运行。核心只依赖 Python 标准库与 FTS5；这是可审查的教学索引，不是部署完成的企业服务。

## 文件与契约

- `text.py`：NFC/换行投影、Markdown 与限定 JSON 解析、带码点区间的切分、中文双字词项和词项计数余弦。
- `index.py`：真实 SQLite 表/FTS5、可见片段先过滤、余弦扫描、RRF、标题规则重排、数据库重读引用，以及事务更新/删除/ACL。
- `fixtures.py` 与 `data/`：8 篇作者构造文档、13 条查询，manifest 校验原始 JSON 文件摘要。
- `demo.py`：退款更新、撤权、删除与重放，实际失败就退出。
- `evaluate.py`：每个查询的前三篇去重文档、正例 Recall/MRR、负例空候选和权限断言。
- `embedding.py` 与 `fetch_embedding.py`：可选真实量化 BGE 推理、固定提交下载与摘要校验。
- `evidence/`：本次实际运行的完整 JSON，不是未来运行的期望模板。

文档坐标是规范投影的 Python Unicode 码点 `[start,end)`，不是原始字节。Markdown 只识别简单 ATX 标题，未实现完整 CommonMark（包括围栏内标题区分）、PDF/OCR 或表格抽取。`Context` 必须由可信层建立；`status()` 属于维护接口，不能公开给普通用户。

## 核心与模型分别验证

```sh
python -m unittest discover -s tests -v
python -m lab.demo --output /tmp/knowledge-demo.json
python -m lab.evaluate --output /tmp/knowledge-term-evaluation.json
```

核心 22 条通过时，2 条可选模型测试应报告跳过。要验证真实模型：

```sh
python -m pip install -r lab/requirements-embedding.txt
python -m lab.fetch_embedding
BGE_MODEL_DIR=.tools/models/bge-small-zh-v1.5 python -m unittest discover -s tests -v
python -m lab.evaluate --onnx-model .tools/models/bge-small-zh-v1.5 --output /tmp/knowledge-bge-evaluation.json
```

下载需要 `curl`。原模型 BAAI/bge-small-zh-v1.5 卡提交 `7999e1d3359715c523056ef9478215996d62a620`；社区导出 Xenova/bge-small-zh-v1.5 提交 `75c43b069aac4d136ba6bc1122f995fedcfd2781`，不与原始全精度权重混称。文件摘要在附录与报告中，权重不进入 Git/实验包。

本机实际执行 24 条测试全部通过；模型和 tokenizer 摘要、CPU 提供方、依赖版本、CLS/L2、查询指令写入 `evidence/bge-evaluation.json`。词项/向量/混合在基础表示下均 0.9/0.9；真实模型的向量与混合均 1.0/1.0。三条负例各模式均空，当前断言无权限违规。

语料与标签都由作者构造，没有独立盲测；演示阈值未校准，耗时不是并发性能。所有回答为非 LLM 摘录，完整性验证不等于语义蕴含；删除不清备份；撤权不能召回已经交付内容；共享 FTS 统计与时间侧信道未审计。
