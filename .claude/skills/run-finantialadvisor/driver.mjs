// Drives the Financial Advisor Streamlit dashboard headlessly with
// Playwright: cadastra um ticker, roda coleta+3 análises, gera conclusão e
// recomendação, tirando screenshot em cada etapa. See SKILL.md for usage.
//
// Usage: node driver.mjs [ticker] [baseUrl]
//   ticker  default: PETR4.SA
//   baseUrl default: http://localhost:8501

import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";

const ticker = process.argv[2] || "PETR4.SA";
const baseUrl = process.argv[3] || "http://localhost:8501";
const outDir = "/tmp/run-finantialadvisor/screenshots";
mkdirSync(outDir, { recursive: true });

const consoleErrors = [];

function shot(page, name) {
  return page.screenshot({ path: `${outDir}/${name}.png`, fullPage: true });
}

async function main() {
  const browser = await chromium.launch({ args: ["--no-sandbox"] });
  const page = await (await browser.newContext()).newPage();
  page.on("pageerror", (e) => consoleErrors.push(`pageerror: ${e}`));
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(`console.error: ${msg.text()}`);
  });

  console.log(`[driver] nav ${baseUrl}`);
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.waitForSelector("text=Financial Advisor", { timeout: 20000 });
  await shot(page, "00_home");

  console.log("[driver] -> Buscar Ativo");
  await page.click("text=Buscar Ativo");
  await page.waitForSelector('text=Ticker do ativo', { timeout: 20000 });

  await page.locator('input[aria-label*="Ticker"]').first().fill(ticker);
  await page.click('button:has-text("Buscar / Cadastrar")');
  await page.waitForSelector("text=pronto (asset_id=", { timeout: 20000 });
  await shot(page, "01_cadastrado");

  console.log(`[driver] Coletar e Analisar (${ticker}) — chama yfinance/brapi.dev/NewsAPI de verdade`);
  await page.click('button:has-text("Coletar e Analisar")');
  // A sidebar já contém o texto "Fundamentalista" antes de clicar, então não
  // dá pra esperar por ele aparecer para saber que terminou. E esperar só
  // "hidden" tem race: se o spinner ainda não tiver renderizado no instante
  // do check, "hidden" (elemento ausente) resolve na hora, cedo demais.
  // Por isso espera aparecer PRIMEIRO, depois sumir.
  const spinner = "text=Coletando dados e rodando as 3 análises...";
  await page.waitForSelector(spinner, { state: "visible", timeout: 10000 });
  await page.waitForSelector(spinner, { state: "hidden", timeout: 60000 });
  await page.waitForTimeout(500);
  await shot(page, "02_coletado");
  writeFileSync(`${outDir}/02_body.txt`, await page.textContent("body"));

  console.log("[driver] -> Conclusão e Recomendação");
  await page.click("text=Conclusão e Recomendação");
  await page.waitForSelector('text=Conclusão e Recomendação', { timeout: 20000 });

  await page.click('button:has-text("Gerar Conclusão")');
  await page.waitForSelector("text=Conclusão gerada com sucesso", { timeout: 30000 });
  await shot(page, "03_conclusao");

  await page.click('button:has-text("Gerar Recomendação")');
  await page.waitForSelector("text=Recomendação gerada com sucesso", { timeout: 30000 });
  await shot(page, "04_recomendacao");
  writeFileSync(`${outDir}/04_body.txt`, await page.textContent("body"));

  await browser.close();

  console.log(`[driver] screenshots em ${outDir}`);
  console.log(`[driver] console errors: ${consoleErrors.length}`);
  for (const e of consoleErrors) console.log(`  - ${e}`);

  if (consoleErrors.length > 0) process.exitCode = 1;
}

main().catch((err) => {
  console.error("[driver] FALHOU:", err);
  process.exit(1);
});
