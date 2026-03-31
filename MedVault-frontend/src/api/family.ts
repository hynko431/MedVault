import { apiRequest } from "./api";

export const getFamily = () => apiRequest("/api/family");
