import { z } from 'zod';

export const CategoryGroupsQuerySchema = z.object({
  hidden: z
    .enum(['true', 'false'])
    .optional()
    .transform((val) => (val === undefined ? undefined : val === 'true')),
});

export type CategoryGroupsQuery = z.infer<typeof CategoryGroupsQuerySchema>;
