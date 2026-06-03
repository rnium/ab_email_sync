import * as api from "@actual-app/api";
import { validateConfig } from "../config/actual.js";

let initialized = false;

export async function connect(): Promise<void> {
  if (initialized) return;

  const config = validateConfig();

  await api.init({
    dataDir: config.dataDir,
    serverURL: config.serverURL,
    password: config.password,
  });

  const downloadOpts = config.budgetPassword
    ? { password: config.budgetPassword }
    : undefined;

  await api.downloadBudget(config.syncId, downloadOpts);

  initialized = true;
}

export async function disconnect(): Promise<void> {
  if (!initialized) return;
  await api.shutdown();
  initialized = false;
}

export function getApi(): typeof api {
  if (!initialized) {
    const err = Object.assign(
      new Error("Actual Budget API is not initialized"),
      { status: 503 },
    );
    throw err;
  }
  return api;
}
