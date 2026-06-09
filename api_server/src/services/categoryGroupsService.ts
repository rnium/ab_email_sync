import type { APICategoryGroupEntity } from '@actual-app/api/models';
import {
  type ActualCredentials,
  withActualApi,
} from '../actual/client.js';

export async function getAllCategoryGroups(
  credentials: ActualCredentials,
  hidden?: boolean,
): Promise<APICategoryGroupEntity[]> {
  return withActualApi(credentials, (api) => api.getCategoryGroups({ hidden }));
}
