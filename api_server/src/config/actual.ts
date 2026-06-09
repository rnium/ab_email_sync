import os from "node:os";
import path from "node:path";

interface ActualConfig {
  readonly dataDir: string;
  readonly serverURL: string | undefined;
  readonly budgetPassword: string | undefined;
}

interface ValidatedActualConfig {
  readonly dataDir: string;
  readonly serverURL: string;
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
  budgetPassword: process.env.ACTUAL_BUDGET_PASSWORD || undefined,
};

export function validateConfig(): ValidatedActualConfig {
  if (!process.env.ACTUAL_SERVER_URL) {
    throw new Error(
      "Missing required environment variable: ACTUAL_SERVER_URL\n" +
        "Copy .env.example to .env and fill in the values.",
    );
  }

  return config as ValidatedActualConfig;
}

export default config;
