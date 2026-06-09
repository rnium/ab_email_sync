import type { Request, Response } from 'express';
import asyncHandler from '../middleware/asyncHandler.js';
import { getAllAccounts } from '../services/accountsService.js';

export const getAccounts = asyncHandler(async (_req: Request, res: Response) => {
  const accounts = await getAllAccounts(res.locals.actualCredentials);
  res.json({ data: accounts });
});
