import os from "node:os";
import path from "node:path";

interface ActualConfig {
  readonly dataDir: string;
  readonly serverURL: string | undefined;
  readonly password: string | undefined;
  readonly syncId: string | undefined;
  readonly budgetPassword: string | undefined;
}

interface ValidatedActualConfig {
  readonly dataDir: string;
  readonly serverURL: string;
  readonly password: string;
  readonly syncId: string;
  readonly budgetPassword: string | undefined;
}

const DEFAULT_DATA_DIR = path.join(
  os.homedir(),
  ".local",
  "share",
  "actual-budget",
);

const config: ActualConfig = {
  dataDir: process.env.ACTUAL_DATA_DIR ?? DEFAULT_DATA_DIR,
  serverURL: process.env.ACTUAL_SERVER_URL,
  password: process.env.ACTUAL_PASSWORD,
  syncId: process.env.ACTUAL_SYNC_ID,
  budgetPassword: process.env.ACTUAL_BUDGET_PASSWORD || undefined,
};

export function validateConfig(): ValidatedActualConfig {
  const missing = (
    ["ACTUAL_SERVER_URL", "ACTUAL_PASSWORD", "ACTUAL_SYNC_ID"] as const
  ).filter((key) => !process.env[key]);

  if (missing.length > 0) {
    throw new Error(
      `Missing required environment variable(s): ${missing.join(", ")}\n` +
        "Copy .env.example to .env and fill in the values.",
    );
  }

  return config as ValidatedActualConfig;
}

export default config;
