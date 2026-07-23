import type { DataQualityReport, DemoFixture, LifeDiagnosis, RehearsalTaskList } from "../types";

export function getApiBaseUrl(): string {
  if (typeof window !== "undefined" && window.__APP_CONFIG__?.API_BASE_URL) {
    const runtimeUrl = window.__APP_CONFIG__.API_BASE_URL.trim();
    if (runtimeUrl) {
      return runtimeUrl.endsWith("/") ? runtimeUrl.slice(0, -1) : runtimeUrl;
    }
  }
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl && typeof envUrl === "string") {
    return envUrl.trim().endsWith("/") ? envUrl.trim().slice(0, -1) : envUrl.trim();
  }
  return "http://localhost:8000";
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    ...init
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${path} (${response.status})`);
  }

  return (await response.json()) as T;
}

export function getDemoFixture(): Promise<DemoFixture> {
  return requestJson<DemoFixture>("/fixtures/demo");
}

export function runDiagnosis(payload: DemoFixture): Promise<LifeDiagnosis> {
  return requestJson<LifeDiagnosis>("/diagnosis/run", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function generateRehearsals(diagnosis: LifeDiagnosis): Promise<RehearsalTaskList> {
  return requestJson<RehearsalTaskList>("/rehearsals/generate", {
    method: "POST",
    body: JSON.stringify(diagnosis)
  });
}

export function getDataQualityReport(): Promise<DataQualityReport> {
  return requestJson<DataQualityReport>("/data-quality");
}
