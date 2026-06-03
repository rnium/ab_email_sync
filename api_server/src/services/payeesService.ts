import type { APIPayeeEntity } from '@actual-app/api/models';
import { getApi } from '../actual/client.js';

export async function getAllPayees(): Promise<APIPayeeEntity[]> {
  return getApi().getPayees();
}
