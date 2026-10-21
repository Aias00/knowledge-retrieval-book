# 企业知识库检索工程

从文档、权限与索引到可以核查的证据。16 章正文、前言与 4 个附录，在线阅读和 EPUB 来自同一份完整中文书稿。

- [在线阅读](https://aias00.github.io/knowledge-retrieval-book/)
- [下载 EPUB](https://aias00.github.io/knowledge-retrieval-book/downloads/knowledge-retrieval-book.epub)
- [版本发布](https://github.com/Aias00/knowledge-retrieval-book/releases)
- [完整交付证据](DELIVERY.md)

书中提供真实 SQLite FTS5、中文双字词项、词项余弦、可选本地 BGE 量化 ONNX、RRF 混合召回、标题规则重排与引用复核。核心链路实际覆盖增量更新、墓碑删除、旧事件重放、ACL 撤权与缓存命中复核。回答直接摘录原文，明确没有调用 LLM。

## 运行实验

需要 Python 3.10+ 和启用 FTS5 的 SQLite，推荐 Python 3.12。核心不依赖第三方 Python 包。

```sh
python3 -m venv .venv
. .venv/bin/activate
python -c 'import sqlite3; c=sqlite3.connect(":memory:"); c.execute("CREATE VIRTUAL TABLE probe USING fts5(text)"); print(sqlite3.sqlite_version)'
python -m unittest discover -s tests -v
python -m lab.demo --output /tmp/knowledge-demo.json
python -m lab.evaluate --output /tmp/knowledge-term-evaluation.json
```

核心 22 条测试；2 条模型测试在未设置模型目录时明确跳过。模型实验已在本机实际运行：

```sh
python -m pip install -r lab/requirements-embedding.txt
python -m lab.fetch_embedding
BGE_MODEL_DIR=.tools/models/bge-small-zh-v1.5 python -m unittest discover -s tests -v
python -m lab.evaluate --onnx-model .tools/models/bge-small-zh-v1.5 --output /tmp/knowledge-bge-evaluation.json
```

使用固定提交的 Xenova 社区量化 ONNX 导出，原模型为 BAAI/bge-small-zh-v1.5；下载校验 SHA-256，不分发模型文件。实际推理使用 CPU、CLS 与 L2，输出 512 维。详见 [实验说明](lab/README.md)。

## 证据与限制

`lab/evidence/` 保存实际演示与两套逐条评估。语料是 8 篇作者构造文档、13 条查询（10 正例、3 负例），不是独立业务验收集。词项计数向量没有语义模型；真实量化 BGE 在这组数据中补回一条同义查询，Recall@3 从 0.9 到 1.0，不构成普遍效果承诺；混合没有超越最好的单通道。

上下文对象假定由可信调用方提供，没有实现 HTTP 认证；向量逐一扫描可见片段，没有 ANN；重排是标题规则，没有重排模型；引用检查完整性与当前权限，没有任意语义蕴含判断。删除只承诺活动索引不可见，没有物理擦除或备份清除保证。共享 FTS 统计与计时侧信道没有审计。

## 出版

书稿在 `book/chapters/`，来源与事实边界在 `book/sources.json` 和来源附录。需要 Pandoc 3.12.1、Python、Java 21（EPUBCheck）与 Node.js（浏览器检查）：

```sh
python scripts/build.py
python scripts/verify.py
sh scripts/epubcheck.sh
python -m http.server 8767 --bind 127.0.0.1 --directory site
# 另一个终端
npm install --no-save --package-lock=false playwright@1.64.1
npx playwright install chromium
node scripts/browser-check.cjs
```

`site/downloads/` 包含 EPUB、离线 HTML、完整 Markdown、实验 ZIP 和校验材料。浏览器检查覆盖全部章节在 320/390px、浅色默认、深色、搜索、字号、目录、无 JavaScript 和存储禁用。

GitHub Actions 在内容、实验、出版脚本或主题变更时构建验证并发布 Pages。仅改 `DELIVERY.md`、`README.md` 或研究说明不会触发重建；Release 必须使用同一成功 CI 的 `book-downloads` artifact，核对 Pages 与 Release EPUB 字节一致。不要用重新本地构建的另一个 EPUB 替换交付版本。

## 授权

原创书稿与插图保留所有权利；随书 `lab/`、`tests/`、`scripts/`、`web/`、`epub/` 代码按 [LICENSE](LICENSE) 的 MIT 部分授权。第三方资料和模型适用各自授权，仓库不再分发来源快照和权重。
