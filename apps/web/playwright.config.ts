import { defineConfig } from '@playwright/test';
export default defineConfig({testDir:'tests',testMatch:'*.spec.ts',use:{baseURL:process.env.NEUROMESH_WEB_URL || 'http://127.0.0.1:5173',browserName:'chromium',channel:'chrome',viewport:{width:1600,height:900}},reporter:'list'});
