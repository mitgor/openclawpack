import { describe, it, expect, vi, beforeEach } from "vitest";
import { registerTools } from "../tools.js";

vi.mock("../exec.js", () => ({
  execOpenClawPack: vi.fn(),
}));

import { execOpenClawPack } from "../exec.js";
const mockExec = vi.mocked(execOpenClawPack);

describe("registerTools", () => {
  let registeredTools: Map<string, any>;
  let mockApi: any;

  beforeEach(() => {
    registeredTools = new Map();
    mockApi = {
      registerTool: vi.fn((tool: any) => {
        registeredTools.set(tool.name, tool);
      }),
    };
    vi.clearAllMocks();
  });

  it("registers exactly 4 tools", () => {
    registerTools(mockApi, {
      cliPath: "openclawpack",
      timeout: 300,
    });

    expect(mockApi.registerTool).toHaveBeenCalledTimes(4);
    expect(registeredTools.has("gsd_new_project")).toBe(true);
    expect(registeredTools.has("gsd_plan_phase")).toBe(true);
    expect(registeredTools.has("gsd_execute_phase")).toBe(true);
    expect(registeredTools.has("gsd_status")).toBe(true);
  });

  it("gsd_new_project calls openclawpack new-project with idea", async () => {
    registerTools(mockApi, { cliPath: "openclawpack", timeout: 300 });

    mockExec.mockResolvedValue({ success: true, result: {} });

    const tool = registeredTools.get("gsd_new_project");
    const result = await tool.execute({
      idea: "Build a todo app",
      project_dir: "/tmp/proj",
    });

    expect(mockExec).toHaveBeenCalledWith(
      ["new-project", "-i", "Build a todo app"],
      { cliPath: "openclawpack", timeout: 300, projectDir: "/tmp/proj" }
    );
    expect(result).toEqual({ success: true, result: {} });
  });

  it("gsd_plan_phase calls openclawpack plan-phase with phase number", async () => {
    registerTools(mockApi, { cliPath: "openclawpack", timeout: 300 });

    mockExec.mockResolvedValue({ success: true, result: {} });

    const tool = registeredTools.get("gsd_plan_phase");
    await tool.execute({ phase: 2 });

    expect(mockExec).toHaveBeenCalledWith(["plan-phase", "2"], {
      cliPath: "openclawpack",
      timeout: 300,
      projectDir: undefined,
    });
  });

  it("gsd_execute_phase calls openclawpack execute-phase with phase number", async () => {
    registerTools(mockApi, { cliPath: "openclawpack", timeout: 300 });

    mockExec.mockResolvedValue({ success: true, result: {} });

    const tool = registeredTools.get("gsd_execute_phase");
    await tool.execute({ phase: 1, project_dir: "/tmp/p" });

    expect(mockExec).toHaveBeenCalledWith(["execute-phase", "1"], {
      cliPath: "openclawpack",
      timeout: 300,
      projectDir: "/tmp/p",
    });
  });

  it("gsd_status calls openclawpack status", async () => {
    registerTools(mockApi, { cliPath: "openclawpack", timeout: 300 });

    mockExec.mockResolvedValue({ success: true, result: { phase: 1 } });

    const tool = registeredTools.get("gsd_status");
    const result = await tool.execute({});

    expect(mockExec).toHaveBeenCalledWith(["status"], {
      cliPath: "openclawpack",
      timeout: 300,
      projectDir: undefined,
    });
    expect(result).toEqual({ success: true, result: { phase: 1 } });
  });

  it("tool returns error string on exec failure", async () => {
    registerTools(mockApi, { cliPath: "openclawpack", timeout: 300 });

    mockExec.mockRejectedValue(new Error("CLI not found"));

    const tool = registeredTools.get("gsd_status");
    const result = await tool.execute({});

    expect(result).toEqual({ error: "CLI not found" });
  });
});
