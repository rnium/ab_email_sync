import type { Request, Response } from 'express';
import asyncHandler from '../middleware/asyncHandler.js';
import { getAllCategoryGroups } from '../services/categoryGroupsService.js';
import type { CategoryGroupsQuery } from '../validation/categoryGroupsValidation.js';

export const getCategoryGroups = asyncHandler(
  async (req: Request, res: Response) => {
    const { hidden } = req.query as unknown as CategoryGroupsQuery;
    const groups = await getAllCategoryGroups(
      res.locals.actualCredentials,
      hidden,
    );
    res.json({ data: groups });
  },
);
