import type { RequestHandler } from "express";

const PASSWORD_HEADER = "x-actual-password";
const SYNC_ID_HEADER = "x-actual-sync-id";

export const requireActualCredentials: RequestHandler = (req, res, next) => {
  const password = req.get(PASSWORD_HEADER);
  const syncId = req.get(SYNC_ID_HEADER);

  if (!password?.trim() || !syncId?.trim()) {
    res.status(401).json({
      error: {
        message:
          "X-Actual-Password and X-Actual-Sync-Id headers are required",
      },
    });
    return;
  }

  res.locals.actualCredentials = { password, syncId: syncId.trim() };
  next();
};
