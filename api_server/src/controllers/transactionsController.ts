import type { Request, Response } from 'express';
import asyncHandler from '../middleware/asyncHandler.js';
import { importTransactions } from '../services/transactionsService.js';
import type {
  AccountIdParams,
  ImportTransactionsBody,
} from '../validation/transactionsValidation.js';

export const importTransactionsHandler = asyncHandler(
  async (req: Request, res: Response) => {
    const { accountId } = req.params as unknown as AccountIdParams;
    const body = req.body as ImportTransactionsBody;

    const result = await importTransactions(accountId, body);
    res.json({ data: result });
  },
);
