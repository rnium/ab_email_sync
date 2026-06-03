import "dotenv/config";
import { mkdir } from "node:fs/promises";
import app from "./app.js";
import { connect, disconnect } from "./actual/client.js";
import config from "./config/actual.js";

const PORT = process.env.PORT ?? "3000";

async function start(): Promise<void> {
  await mkdir(config.dataDir, { recursive: true });
  console.log(`Data directory: ${config.dataDir}`);

  await connect();

  const server = app.listen(Number(PORT), () => {
    console.log(`Server running on port ${PORT}`);
  });

  async function shutdown(): Promise<void> {
    server.close();
    await disconnect();
    process.exit(0);
  }

  process.on("SIGTERM", () => void shutdown());
  process.on("SIGINT", () => void shutdown());
}

start().catch((err: unknown) => {
  console.error("Failed to start server:", err);
  process.exit(1);
});
