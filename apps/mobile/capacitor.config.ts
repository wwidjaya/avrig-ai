import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "ai.avrig.mobile",
  appName: "avrig.ai",
  webDir: "dist",
  server: {
    url: "https://app.avrig.ai",
    cleartext: false
  }
};

export default config;
