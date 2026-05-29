## xiaomi-cli

基于小米云笔记 Web 端接口封装的 CLI，当前覆盖：

- 笔记：列表、详情、创建、更新、删除
- 待办：列表、详情、创建、更新、删除、完成、取消完成
- 同步：笔记同步、索引检查、索引更新
- 待办提醒：支持 `--remind-at` 和 `--repeat`

项目使用 `uv` 初始化并管理依赖。

## 已确认的 Web API

这部分来自当前已登录 Chrome 会话下的真实抓包与 bundle 分析：

- `GET /note/full/page`
- `GET /note/note/{id}/`
- `POST /note/note`
- `POST /note/note/{id}`
- `POST /note/full/{id}/delete`
- `GET /note/sync/full/`
- `GET /note/index/check`
- `POST /note/index/update`
- `GET /todo/v1/user/records`
- `GET /todo/v1/user/records/{id}`
- `POST /todo/v1/user/records`
- `POST /todo/v1/user/records/{id}/update`
- `POST /todo/v1/user/records/{id}/delete`

请求细节：

- `GET` 会自动附带 `ts`
- `POST` 使用 `application/x-www-form-urlencoded`
- `POST` body 会附带 `serviceToken`
- 登录态主要依赖浏览器 cookie

## 安装

```bash
uv sync
```

运行帮助：

```bash
uv run xiaomi-cli --help
```

## Agent 使用手册

这一节是给 Agent、自动化助手、以及二次集成方看的。目标是让 Agent 只读 README 也能快速判断：

- 什么时候应该使用这个 CLI
- 如何安装
- 如何确认认证是否可用
- 遇到 `tag` / `eTag` / `401` 时应该怎么处理

### 适用场景

当用户提到以下意图时，优先使用当前仓库里的 `xiaomi-cli`，而不是继续走浏览器页面点击：

- 小米云笔记 / 小米待办
- 笔记或待办的创建、查询、更新、删除
- 提醒时间设置
- 相对时间提醒，例如 `5分钟后`、`1天后`、`1h`、`1d`
- 笔记同步、索引检查、索引更新

### 安装与启动

在仓库根目录执行：

```bash
uv sync
uv run xiaomi-cli --help
```

如果只是调用模块入口，也可以：

```bash
uv run python -m xiaomi_cli --help
```

### 认证检查

当前 CLI 依赖浏览器 Cookie 登录态。

Agent 应优先这样确认本机认证配置路径：

```bash
uv run xiaomi-cli auth show-path
```

如果没有配置，再引导用户使用以下方式之一：

```bash
uv run xiaomi-cli auth save
uv run xiaomi-cli auth refresh
uv run xiaomi-cli auth keepalive --interval-seconds 25
uv run xiaomi-cli ... --cookie '...'
uv run xiaomi-cli ... --cookie-file ./xiaomi.cookie
```

### 命令优先级

用户要求进行笔记 / 待办操作时，优先匹配这些命令：

- 笔记
  - `uv run xiaomi-cli note list`
  - `uv run xiaomi-cli note get <note_id>`
  - `uv run xiaomi-cli note create --content '...'`
  - `uv run xiaomi-cli note update <note_id> --tag <tag> --title '...' --content '...'`
  - `uv run xiaomi-cli note delete <note_id> --tag <tag>`
- 待办
  - `uv run xiaomi-cli todo list`
  - `uv run xiaomi-cli todo get <record_id>`
  - `uv run xiaomi-cli todo create --title '...'`
  - `uv run xiaomi-cli todo update <record_id> --e-tag <etag> --title '...'`
  - `uv run xiaomi-cli todo delete <record_id> --e-tag <etag>`
  - `uv run xiaomi-cli todo finish <record_id> --e-tag <etag>`
  - `uv run xiaomi-cli todo unfinish <record_id> --e-tag <etag>`
- 同步
  - `uv run xiaomi-cli sync notes`
  - `uv run xiaomi-cli sync index-check`
  - `uv run xiaomi-cli sync index-update`

### 提醒时间规则

Agent 处理提醒时间时，遵循这两个参数：

- `--remind-at`
  - 绝对时间，例如：`2026-05-29 09:30`
- `--remind-in`
  - 相对时间，支持：
    - 中文：`5分钟后`、`2小时后`、`1天后`、`30秒后`、`1周后`
    - 短格式：`1m`、`1h`、`1d`、`1s`、`1w`

限制：

- `--remind-at` 和 `--remind-in` 不能同时传
- 如果用户说“10 分钟后提醒我”，优先转成 `--remind-in '10分钟后'`

### 更新与删除前置条件

Agent 在执行更新或删除前，应先确保控制字段是最新的：

- 笔记使用 `tag`
- 待办使用 `eTag`

推荐顺序：

1. `get`
2. 拿到最新 `tag` 或 `eTag`
3. 再执行 `update` / `delete`

补充说明：

- 笔记更新成功后，服务端通常会返回新的 `tag`
- 待办更新成功后，服务端通常会返回新的 `eTag`
- 如果紧接着删除刚更新的数据，应使用最新值

### 失败处理

如果 Agent 遇到这些情况，应按下面处理：

- `401 Unauthorized`
  - 说明 Cookie 失效或缺失，应优先尝试：
    - `uv run xiaomi-cli auth refresh`
    - 如果需要长期保活：`uv run xiaomi-cli auth keepalive --interval-seconds 25`
  - 如果刷新后仍失败，再要求用户重新登录并更新 Cookie
- note delete 冲突
  - 重新读取最新 `tag` 后重试
- todo update/delete 冲突
  - 重新读取最新 `eTag` 后重试

### 建议回读验证

执行写操作后，建议 Agent 做最小验证：

- `note create/update` 后执行 `note get`
- `todo create/update` 后执行 `todo get` 或 `todo list`
- `sync` 命令直接检查 JSON 返回

## 认证

当前版本为了保持 CLI 可独立运行，使用浏览器里复制出来的完整 Cookie header。

另外，当前版本已经支持纯脚本续期 Cookie：

- `auth refresh`
  - 通过 `note sync` 心跳请求触发服务端返回新的 Cookie
  - 适合单次刷新并回写本地配置
- `auth keepalive`
  - 按固定间隔持续续期
  - 适合长时间运行脚本前先保活登录态

推荐方式：

1. 打开已登录的小米云笔记页面：`https://i.mi.com/note/h5#/`
2. 打开开发者工具
3. 找任意一个请求，复制它的 `Cookie` 请求头
4. 保存到本地配置

示例：

```bash
uv run xiaomi-cli auth save
```

如果已经有可用 Cookie，也可以直接做一次续期并保存：

```bash
uv run xiaomi-cli auth refresh
```

如果只想输出刷新后的 Cookie，不回写配置：

```bash
uv run xiaomi-cli auth refresh --no-save --cookie 'serviceToken=...; userId=...'
```

如果需要持续保活：

```bash
uv run xiaomi-cli auth keepalive --interval-seconds 25
```

限制轮数的保活示例：

```bash
uv run xiaomi-cli auth keepalive --interval-seconds 25 --max-rounds 10
```

也可以临时传参：

```bash
uv run xiaomi-cli note list --cookie 'serviceToken=...; userId=...'
```

或者从文件读取：

```bash
uv run xiaomi-cli note list --cookie-file ./xiaomi.cookie
```

默认配置文件路径：

```bash
uv run xiaomi-cli auth show-path
```

续期说明：

- 当前验证结果表明，Cookie 续期来自服务端响应下发，而不是前端 JS 主动写 `document.cookie`
- CLI 在续期后会自动去重同名 Cookie，优先保留服务端返回的新值

## 笔记命令

列出笔记：

```bash
uv run xiaomi-cli note list
```

查看详情：

```bash
uv run xiaomi-cli note get 50472786418352736
```

创建笔记：

```bash
uv run xiaomi-cli note create \
  --content '这是通过 CLI 创建的笔记'
```

更新笔记：

```bash
uv run xiaomi-cli note update 50472786418352736 \
  --tag 50472992708121120 \
  --title '更新后的标题' \
  --content '更新后的正文'
```

删除笔记：

```bash
uv run xiaomi-cli note delete 50472786418352736 --tag 50472992708121120
```

彻底删除：

```bash
uv run xiaomi-cli note delete 50472786418352736 --tag 50472992708121120 --purge
```

## 待办命令

列出待办：

```bash
uv run xiaomi-cli todo list
```

查看详情：

```bash
uv run xiaomi-cli todo get 13384854326018272
```

创建普通待办：

```bash
uv run xiaomi-cli todo create \
  --title '明早开会'
```

创建带提醒的待办：

```bash
uv run xiaomi-cli todo create \
  --title '明早开会' \
  --remind-at '2026-05-29 09:30'
```

创建相对时间提醒的待办：

```bash
uv run xiaomi-cli todo create \
  --title '10 分钟后提醒我' \
  --remind-in '10分钟后'
```

也支持短格式：

```bash
uv run xiaomi-cli todo create \
  --title '1 小时后提醒我' \
  --remind-in '1h'
```

创建带重复提醒的待办：

```bash
uv run xiaomi-cli todo create \
  --title '日报提醒' \
  --remind-at '2026-05-29 18:00' \
  --repeat daily
```

创建清单型待办：

```bash
uv run xiaomi-cli todo create \
  --title '发布前检查' \
  --checklist '写文案' \
  --checklist '过一遍接口' \
  --checklist '发版'
```

更新待办：

```bash
uv run xiaomi-cli todo update 13384854326018272 \
  --e-tag 13384889204211904 \
  --title '今晚吃饭' \
  --remind-at '2026-05-29 19:00' \
  --repeat none
```

按相对时间更新提醒：

```bash
uv run xiaomi-cli todo update 13384854326018272 \
  --e-tag 13384889204211904 \
  --title '今晚吃饭' \
  --remind-in '1天后' \
  --repeat none
```

标记完成：

```bash
uv run xiaomi-cli todo finish 13384854326018272 --e-tag 13384889204211904
```

取消完成：

```bash
uv run xiaomi-cli todo unfinish 13384854326018272 --e-tag 13384889204211904
```

删除待办：

```bash
uv run xiaomi-cli todo delete 13384854326018272 --e-tag 13384889204211904
```

## 待办提醒字段说明

当前 CLI 已按 Web 端真实枚举实现：

- `remindType`
  - `0`: 不提醒
  - `1`: 日期型
  - `2`: 精确时间
- `remindRepeatType`
  - `0`: 不重复
  - `1`: 每天
  - `2`: 每周
  - `3`: 工作日
  - `7`: 每月
  - `8`: 每年

CLI 对应参数：

- `--remind-at '2026-05-29 09:30'`
- `--remind-in '5分钟后'`
- `--remind-in '1天后'`
- `--remind-in '1m'`
- `--remind-in '1h'`
- `--remind-in '1d'`
- `--remind-in '1w'`
- `--repeat none|daily|weekly|weekday|monthly|yearly`

## 同步命令

拉取笔记同步数据：

```bash
uv run xiaomi-cli sync notes
```

检查索引状态：

```bash
uv run xiaomi-cli sync index-check
```

触发索引更新：

```bash
uv run xiaomi-cli sync index-update
```

## 已知限制

- 当前认证方式依赖你手工提供浏览器 Cookie，还没有自动从 Chrome 提取
- 加密笔记 / 加密待办暂未实现本地加解密，只支持当前抓到的非加密常见路径
- `todo update` 目前会重建待办主体内容，更适合常规文本 / 清单类编辑
- Web 端存在一些冲突控制字段，例如 `tag`、`eTag`，更新或删除前建议先 `get` 一次
- 为了安全起见，README 里只给出无敏感信息的示例，真实 Cookie 不要提交进仓库

## 建议工作流

1. 先 `auth save`
2. 用 `note list` / `todo list` 验证登录态
3. 修改前先 `get`，拿到 `tag` 或 `eTag`
4. 再执行 `update` / `delete`

补充说明：

- 笔记在更新成功后，服务端会返回新的 `tag`
- 如果你准备紧接着删除同一条笔记，请使用更新后的 `tag`
