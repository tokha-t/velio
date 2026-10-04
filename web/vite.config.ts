import { defineConfig } from "vite";

// GitHub Pages serves this project from /velio/ while local Vite stays at /.
export default defineConfig({
  base: process.env.GITHUB_ACTIONS ? "/velio/" : "/",
});
