import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--ignore-certificate-errors'] });
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();
  const authorizeUrl = 'https://iam.avrig.ai/auth/v1/oidc/authorize?client_id=avrig-web-ui&redirect_uri=https%3A%2F%2Favrig.ai%2Fauth%2Fcallback&response_type=code&scope=openid+profile+email&state=teststate&code_challenge=dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk&code_challenge_method=S256';
  await page.goto(authorizeUrl, { waitUntil: 'networkidle' });
  const html = await page.evaluate(() => {
    const el = document.querySelector('main') || document.body;
    return el.outerHTML;
  });
  console.log('Main HTML:\n', html);
  await browser.close();
})();
