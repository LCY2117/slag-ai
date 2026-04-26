# MSPC-GreenAI：钢渣基镁磷水泥透水建材智能设计与应用决策系统

这是一个不依赖训练数据的 AI + 规则约束型原型系统，适合节能减排竞赛、项目答辩、公众号/小程序展示和后续工程推广。

系统定位：

> 基于钢渣基镁磷水泥透水混凝土（MSPC）的实验规律、材料机理和工程应用需求，构建 AI 辅助设计、性能评估、工艺推荐、节能减排测算和应用方案生成的一体化智能平台。

## 1. 功能模块

- AI 项目知识问答
- 智能配方推荐
- 半经验性能评估
- 工程应用方案生成
- 节能减排与经济效益测算
- 实验数据闭环升级接口预留

## 2. 为什么不需要训练数据也能用

本系统当前不是“黑盒训练模型”，而是“专家规则 + 半经验评估 + 大模型生成解释”的工程化原型。它把已有项目规律转化为可计算规则：

- 综合最优工况：中粒级钢渣（5.0–10.0 mm）+ 振动成型
- 最优孔隙率：约 25%
- 推荐水胶比：0.16
- 推荐骨料胶凝比：4.8
- 典型最优性能：28d 抗压强度约 41.5 MPa、抗折强度约 8.0 MPa、透水系数约 7.0 mm/s
- 单位混凝土钢渣消纳量：约 1700 kg/m³

后续如果有真实正交试验数据，可以把规则引擎升级为“规则约束 + 残差学习”的预测模型。

## 3. 快速运行

### Windows PowerShell

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
notepad .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# 或者：python launch.py
```

浏览器打开：

```text
http://127.0.0.1:8000
```

也可以直接双击 `run.bat`，或者在 PowerShell 运行：

```powershell
.\run.ps1
```

## 4. 配置硅基流动 API Key

你有两种方式：

### 方式 A：填写 `.env`

复制 `.env.example` 为 `.env`，填入：

```env
SILICONFLOW_API_KEY="sk-你的key"
SILICONFLOW_BASE_URL="https://api.siliconflow.cn/v1"
SILICONFLOW_MODEL="Qwen/Qwen2.5-7B-Instruct"
```

### 方式 B：填写 `config.yaml`

```yaml
siliconflow:
  enabled: true
  api_key: "sk-你的key"
  base_url: "https://api.siliconflow.cn/v1"
  model: "Qwen/Qwen2.5-7B-Instruct"
```

环境变量优先级高于 `config.yaml`。

没有 API Key 也能运行，系统会自动使用离线模板生成推荐和报告。

## 5. 检查硅基流动 API 是否可用

配置好 `.env` 或 `config.yaml` 后运行：

```powershell
python scripts/check_siliconflow.py
```

如果输出 `mode: siliconflow`，说明 API 调用成功；如果输出 `offline_fallback`，说明系统仍会使用离线规则模板，不影响规则推荐功能。

## 6. 项目结构

```text
mspc_greenai_system/
  app/
    main.py              FastAPI 入口
    config.py            配置读取
    models.py            请求/响应模型
    rules.py             专家规则与半经验评估核心
    llm.py               硅基流动 API 封装
    report.py            工程方案与问答生成
  static/
    index.html           Web 前端
    app.js               前端交互
    styles.css           页面样式
  data/
    knowledge_base.json  项目知识库
    rules_profile.json   规则参数说明
  config.yaml            配置文件
  .env.example           API key 模板
  requirements.txt
  run.bat
  run.ps1
```

## 7. API 接口

启动后可以访问：

- `GET /api/health`
- `POST /api/recommend`
- `POST /api/evaluate`
- `POST /api/project-plan`
- `POST /api/carbon-economy`
- `POST /api/qa`

自动文档：

```text
http://127.0.0.1:8000/docs
```

## 8. 答辩表述建议

> 我们构建了 MSPC-GreenAI 钢渣基镁磷水泥透水建材智能设计与应用决策系统。系统以项目已有实验规律和材料机理为核心，融合硅基流动大模型 API，形成“专家规则约束 + 半经验性能评估 + 工程方案生成 + 节能减排测算”的智能化应用体系。用户输入工程场景、强度需求、透水需求和施工条件后，系统可自动推荐钢渣粒径、成型方式、孔隙率控制范围和施工方案，并生成工程应用报告与低碳效益分析。现阶段系统为规则约束型 AI 原型，后续可接入正交试验数据库，升级为数据驱动的材料智能设计平台。

## 9. 注意事项

- 当前输出是半经验规则评估，不能替代正式工程设计和检测报告。
- 若用于比赛答辩，请明确说明“现阶段为规则约束型 AI 原型”。
- 硅基流动模型名称可能调整，若接口报模型不可用，请在 `config.yaml` 中更换模型。
# -
# -
