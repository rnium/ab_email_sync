import type { RequestHandler } from 'express';
import type { ParsedQs } from 'qs';
import { type ZodType } from 'zod';

function makeValidator<T>(
  target: 'body' | 'query' | 'params',
  schema: ZodType<T>,
): RequestHandler {
  return (req, res, next) => {
    const result = schema.safeParse(req[target]);

    if (!result.success) {
      res.status(400).json({
        error: {
          message: 'Validation failed',
          details: result.error.flatten(),
        },
      });
      return;
    }

    if (target === 'body') {
      req.body = result.data;
    } else if (target === 'params') {
      req.params = result.data as Record<string, string>;
    } else {
      req.query = result.data as ParsedQs;
    }

    next();
  };
}

export const validate = {
  body: <T>(schema: ZodType<T>): RequestHandler => makeValidator('body', schema),
  query: <T>(schema: ZodType<T>): RequestHandler => makeValidator('query', schema),
  params: <T>(schema: ZodType<T>): RequestHandler => makeValidator('params', schema),
};
