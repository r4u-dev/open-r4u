import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://api.r4u.dev";

if (!API_BASE_URL) {
  throw new Error("VITE_API_BASE_URL is not defined");
}


/**
 * The centralized axios instance.
 */
const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

export default apiClient;
