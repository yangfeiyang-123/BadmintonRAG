# 打开 / 关闭报告网页

服务启动后，浏览器访问 **http://127.0.0.1:8765/**

## 启动

任选一种。启动后窗口会被服务占用（前台运行）。

```bash
# 方式 A：用脚本（位置参数，host 在前 port 在后；不带参数则默认 127.0.0.1 8765）
cd /data3/yangfeiyang/WorkSpace/BadmintonRAG
bash ./scripts/serve.sh 127.0.0.1 8765

# 方式 B：直接调 Python（用 --host / --port 标志）
cd /data3/yangfeiyang/WorkSpace/BadmintonRAG
.venv/bin/python -m rag_project.api.server --host 127.0.0.1 --port 8765
```

打开浏览器（可选）：

```bash
xdg-open http://127.0.0.1:8765/
```

## 关闭

```bash
# 情况 1：服务在前台运行（当前终端）
# 直接按 Ctrl + C

# 情况 2：服务在后台 / 别的终端，按端口结束
kill $(lsof -t -i:8765)

# 若上面不生效，强制结束
kill -9 $(lsof -t -i:8765)

# 情况 3：没装 lsof 时，用 fuser 按端口结束
fuser -k 8765/tcp
```

## 后台启动（可选）

```bash
# 启动并丢到后台，日志写到 serve.log
cd /data3/yangfeiyang/WorkSpace/BadmintonRAG
nohup .venv/bin/python -m rag_project.api.server --host 127.0.0.1 --port 8765 > serve.log 2>&1 &

# 关闭同上：kill $(lsof -t -i:8765)
```
