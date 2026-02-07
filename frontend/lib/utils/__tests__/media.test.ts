import { describe, it, expect, vi, beforeEach } from "vitest";

// We need to test with different env values, so we re-import each time
describe("getImageUrl", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("returns empty string for empty input", async () => {
    const { getImageUrl } = await import("../media");
    expect(getImageUrl("")).toBe("");
  });

  it("returns full URL unchanged for http URLs", async () => {
    const { getImageUrl } = await import("../media");
    expect(getImageUrl("http://example.com/img.png")).toBe(
      "http://example.com/img.png"
    );
  });

  it("returns full URL unchanged for https URLs", async () => {
    const { getImageUrl } = await import("../media");
    expect(getImageUrl("https://cdn.example.com/img.png")).toBe(
      "https://cdn.example.com/img.png"
    );
  });

  it("prepends API base URL for /media/ paths", async () => {
    const { getImageUrl } = await import("../media");
    const result = getImageUrl("/media/images/abc.png");
    expect(result).toContain("/media/images/abc.png");
    expect(result).toMatch(/^https?:\/\//);
  });

  it("prepends API base URL for media/ paths without leading slash", async () => {
    const { getImageUrl } = await import("../media");
    const result = getImageUrl("media/images/abc.png");
    expect(result).toContain("media/images/abc.png");
    expect(result).toMatch(/^https?:\/\//);
  });

  it("prepends API base URL for other relative paths", async () => {
    const { getImageUrl } = await import("../media");
    const result = getImageUrl("/some/path.png");
    expect(result).toContain("/some/path.png");
    expect(result).toMatch(/^https?:\/\//);
  });

  it("prepends API base URL for bare filenames", async () => {
    const { getImageUrl } = await import("../media");
    const result = getImageUrl("image.png");
    expect(result).toContain("image.png");
    expect(result).toMatch(/^https?:\/\//);
  });
});

describe("getApiBaseUrl", () => {
  it("returns a string", async () => {
    const { getApiBaseUrl } = await import("../media");
    expect(typeof getApiBaseUrl()).toBe("string");
  });

  it("returns a URL-like value", async () => {
    const { getApiBaseUrl } = await import("../media");
    expect(getApiBaseUrl()).toMatch(/^https?:\/\//);
  });
});
