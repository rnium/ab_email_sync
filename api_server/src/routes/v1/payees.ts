import { Router } from 'express';
import { getPayees } from '../../controllers/payeesController.js';

const router = Router();

router.get('/', getPayees);

export default router;
