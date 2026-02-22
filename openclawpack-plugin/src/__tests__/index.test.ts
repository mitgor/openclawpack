import { describe, it, expect, vi, beforeEach } from "vitest";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

vi.mock("../tools.js", () => ({
  registerTools: vi.fn(),
}));

import { registerTools } from "../tools.js";
const mockRegisterTools = vi.mocked(registerTools);

describe("plugin entry", () => {
  let mockApi: any;

  beforeEach(() => {
    mockApi = {
      registerHook: vi.fn(),
      registerTool: vi.fn(),
    };
    vi.clearAllMocks();
  });

  it("exports a default function", async () => {
    const plugin = await import("../index.js");
    expect(typeof plugin.default).toBe("function");
  });

  it("registers agent:bootstrap hook", async () => {
    const plugin = await import("../index.js");
    plugin.default(mockApi);

    expect(mockApi.registerHook).toHaveBeenCalledWith(
      "agent:bootstrap",
      expect.any(Function),
      expect.objectContaining({
        name: "gsd-router.bootstrap",
      })
    );
  });

  it("calls registerTools with config defaults", async () => {
    const plugin = await import("../index.js");
    plugin.default(mockApi);

    expect(mockRegisterTools).toHaveBeenCalledWith(mockApi, {
      cliPath: "openclawpack",
      timeout: 300,
    });
  });

  it("bootstrap hook injects GSD-ROUTER.md content", async () => {
    const plugin = await import("../index.js");
    plugin.default(mockApi);

    const hookCall = mockApi.registerHook.mock.calls.find(
      (c: any[]) => c[0] === "agent:bootstrap"
    );
    const hookFn = hookCall[1];

    const event = {
      context: {
        bootstrapFiles: new Map<string, string>(),
      },
    };

    await hookFn(event);

    expect(event.context.bootstrapFiles.has("GSD-ROUTER.md")).toBe(true);
    const content = event.context.bootstrapFiles.get("GSD-ROUTER.md");
    expect(content).toContain("Task Evaluation Protocol");
    expect(content).toContain("SIMPLE");
    expect(content).toContain("MEDIUM");
    expect(content).toContain("HARD");
  });

  it("skips bootstrap injection when evaluation_enabled is false", async () => {
    const plugin = await import("../index.js");

    const configApi = {
      ...mockApi,
      config: { evaluation_enabled: false },
    };
    plugin.default(configApi);

    const hookCall = configApi.registerHook.mock.calls.find(
      (c: any[]) => c[0] === "agent:bootstrap"
    );
    const hookFn = hookCall[1];

    const event = {
      context: {
        bootstrapFiles: new Map<string, string>(),
      },
    };

    await hookFn(event);

    expect(event.context.bootstrapFiles.has("GSD-ROUTER.md")).toBe(false);
  });
});
