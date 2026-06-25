// src/services/api.js
// Talks to the FastAPI backend (back_main.py), which reads from Supabase.

import axios from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 5000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Fetch all topics for the student-facing Topics page.
 *
 * BACKEND: GET /api/topics
 * RESPONSE: { topics: [{ id, title, summary, source, source_url, date, score, decision }], total }
 */
export const getActiveTopics = async () => {
  const response = await api.get('/api/topics');
  return response.data;
};

/**
 * Fetch a single topic by id.
 *
 * BACKEND: GET /api/topics/{id}
 */
export const getTopicById = async (id) => {
  const response = await api.get(`/api/topics/${id}`);
  return response.data;
};

/**
 * Trigger the AI pipeline to generate and push new topics to Supabase.
 *
 * BACKEND: POST /api/run-pipeline
 * Runs __main__.py via subprocess using the same venv Python.
 * Times out after 5 minutes.
 */
export const runPipeline = async () => {
  const response = await api.post('/api/run-pipeline', {}, { timeout: 620000 });
  return response.data;
};

export default {
  getActiveTopics,
  getTopicById,
  runPipeline,
};