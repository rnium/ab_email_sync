import { getApi } from '../actual/client.js';
import type { ImportTransactionsBody } from '../validation/transactionsValidation.js';

export async function importTransactions(
  accountId: string,
  { transactions, opts }: ImportTransactionsBody,
) {
  const api = getApi();

  const withAccount = transactions.map((t) => ({ ...t, account: accountId }));

  return api.importTransactions(accountId, withAccount, opts);
}
