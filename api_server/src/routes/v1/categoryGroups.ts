import { Router } from 'express';
import { getCategoryGroups } from '../../controllers/categoryGroupsController.js';
import { validate } from '../../middleware/validate.js';
import { CategoryGroupsQuerySchema } from '../../validation/categoryGroupsValidation.js';

const router = Router();

router.get('/', validate.query(CategoryGroupsQuerySchema), getCategoryGroups);

export default router;
