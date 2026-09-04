import { describe, expect, it } from "vitest";

import {
  companyFormSchema,
  createLeadFormSchema,
  loginSchema,
  registerSchema,
} from "@/lib/validations";

describe("loginSchema", () => {
  it("accepts a valid email and non-empty password", () => {
    const result = loginSchema.safeParse({ email: "user@example.com", password: "x" });
    expect(result.success).toBe(true);
  });

  it("rejects an invalid email address", () => {
    const result = loginSchema.safeParse({ email: "not-an-email", password: "x" });
    expect(result.success).toBe(false);
  });

  it("rejects an empty password", () => {
    const result = loginSchema.safeParse({ email: "user@example.com", password: "" });
    expect(result.success).toBe(false);
  });
});

describe("registerSchema password rules", () => {
  const base = {
    organization_name: "Acme Inc",
    admin_full_name: "Ada Admin",
    admin_email: "admin@example.com",
  };

  it("accepts a password with 12+ chars, an uppercase letter, and a digit", () => {
    const result = registerSchema.safeParse({ ...base, admin_password: "SuperSecret123" });
    expect(result.success).toBe(true);
  });

  it("rejects a password under 12 characters", () => {
    const result = registerSchema.safeParse({ ...base, admin_password: "Short1" });
    expect(result.success).toBe(false);
  });

  it("rejects a password with no uppercase letter", () => {
    const result = registerSchema.safeParse({ ...base, admin_password: "lowercase123456" });
    expect(result.success).toBe(false);
  });

  it("rejects a password with no digit", () => {
    const result = registerSchema.safeParse({ ...base, admin_password: "NoDigitsHereAtAll" });
    expect(result.success).toBe(false);
  });
});

describe("companyFormSchema", () => {
  it("rejects a blank website (dedup key would be unresolvable)", () => {
    const result = companyFormSchema.safeParse({ name: "Acme Robotics", website: "" });
    expect(result.success).toBe(false);
  });

  it("accepts a minimal valid company with defaults filled in", () => {
    const result = companyFormSchema.safeParse({
      name: "Acme Robotics",
      website: "https://acme.com",
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.locations).toEqual([]);
      expect(result.data.confidence_score).toBe(0);
    }
  });
});

describe("createLeadFormSchema", () => {
  it("requires company_id and product_id to be valid UUIDs", () => {
    const result = createLeadFormSchema.safeParse({
      company_id: "not-a-uuid",
      product_id: "not-a-uuid",
      name: "A lead",
    });
    expect(result.success).toBe(false);
  });

  it("accepts a well-formed lead with an empty (unselected) contact_id", () => {
    const result = createLeadFormSchema.safeParse({
      company_id: "11111111-1111-1111-1111-111111111111",
      product_id: "22222222-2222-2222-2222-222222222222",
      contact_id: "",
      name: "Acme - Sales Copilot",
    });
    expect(result.success).toBe(true);
  });
});
