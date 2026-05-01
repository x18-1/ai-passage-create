/** API 基础路径，由 .env.development / .env.production 中 VITE_API_BASE_URL 注入 */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'
