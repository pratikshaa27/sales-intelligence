import { AxiosError, AxiosHeaders } from "axios";
import { describe, expect, it } from "vitest";

import { extractApiErrorMessage } from "@/lib/api";

function axiosErrorWithBody(body: unknown, status = 422): AxiosError {
  const error = new AxiosError("Request failed");
  error.response = {
    data: body,
    status,
    statusText: "",
    headers: {},
    config: { headers: new AxiosHeaders() },
  };
  return error;
}

describe("extractApiErrorMessage", () => {
  it("extracts the backend's error message from a well-formed API error response", () => {
    const error = axiosErrorWithBody({
      success: false,
      error: { code: "VALIDATION_ERROR", message: "Website is required", details: {} },
    });
    expect(extractApiErrorMessage(error)).toBe("Website is required");
  });

  it("falls back to the provided default when the response has no error message", () => {
    const error = axiosErrorWithBody({});
    expect(extractApiErrorMessage(error, "Could not save")).toBe("Could not save");
  });

  it("falls back to a generic default for a non-axios error (e.g. a thrown string)", () => {
    expect(extractApiErrorMessage(new Error("boom"))).toBe("Something went wrong");
  });

  it("uses the caller's custom fallback for a non-axios error", () => {
    expect(extractApiErrorMessage("not an error object", "Custom fallback")).toBe(
      "Custom fallback",
    );
  });
});
