import express, { type Express } from 'express';
import { errorHandler } from './middleware/errorHandler.js';
import router from './routes/index.js';

const app: Express = express();

app.use(express.json());

app.get('/health', (_req, res) => {
  res.status(200).json({ status: 'ok' });
});

app.use('/api', router);
app.use(errorHandler);

export default app;
