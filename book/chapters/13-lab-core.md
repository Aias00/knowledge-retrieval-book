# 第13章 运行核心实验并检查失败路径

本章把前面的契约放进同一个可重复实验。核心链路没有模型下载、账号或服务密钥，只需要 Python 3.10 及以上和启用了 FTS5 的 SQLite。建议用 Python 3.12 建立独立环境，避免系统解释器的扩展缺失影响结果。

## 准备环境

在仓库根目录执行：

```sh
python3 -m venv .venv
. .venv/bin/activate
python -c 'import sqlite3; c=sqlite3.connect(":memory:"); c.execute("CREATE VIRTUAL TABLE probe USING fts5(text)"); print(sqlite3.sqlite_version)'
python -m unittest discover -s tests -v
```

探针实际创建一张 FTS5 表，比只打印 SQLite 版本更能验证所需能力。如果 `sqlite3` 无法导入，或报告没有 FTS5 模块，应换用包含该功能的 Python 发行版。不要通过跳过探针把故障掩盖成一次成功实验。

未设置模型目录时，核心二十二条测试运行，两条可选 ONNX 测试明确跳过。它们不是两个成功结果。CI 也采用这个无模型下载路径；实际本地模型验证见下一章，两类记录在交付信息中分别列出。

## 执行真实状态变化

```sh
python -m lab.demo --output /tmp/knowledge-demo.json
python -m lab.evaluate --output /tmp/knowledge-term-evaluation.json
```

`demo` 创建临时 SQLite 文件并载入清单校验后的文档。它先搜索住宿规定并输出摘录，随后完成退款版本更新、Alice 撤权、年假删除和旧内容重放。程序结束后临时数据库清除，JSON 报告保留在显式指定的位置。

报告中的 `old_30_day_fact_retrievable` 为假，新答案包含十四天；`stale_revision_citation_rejected`、`revoked_alice_citation_rejected` 与 `deleted_citation_rejected` 为真；`bob_access_preserved` 为真。三个私有、跨租户和不相关查询的返回数量为 `[0,0,0]`。

注意这些字段来自真实断言通过后的输出，不是配置文件写入的期望值。任何断言失败，实验都会异常退出，不会把后面的成功字段正常输出。对照源码，可以看到每项声明对应哪些搜索和数据库操作。

## 从测试名找到保障对象

`test_actual_fts5_table_returns_ranked_rows` 检查实际虚拟表与命中；`test_incremental_update_removes_old_fact_and_invalidates_citation` 同时观察旧数字和缓存引用；`test_new_content_event_cannot_regrant_old_acl` 覆盖正文事件重新授予权限的反例。

还有一个容易忽略的测试，把候选的文本字段替换为伪造字串，再调用回答函数。系统仍从数据库读出规范片段。这验证了引用不是简单转发调用方内容，但没有把数据库本身当作不受信攻击者；存储篡改防护属于更大的完整性设计。

## 怎样判断一次复现是否成立

比较语料指纹、模式、文档排名、拒答和状态迁移，不要要求 `wall_ms` 完全相同。机器、Python 与 SQLite 版本会影响耗时，也可能影响同分排序的细节。当前实现用主键稳定打破同分，在同一语料顺序下应得到相同逻辑结果。

仓库的 `lab/evidence/` 保存本次真实运行记录，供离线检查；读者的新报告建议写到 `/tmp`，保留原始证据不变。若修改语料，必须更新清单并重新评估，不能继续把旧报告当成新系统的证据。
