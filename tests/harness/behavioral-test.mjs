/**
 * Behavioral tests for harness extensions.
 * Run with: npx tsx tests/harness/behavioral-test.mjs
 * Or integrated into the main test suite via spawn.
 */
import assert from "node:assert/strict";
import { createMockExtensionAPI } from "./utils.ts";

async function loadExtension(name) {
  const mod = await import(`../../extensions/${name}/index.ts`);
  return mod.default;
}

async function run() {
  console.log("Testing fusion extension registers fusion tool...");
  {
    const fusion = await loadExtension("fusion");
    const api = createMockExtensionAPI();
    fusion(api.pi);
    assert.ok(api.getTool("fusion"), "fusion tool should be registered");
    const tool = api.getTool("fusion");
    assert.equal(tool.name, "fusion");
    assert.equal(tool.label, "MiniMax Fusion");
    assert.ok(tool.description.includes("deliberation panel"));
    assert.ok(tool.parameters, "fusion should have parameters schema");
    assert.ok(tool.execute, "fusion should have execute function");
    console.log("  ✓ fusion tool registered correctly");
  }

  console.log("Testing subagent extension registers subagent tool...");
  {
    const subagent = await loadExtension("subagent");
    const api = createMockExtensionAPI();
    subagent(api.pi);
    assert.ok(api.getTool("subagent"), "subagent tool should be registered");
    const tool = api.getTool("subagent");
    assert.equal(tool.name, "subagent");
    assert.equal(tool.label, "Run Subagent");
    assert.ok(tool.description.includes("child pi process"));
    assert.ok(tool.parameters, "subagent should have parameters schema");
    assert.ok(tool.execute, "subagent should have execute function");
    console.log("  ✓ subagent tool registered correctly");
  }

  console.log("Testing long-task extension registers all 4 tools...");
  {
    const longTask = await loadExtension("long-task");
    const api = createMockExtensionAPI();
    longTask(api.pi);
    assert.ok(api.getTool("long_task_start"), "long_task_start should be registered");
    assert.ok(api.getTool("long_task_resume"), "long_task_resume should be registered");
    assert.ok(api.getTool("long_task_checkpoint"), "long_task_checkpoint should be registered");
    assert.ok(api.getTool("long_task_finish"), "long_task_finish should be registered");
    const start = api.getTool("long_task_start");
    assert.ok(start.description.includes("progress file"));
    const resume = api.getTool("long_task_resume");
    assert.ok(resume.description.includes("fresh context"));
    console.log("  ✓ long_task tools registered correctly");
  }

  console.log("Testing load-skill extension registers load_skill and list_skills...");
  {
    const loadSkill = await loadExtension("load-skill");
    const api = createMockExtensionAPI();
    loadSkill(api.pi);
    assert.ok(api.getTool("load_skill"), "load_skill should be registered");
    assert.ok(api.getTool("list_skills"), "list_skills should be registered");
    const loadTool = api.getTool("load_skill");
    assert.ok(loadTool.description.includes("skill by name"));
    assert.ok(loadTool.execute, "load_skill should have execute function");
    const listTool = api.getTool("list_skills");
    assert.ok(listTool.description.includes("enumerate"));
    assert.ok(listTool.execute, "list_skills should have execute function");
    console.log("  ✓ load_skill and list_skills registered correctly");
  }

  console.log("Testing repo-map extension registers repo_map tool...");
  {
    const repoMap = await loadExtension("repo-map");
    const api = createMockExtensionAPI();
    repoMap(api.pi);
    assert.ok(api.getTool("repo_map"), "repo_map should be registered");
    const tool = api.getTool("repo_map");
    assert.equal(tool.name, "repo_map");
    assert.equal(tool.label, "Repo Map");
    assert.ok(tool.description.includes("dependency-graph"));
    assert.ok(tool.parameters, "repo_map should have parameters schema");
    assert.ok(tool.execute, "repo_map should have execute function");
    console.log("  ✓ repo_map tool registered correctly");
  }

  console.log("\nAll behavioral tests passed!");
}

run().catch((err) => {
  console.error("Test failed:", err);
  process.exit(1);
});
