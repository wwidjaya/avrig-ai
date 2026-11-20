// The one place a browser session is seeded.
//
// Every row that needs an authenticated console calls seedSession. The three
// keys below are the contract: an OIDC user in sessionStorage under the exact
// key react-oidc-context derives, plus the two flags the shell reads. The theme
// and language keys are added because the computed-style rows set them, and a
// fixture that writes the wrong theme key leaves every row in dark while still
// reporting a pass (see the `avrig-ui-theme` defect in the plan).
export const OIDC_STORAGE_KEY = "oidc.user:https://iam.avrig.ai:avrig-web-ui";

export const TEST_USER = {
  id_token: "qa.id.token",
  access_token: "qa.access.token",
  refresh_token: "qa.refresh.token",
  token_type: "Bearer",
  scope: "openid profile email",
  profile: {
    sub: "qa-operator-0001",
    email: "qa.operator@avrig.ai",
    name: "QA Operator",
    preferred_username: "qa.operator"
  },
  expires_at: Math.floor(Date.now() / 1000) + 86400,
  expired_at: Math.floor(Date.now() / 1000) + 86400
};

export async function seedSession(page, { theme = "dark", lang = "en", user = TEST_USER } = {}) {
  await page.addInitScript(
    ({ theme, lang, user, oidcKey }) => {
      try {
        sessionStorage.setItem(oidcKey, JSON.stringify(user));
        localStorage.setItem("avrig-logged-in", "true");
        localStorage.setItem("avrig-operator-mode", "true");
        localStorage.setItem("avrig-theme", theme);
        localStorage.setItem("avrig-lang", lang);
      } catch {
        // A storage failure surfaces as an unauthenticated render, which the
        // row's adoption read-back reports rather than hiding here.
      }
    },
    { theme, lang, user, oidcKey: OIDC_STORAGE_KEY }
  );
}
