import type { APIAccountEntity } from '@actual-app/api/models';
import {
  type ActualCredentials,
  withActualApi,
} from '../actual/client.js';

export async function getAllAccounts(
  credentials: ActualCredentials,
): Promise<APIAccountEntity[]> {
  return withActualApi(credentials, (api) => api.getAccounts());
}
