import { z } from "zod";

const SubtransactionSchema = z.object({
  amount: z.number(),
  category: z.string().optional(),
  notes: z.string().optional(),
});

const TransactionSchema = z.object({
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Must be in YYYY-MM-DD format"),
  amount: z.number().optional(),
  payee: z.string().nullable().optional(),
  payee_name: z.string().optional(),
  imported_payee: z.string().optional(),
  category: z.string().optional(),
  notes: z.string().optional(),
  imported_id: z.string().optional(),
  transfer_id: z.string().optional(),
  cleared: z.boolean().optional(),
  subtransactions: z.array(SubtransactionSchema).optional(),
});

const ImportOptsSchema = z.object({
  defaultCleared: z.boolean().optional(),
  dryRun: z.boolean().optional(),
  reimportDeleted: z.boolean().optional(),
});

export const AccountIdParamsSchema = z.object({
  accountId: z.string().min(1, "accountId is required"),
});

export const ImportTransactionsBodySchema = z.object({
  transactions: z
    .array(TransactionSchema)
    .min(1, "At least one transaction is required"),
  opts: ImportOptsSchema.optional(),
});

export type AccountIdParams = z.infer<typeof AccountIdParamsSchema>;
export type ImportTransactionsBody = z.infer<
  typeof ImportTransactionsBodySchema
>;
