import esbuild from "esbuild";

const production = process.argv[2] === "production";
const context = await esbuild.context({
  entryPoints: ["src/main.ts"],
  bundle: true,
  external: ["obsidian"],
  format: "cjs",
  target: "es2018",
  sourcemap: production ? false : "inline",
  minify: production,
  outfile: "main.js",
  platform: "node"
});

if (production) {
  await context.rebuild();
  await context.dispose();
} else {
  await context.watch();
  console.log("Watching Vault Agent plugin source…");
}
