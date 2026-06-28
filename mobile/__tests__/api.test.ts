import { api } from "../services/api";

beforeEach(() => {
  jest.resetAllMocks();
});

describe("API Service", () => {
  it("get fetches data correctly", async () => {
    const mockData = { id: 1, city: "Test" };
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue(mockData),
    });

    const result = await api.get("/zones/");
    expect(result).toEqual(mockData);
    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/zones/"
    );
  });

  it("get throws on non-ok response", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 500,
    });

    await expect(api.get("/zones/")).rejects.toThrow("HTTP Error: 500");
  });

  it("get throws on network error", async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error("Network failed"));
    await expect(api.get("/zones/")).rejects.toThrow("Network failed");
  });

  it("post sends JSON body", async () => {
    const body = { city: "New Zone" };
    const mockResponse = { id: 1, city: "New Zone" };
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue(mockResponse),
    });

    const result = await api.post("/zones/", body);
    expect(result).toEqual(mockResponse);
    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/zones/",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
    );
  });

  it("post throws on error", async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error("POST failed"));
    await expect(api.post("/zones/", {})).rejects.toThrow("POST failed");
  });
});
