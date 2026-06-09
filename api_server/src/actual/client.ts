import * as api from "@actual-app/api";
import { validateConfig } from "../config/actual.js";

export interface ActualCredentials {
  readonly password: string;
  readonly syncId: string;
}

let activeCredentials: ActualCredentials | undefined;
let operationQueue = Promise.resolve();

function credentialsMatch(credentials: ActualCredentials): boolean {
  return (
    activeCredentials?.password === credentials.password &&
    activeCredentials.syncId === credentials.syncId
  );
}

async function connect(credentials: ActualCredentials): Promise<void> {
  if (credentialsMatch(credentials)) return;

  if (activeCredentials) {
    await api.shutdown();
    activeCredentials = undefined;
  }

  const config = validateConfig();

  try {
    await api.init({
      dataDir: config.dataDir,
      serverURL: config.serverURL,
      password: credentials.password,
    });

    const downloadOpts = config.budgetPassword
      ? { password: config.budgetPassword }
      : undefined;

    await api.downloadBudget(credentials.syncId, downloadOpts);
    activeCredentials = { ...credentials };
  } catch (error) {
    await api.shutdown().catch(() => undefined);
    activeCredentials = undefined;
    throw error;
  }
}

async function exclusively<T>(operation: () => Promise<T>): Promise<T> {
  const previousOperation = operationQueue;
  let release: () => void = () => undefined;
  operationQueue = new Promise<void>((resolve) => {
    release = resolve;
  });

  await previousOperation;
  try {
    return await operation();
  } finally {
    release();
  }
}

export async function withActualApi<T>(
  credentials: ActualCredentials,
  operation: (actualApi: typeof api) => Promise<T>,
): Promise<T> {
  return exclusively(async () => {
    await connect(credentials);
    return operation(api);
  });
}

export async function disconnect(): Promise<void> {
  await exclusively(async () => {
    if (!activeCredentials) return;
    await api.shutdown();
    activeCredentials = undefined;
  });
}
