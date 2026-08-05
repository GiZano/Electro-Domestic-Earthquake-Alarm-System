import { useAlertStore } from "../store/useAlertStore";

const makeAlert = (overrides = {}) => ({
  type: "CRITICAL",
  alert_id: 1,
  zone_id: 1,
  magnitude: 5.2,
  message: "Test alert",
  timestamp: "2026-01-01T00:00:00Z",
  ...overrides,
});

const makeReport = (overrides = {}) => ({
  type: "EMERGENCY_REPORT" as const,
  alert_id: 1,
  report_id: 1,
  zone_id: 1,
  magnitude: 5.2,
  status: "COMPLETED" as const,
  summary: "A seismic event was detected.",
  recommendations: ["Stay away from windows."],
  timestamp: "2026-01-01T00:01:00Z",
  ...overrides,
});

beforeEach(() => {
  useAlertStore.setState({ alerts: [], reports: {} });
});

describe("useAlertStore", () => {
  it("starts with empty alerts", () => {
    expect(useAlertStore.getState().alerts).toEqual([]);
  });

  it("adds an alert to the front", () => {
    const alert = makeAlert();
    useAlertStore.getState().addAlert(alert);
    expect(useAlertStore.getState().alerts).toHaveLength(1);
    expect(useAlertStore.getState().alerts[0]).toEqual(alert);
  });

  it("keeps only the latest 10 alerts", () => {
    for (let i = 0; i < 15; i++) {
      useAlertStore.getState().addAlert(makeAlert({ magnitude: i }));
    }
    expect(useAlertStore.getState().alerts).toHaveLength(10);
    expect(useAlertStore.getState().alerts[0].magnitude).toBe(14);
  });

  it("clears all alerts", () => {
    useAlertStore.getState().addAlert(makeAlert());
    useAlertStore.getState().addReport(makeReport());
    useAlertStore.getState().clearAlerts();
    expect(useAlertStore.getState().alerts).toEqual([]);
    expect(useAlertStore.getState().reports).toEqual({});
  });

  it("adds a report keyed by alert_id", () => {
    useAlertStore.getState().addReport(makeReport());
    expect(useAlertStore.getState().reports[1]).toMatchObject({ status: "COMPLETED" });
  });

  it("keeps the latest report for the same alert", () => {
    useAlertStore.getState().addReport(makeReport({ status: "COMPLETED" }));
    useAlertStore.getState().addReport(makeReport({ status: "FAILED", summary: undefined }));
    expect(useAlertStore.getState().reports[1].status).toBe("FAILED");
  });

  it("maintains most recent alert order", () => {
    const a1 = makeAlert({ magnitude: 3.0 });
    const a2 = makeAlert({ magnitude: 4.0 });
    const a3 = makeAlert({ magnitude: 5.0 });

    useAlertStore.getState().addAlert(a1);
    useAlertStore.getState().addAlert(a2);
    useAlertStore.getState().addAlert(a3);

    const alerts = useAlertStore.getState().alerts;
    expect(alerts[0].magnitude).toBe(5.0);
    expect(alerts[1].magnitude).toBe(4.0);
    expect(alerts[2].magnitude).toBe(3.0);
  });
});
