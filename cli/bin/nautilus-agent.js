#!/usr/bin/env node
/**
 * Nautilus Agent Platform 脚手架 CLI（零依赖）
 *
 * 用法：
 *   node cli/bin/nautilus-agent.js create <项目名> --template <clinic|generic>
 *   简写：nautilus-agent create my-agent -t clinic
 *
 * 能力：从 cli/templates/<模板名> 复制生成企业级 Agent 工程骨架，
 *       自动替换占位符 {{PROJECT_NAME}}，并输出后续步骤提示。
 */

"use strict";

const fs = require("fs");
const path = require("path");

const TEMPLATES_DIR = path.join(__dirname, "..", "templates");
const AVAILABLE_TEMPLATES = ["clinic", "generic"];

/** 递归复制目录并替换模板占位符 */
function copyTemplate(srcDir, destDir, projectName) {
  fs.mkdirSync(destDir, { recursive: true });
  for (const entry of fs.readdirSync(srcDir, { withFileTypes: true })) {
    const src = path.join(srcDir, entry.name);
    const dest = path.join(destDir, entry.name);
    if (entry.isDirectory()) {
      copyTemplate(src, dest, projectName);
    } else {
      const content = fs
        .readFileSync(src, "utf8")
        .replaceAll("{{PROJECT_NAME}}", projectName);
      fs.writeFileSync(dest, content, "utf8");
    }
  }
}

/** 主入口：解析参数并执行 create 命令 */
function main() {
  const [, , command, projectName, ...rest] = process.argv;

  if (command !== "create") {
    console.error("用法: nautilus-agent create <项目名> --template <clinic|generic>");
    process.exit(1);
  }
  if (!projectName) {
    console.error("错误: 缺少项目名，例如 nautilus-agent create my-agent");
    process.exit(1);
  }

  // 解析 --template / -t 参数
  const tIdx = rest.findIndex((a) => a === "--template" || a === "-t");
  const template = tIdx >= 0 ? rest[tIdx + 1] : "generic";
  if (!AVAILABLE_TEMPLATES.includes(template)) {
    console.error(`错误: 未知模板 "${template}"，可用模板: ${AVAILABLE_TEMPLATES.join(", ")}`);
    process.exit(1);
  }

  const dest = path.resolve(process.cwd(), projectName);
  if (fs.existsSync(dest)) {
    console.error(`错误: 目标目录已存在 ${dest}`);
    process.exit(1);
  }

  copyTemplate(path.join(TEMPLATES_DIR, template), dest, projectName);

  console.log(`✔ 工程已生成: ${dest}`);
  console.log(`  模板: ${template}（${template === "clinic" ? "医疗诊所业务" : "通用业务"}）`);
  console.log("\n后续步骤:");
  console.log(`  cd ${projectName}`);
  console.log("  pip install -r requirements.txt   # 容器化开发时跳过（依赖已在镜像内）");
  console.log("  cp .env.example .env              # 填入 LLM_API_KEY 等");
}

main();
