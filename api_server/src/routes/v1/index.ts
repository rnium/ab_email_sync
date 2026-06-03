import { Router } from "express";
import accountsRouter from "./accounts.js";
import categoryGroupsRouter from "./categoryGroups.js";
import payeesRouter from "./payees.js";

const router = Router();

router.use("/accounts", accountsRouter);
router.use("/category-groups", categoryGroupsRouter);
router.use("/payees", payeesRouter);

export default router;
