import { useQuakeStore } from "../store/quakeStore";
import { usePreferencesStore } from "../store/usePreferencesStore";

beforeEach(() => {
  useQuakeStore.setState({
    systemStatus: "SECURE",
    sensors: [],
    lastAlertTime: null,
  });
  usePreferencesStore.setState({
    isOfflineMode: false,
    notificationsEnabled: true,
  });
  jest.useFakeTimers();
});

afterEach(() => {
  useQuakeStore.getState().stopMonitoring();
  jest.useRealTimers();
});

describe("useQuakeStore", () => {
  it("starts with SECURE status", () => {
    expect(useQuakeStore.getState().systemStatus).toBe("SECURE");
  });

  it("starts with empty sensors", () => {
    expect(useQuakeStore.getState().sensors).toEqual([]);
  });

  it("fetchSensors handles network error gracefully", async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error("Network error"));
    await useQuakeStore.getState().fetchSensors();
    expect(useQuakeStore.getState().sensors).toEqual([]);
  });

  it("fetchSensors parses response correctly", async () => {
    const mockSensors = [
      { id: 1, lat: 41.9, lon: 12.5, status: "Active" },
    ];
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue(mockSensors),
    });
    await useQuakeStore.getState().fetchSensors();
    expect(useQuakeStore.getState().sensors).toEqual(mockSensors);
  });

  it("startMonitoring sets up polling interval", () => {
    const spy = jest.spyOn(global, "setInterval");
    useQuakeStore.getState().startMonitoring();
    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledWith(expect.any(Function), 2000);
    spy.mockRestore();
  });

  it("stopMonitoring clears polling interval", () => {
    useQuakeStore.getState().startMonitoring();
    useQuakeStore.getState().stopMonitoring();
    expect(useQuakeStore.getState().systemStatus).toBe("SECURE");
  });

  it("does not start multiple intervals", () => {
    const spy = jest.spyOn(global, "setInterval");
    useQuakeStore.getState().startMonitoring();
    useQuakeStore.getState().startMonitoring();
    expect(spy).toHaveBeenCalledTimes(1);
    spy.mockRestore();
  });
});
