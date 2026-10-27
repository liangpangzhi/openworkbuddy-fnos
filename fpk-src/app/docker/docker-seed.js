// 安装向导里填写的模型信息 → config.json 的 models 段
// 只在 ai.env 里有非空 API Key 时调用；已存在的 config.json 会被保留，只补 models / active_model。
"use strict";
const fs = require("fs");
const path = require("path");

const DATA = process.env.OPENWORKBUDDY_HOME || "/data";
const cfgFile = path.join(DATA, "config.json");
const envFile = path.join(DATA, "ai.env");

function readEnv(file) {
  const out = {};
  try {
    for (const line of fs.readFileSync(file, "utf8").split(/\r?\n/)) {
      const i = line.indexOf("=");
      if (i <= 0) continue;
      out[line.slice(0, i).trim()] = line.slice(i + 1).trim();
    }
  } catch {
    /* 文件不存在就算了 */
  }
  return out;
}

const env = readEnv(envFile);
const apiKey = env.OWB_API_KEY || "";
if (!apiKey) {
  console.log("[seed] 未填写 API Key，跳过模型种子配置");
  process.exit(0);
}

const provider = (env.OWB_PROVIDER || "deepseek").toLowerCase();
const PRESETS = {
  deepseek: { name: "DeepSeek", base_url: "https://api.deepseek.com/v1", model: "deepseek-chat" },
  qwen: { name: "通义Qwen", base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1", model: "qwen-max" },
  zhipu: { name: "智谱GLM", base_url: "https://open.bigmodel.cn/api/paas/v4", model: "glm-4-plus" },
  kimi: { name: "Kimi", base_url: "https://api.moonshot.cn/v1", model: "moonshot-v1-32k" },
  doubao: { name: "火山方舟", base_url: "https://ark.cn-beijing.volces.com/api/v3", model: "" },
  openai: { name: "OpenAI", base_url: "https://api.openai.com/v1", model: "gpt-4o" },
  claude: { name: "Anthropic Claude", base_url: "", model: "claude-sonnet-4-5" },
  openrouter: { name: "OpenRouter", base_url: "https://openrouter.ai/api/v1", model: "" },
  ollama: { name: "Ollama本地", base_url: "http://host.docker.internal:11434/v1", model: "qwen3:14b" },
};

const preset = PRESETS[provider] || PRESETS.deepseek;
const baseUrl = env.OWB_BASE_URL || preset.base_url;
const model = env.OWB_MODEL || preset.model;
const name = preset.name;
const proto = provider === "claude" ? "anthropic" : "openai";

let cfg = {};
try {
  cfg = JSON.parse(fs.readFileSync(cfgFile, "utf8"));
} catch {
  try {
    cfg = JSON.parse(fs.readFileSync("/app/config.example.json", "utf8"));
  } catch {
    cfg = {};
  }
}

const row = { name, provider: proto, base_url: baseUrl, api_key: apiKey, model };
cfg.models = Array.isArray(cfg.models) ? cfg.models.filter((m) => m && String(m.api_key || "").trim()) : [];
cfg.models.push(row);
cfg.active_model = name;
if (proto === "anthropic") {
  cfg.provider = "anthropic";
  cfg.anthropic = Object.assign({}, cfg.anthropic, { api_key: apiKey, model });
} else {
  cfg.provider = "openai";
  cfg.openai = Object.assign({}, cfg.openai, { base_url: baseUrl, api_key: apiKey, model });
}

fs.writeFileSync(cfgFile, JSON.stringify(cfg, null, 2), { mode: 0o600 });
console.log(`[seed] 已写入模型配置：${name} / ${model}`);
