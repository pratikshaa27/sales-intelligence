import { describe, expect, it } from "vitest";

import { hasPermission } from "@/lib/permissions";

describe("hasPermission", () => {
  it("returns true when the permission is present", () => {
    expect(hasPermission(["leads.create", "leads.view"], "leads.create")).toBe(true);
  });

  it("returns false when the permission is absent", () => {
    expect(hasPermission(["leads.view"], "leads.create")).toBe(false);
  });

  it("returns false when permissions is undefined (not yet loaded)", () => {
    expect(hasPermission(undefined, "leads.create")).toBe(false);
  });

  it("returns false for an empty permissions list", () => {
    expect(hasPermission([], "leads.create")).toBe(false);
  });
});
