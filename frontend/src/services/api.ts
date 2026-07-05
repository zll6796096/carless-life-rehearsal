import type { DataQualityReport, DemoFixture, LifeDiagnosis, RehearsalTaskList } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
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
