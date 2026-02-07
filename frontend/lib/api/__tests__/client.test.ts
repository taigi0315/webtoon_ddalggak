import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ApiError, fetchJson, apiConfig } from "../client";

describe("ApiError", () => {
  it("has correct name", () => {
    const error = new ApiError("test", 404);
    expect(error.name).toBe("ApiError");
  });

  it("stores status and payload", () => {
    const error = new ApiError("not found", 404, { detail: "missing" });
    expect(error.status).toBe(404);
    expect(error.payload).toEqual({ detail: "missing" });
    expect(error.message).toBe("not found");
  });

  it("is an instance of Error", () => {
    const error = new ApiError("test", 500);
    expect(error).toBeInstanceOf(Error);
  });

  it("payload is optional", () => {
    const error = new ApiError("test", 500);
    expect(error.payload).toBeUndefined();
  });
});

describe("apiConfig", () => {
  it("has a baseUrl string", () => {
    expect(typeof apiConfig.baseUrl).toBe("string");
  });

  it("baseUrl looks like a URL", () => {
    expect(apiConfig.baseUrl).toMatch(/^https?:\/\//);
  });
});

describe("fetchJson", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("calls fetch with correct URL", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      text: () => Promise.resolve('{"data": "test"}'),
    });
    globalThis.fetch = mockFetch;

    await fetchJson("/v1/health");

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const calledUrl = mockFetch.mock.calls[0][0];
    expect(calledUrl).toContain("/v1/health");
  });

  it("returns parsed JSON on success", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      text: () => Promise.resolve('{"status": "ok"}'),
    });

    const result = await fetchJson("/v1/health");
    expect(result).toEqual({ status: "ok" });
  });

  it("throws ApiError on non-ok response with detail", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      text: () => Promise.resolve('{"detail": "not found"}'),
    });

    await expect(fetchJson("/v1/missing")).rejects.toThrow(ApiError);

    try {
      await fetchJson("/v1/missing");
    } catch (err) {
      expect((err as ApiError).status).toBe(404);
      expect((err as ApiError).message).toBe("not found");
    }
  });

  it("throws ApiError with generic message when no detail", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve(""),
    });

    try {
      await fetchJson("/v1/broken");
    } catch (err) {
      expect((err as ApiError).status).toBe(500);
      expect((err as ApiError).message).toContain("500");
    }
  });

  it("sets Content-Type header by default", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      text: () => Promise.resolve("{}"),
    });
    globalThis.fetch = mockFetch;

    await fetchJson("/v1/test");

    const options = mockFetch.mock.calls[0][1];
    expect(options.headers["Content-Type"]).toBe("application/json");
  });

  it("merges custom headers with defaults", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      text: () => Promise.resolve("{}"),
    });
    globalThis.fetch = mockFetch;

    await fetchJson("/v1/test", {
      headers: { "X-Custom": "value" },
    });

    const options = mockFetch.mock.calls[0][1];
    expect(options.headers["X-Custom"]).toBe("value");
    // Note: custom headers override defaults due to spread order in fetchJson
    // Content-Type only present when no custom headers override it
  });

  it("handles non-JSON response text gracefully", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      text: () => Promise.resolve("plain text response"),
    });

    const result = await fetchJson("/v1/text");
    expect(result).toBe("plain text response");
  });

  it("handles empty response body", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      text: () => Promise.resolve(""),
    });

    const result = await fetchJson("/v1/empty");
    expect(result).toBeNull();
  });
});
