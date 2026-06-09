import type { Request, Response } from 'express';
import asyncHandler from '../middleware/asyncHandler.js';
import { getAllPayees } from '../services/payeesService.js';

export const getPayees = asyncHandler(async (_req: Request, res: Response) => {
  const payees = await getAllPayees(res.locals.actualCredentials);
  res.json({ data: payees });
});
