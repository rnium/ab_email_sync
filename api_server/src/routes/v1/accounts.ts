import { Router } from 'express';
import { getAccounts } from '../../controllers/accountsController.js';
import { importTransactionsHandler } from '../../controllers/transactionsController.js';
import { validate } from '../../middleware/validate.js';
import {
  AccountIdParamsSchema,
  ImportTransactionsBodySchema,
} from '../../validation/transactionsValidation.js';

const router = Router();

router.get('/', getAccounts);

router.post(
  '/:accountId/transactions/import',
  validate.params(AccountIdParamsSchema),
  validate.body(ImportTransactionsBodySchema),
  importTransactionsHandler,
);

export default router;
