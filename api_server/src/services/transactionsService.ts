import type { TransactionEntity } from "@actual-app/core/types/models";
import {
  type ActualCredentials,
  withActualApi,
} from "../actual/client.js";
import { fromActualAmount, toActualAmount } from "../utils/amount.js";
import type { ImportTransactionsBody } from "../validation/transactionsValidation.js";

function fromActualTransaction(t: TransactionEntity): TransactionEntity {
  return {
    ...t,
    amount: fromActualAmount(t.amount),
    ...(t.subtransactions && {
      subtransactions: t.subtransactions.map(fromActualTransaction),
    }),
  };
}

export async function importTransactions(
  credentials: ActualCredentials,
  accountId: string,
  { transactions, opts }: ImportTransactionsBody,
) {
  const withAccount = transactions.map((t) => ({
    ...t,
    account: accountId,
    ...(t.amount !== undefined ? { amount: toActualAmount(t.amount) } : {}),
    ...(t.subtransactions
      ? {
          subtransactions: t.subtransactions.map((sub) => ({
            ...sub,
            amount: toActualAmount(sub.amount),
          })),
        }
      : {}),
  }));

  const result = await withActualApi(credentials, (api) =>
    api.importTransactions(accountId, withAccount, opts),
  );

  return {
    ...result,
    updatedPreview: result.updatedPreview.map((preview) => ({
      ...preview,
      transaction: fromActualTransaction(preview.transaction),
      ...(preview.existing && {
        existing: fromActualTransaction(preview.existing),
      }),
    })),
  };
}
