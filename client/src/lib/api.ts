const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI(path: string, options?: RequestInit) {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      headers: { "Content-Type": "application/json", ...options?.headers },
      ...options,
    });
  } catch (err) {
    throw new Error(
      `Cannot connect to backend (${API_URL}). Make sure the server is running.`
    );
  }
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = typeof error.detail === "string"
      ? error.detail
      : Array.isArray(error.detail)
        ? error.detail.map((d: Record<string, string>) => d.msg || d.type).join("; ")
        : `Server error (${res.status})`;
    throw new Error(detail);
  }
  return res.json();
}

// Chains
export const getChains = (enabledOnly = false) =>
  fetchAPI(`/api/chains${enabledOnly ? "?enabled_only=true" : ""}`);

// Assets
export const getAssets = (chain?: string) =>
  fetchAPI(`/api/assets${chain ? `?chain=${encodeURIComponent(chain)}` : ""}`);
export const getAsset = (id: number) => fetchAPI(`/api/assets/${id}`);
export const createAsset = (data: Record<string, unknown>) =>
  fetchAPI("/api/assets", { method: "POST", body: JSON.stringify(data) });

// Holders
export const getHolders = (assetId: number) =>
  fetchAPI(`/api/assets/${assetId}/holders`);
export const addToWhitelist = (assetId: number, data: Record<string, unknown>) =>
  fetchAPI(`/api/assets/${assetId}/whitelist`, { method: "POST", body: JSON.stringify(data) });

// Compliance
export const getCompliance = (assetId: number) =>
  fetchAPI(`/api/assets/${assetId}/compliance`);
export const validateTransfer = (assetId: number, fromId: string, toId: string, amount: number) =>
  fetchAPI(`/api/assets/${assetId}/validate-transfer?from_id=${fromId}&to_id=${toId}&amount=${amount}`, { method: "POST" });

// Lifecycle
export const distributeCoupon = (assetId: number) =>
  fetchAPI(`/api/assets/${assetId}/distribute-coupon`, { method: "POST" });
export const updateNav = (assetId: number, nav: number) =>
  fetchAPI(`/api/assets/${assetId}/update-nav?nav=${nav}`, { method: "POST" });
export const matureAsset = (assetId: number) =>
  fetchAPI(`/api/assets/${assetId}/mature`, { method: "POST" });

// Events
export const getEvents = (assetId: number) =>
  fetchAPI(`/api/assets/${assetId}/events`);
export const getUpcomingEvents = (limit = 10, chain?: string) =>
  fetchAPI(`/api/events/upcoming?limit=${limit}${chain ? `&chain=${encodeURIComponent(chain)}` : ""}`);

// Audit Log
export const getAuditLog = (assetId: number) =>
  fetchAPI(`/api/assets/${assetId}/audit-log`);

// Reports
export const getReports = (assetId: number) =>
  fetchAPI(`/api/assets/${assetId}/reports`);
export const generateReport = (assetId: number, reportType = "compliance", period = "Q1 2026") =>
  fetchAPI(`/api/assets/${assetId}/reports?report_type=${reportType}&period=${period}`, { method: "POST" });

// Purchase
export const purchaseTokens = (assetId: number, accountId: string, amount: number) =>
  fetchAPI(`/api/assets/${assetId}/purchase`, {
    method: "POST",
    body: JSON.stringify({ account_id: accountId, amount }),
  });

// Chat
export const sendChat = (message: string, history: { role: string; content: string }[] = []) =>
  fetchAPI("/api/chat", { method: "POST", body: JSON.stringify({ message, history }) });

// OFAC
export const screenOFAC = (data: { name?: string; address?: string }) =>
  fetchAPI("/api/ofac/screen", { method: "POST", body: JSON.stringify(data) });
export const getOFACStatus = () => fetchAPI("/api/ofac/status");
export const refreshOFACData = () =>
  fetchAPI("/api/ofac/refresh", { method: "POST" });

// Health
export const checkHealth = () => fetchAPI("/health");
