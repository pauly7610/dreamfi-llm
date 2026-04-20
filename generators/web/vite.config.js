import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
    base: '/console/',
    plugins: [react()],
    server: {
        port: 5173,
        proxy: {
            '/api': 'http://127.0.0.1:5001',
            '/v1': 'http://127.0.0.1:5001',
            '/health': 'http://127.0.0.1:5001'
        }
    }
});
