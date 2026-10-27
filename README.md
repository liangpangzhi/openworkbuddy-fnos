# OpenWorkBuddy for fnOS（飞牛私有云）

把开源项目 [CatCatUncle/openworkbuddy](https://github.com/CatCatUncle/openworkbuddy)（v0.17.5，本机优先的 AI 办公工作台）
打包成飞牛 fnOS 的 `.fpk` 应用：装到 NAS 上，点桌面图标直接进工作台，用自然语言下任务，
让 AI 直接产出可编辑的 PPT / Word / Excel / HTML 成果文件。

- **完全离线自包含**：Docker 基础镜像和全部 Node 依赖都打在安装包里，安装过程不访问 Docker Hub
- **桌面图标进入**：安装后飞牛桌面出现「OpenWorkBuddy」图标，点击打开 `http://<NAS-IP>:3800`
- **可接各类主流 AI**：DeepSeek、通义千问、智谱 GLM、Kimi、豆包（火山方舟）、OpenAI、Claude、
  OpenRouter、Ollama 本地模型，以及任意 OpenAI 兼容接口（BYOK，Key 只留在自己的 NAS 上）
- **数据不丢**：数据落在应用的共享目录，卸载应用保留

> 上游 openworkbuddy 自身为 PolyForm Noncommercial 1.0.0 授权（个人非商用免费，商用需授权），
> 本仓库只是打包脚本与配置，使用时请遵守上游许可证。

---

## 目录结构

```
openworkbuddy-fnos/
├── README.md                 本文件
├── docs/
│   ├── 01-打包开发文档.md     FPK 规范、manifest、生命周期脚本、桌面入口
│   ├── 02-构建流程.md         从源码到 .fpk 的完整步骤
│   ├── 03-安装与使用.md        安装、接模型、数据目录、升级卸载
│   └── 04-踩坑记录.md         本次开发踩到的坑与解决办法
├── scripts/
│   ├── prepare-payload.sh    拉上游源码 + 装生产依赖 + 组装容器运行目录
│   ├── fetch_image.py        从 Docker Hub 取基础镜像，组装成 docker load 可用的 tar
│   └── build_fpk.py          调用 fnpack 打包，并修正 Windows 下丢失的可执行位
└── fpk-src/                  FPK 源码（不含运行时依赖，构建时生成）
    ├── manifest              应用身份信息
    ├── ICON.PNG / ICON_256.PNG
    ├── cmd/                  9 个生命周期脚本
    ├── config/privilege      运行身份声明
    ├── config/resource       docker 项目 + 数据共享目录声明
    └── app/
        ├── ui/config         桌面图标入口配置
        ├── ui/images/        64 / 256 图标
        └── docker/
            ├── docker-compose.yaml
            ├── docker-entrypoint.sh   容器入口（首次启动自愈依赖）
            └── docker-seed.js         安装参数 → config.json 模型配置
```

## 快速开始

```bash
# 1. 组装容器运行目录（上游源码 + node_modules）
bash scripts/prepare-payload.sh v0.17.5

# 2. 取基础镜像（离线包的关键，205MB，只需做一次）
python scripts/fetch_image.py

# 3. 打包（需要 fnpack，见 docs/02-构建流程.md）
python scripts/build_fpk.py
```

产物：`openworkbuddy-<version>.fpk`（约 160 MB）。
在飞牛「应用中心 → 手动安装」上传即可，或用 `fnos-cli app install-fpk xxx.fpk --volume-id 1 --yes`。

## 运行时结构

| 路径 | 说明 |
| --- | --- |
| 容器内 `/app` | 应用代码（挂载 `target/docker/app`，含 node_modules） |
| 容器内 `/data` | 全部可写数据（挂载 `shares/<appname>`，卸载保留） |
| 服务端口 | 3800（`manifest` 的 `service_port`，可在 compose 里改） |
| 桌面入口 | `type=url`，`http://<NAS-IP>:3800/` |

## 验证状态（192.168.5.11，fnOS）

- 应用中心状态 running，容器运行中，端口 3800 映射 0.0.0.0
- `http://<NAS>:3800` 返回 200，`/api/auth/state` 正常
- 桌面入口已注册，点击可进入
- 随包加载 40 个技能、34 个专家团
