import type { APIAccountEntity } from '@actual-app/api/models';
import { getApi } from '../actual/client.js';

export async function getAllAccounts(): Promise<APIAccountEntity[]> {
  return getApi().getAccounts();
}
