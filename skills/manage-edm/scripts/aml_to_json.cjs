const { parseAml, generateJsonDatabase } = require("./azimutt-aml.cjs");
const fs = require("fs");

const [, , amlPath, jsonPath] = process.argv;
const content = fs.readFileSync(amlPath, "utf-8");
const parsed = parseAml(content);
if (!parsed.result) {
  console.error("AML parse errors:", JSON.stringify(parsed.errors));
  process.exit(1);
}
fs.writeFileSync(jsonPath, generateJsonDatabase(parsed.result));
console.log(`Converted ${amlPath} -> ${jsonPath}`);