import type { APICategoryGroupEntity } from '@actual-app/api/models';
import { getApi } from '../actual/client.js';

export async function getAllCategoryGroups(
  hidden?: boolean,
): Promise<APICategoryGroupEntity[]> {
  return getApi().getCategoryGroups({ hidden });
}
