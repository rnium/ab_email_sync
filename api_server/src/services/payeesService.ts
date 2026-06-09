import type { APIPayeeEntity } from '@actual-app/api/models';
import {
  type ActualCredentials,
  withActualApi,
} from '../actual/client.js';

export async function getAllPayees(
  credentials: ActualCredentials,
): Promise<APIPayeeEntity[]> {
  return withActualApi(credentials, (api) => api.getPayees());
}
