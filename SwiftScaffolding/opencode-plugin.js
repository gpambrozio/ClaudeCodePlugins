import { createOpenCodePlugin } from "./common/opencode-plugin.js";

export default {
  id: "SwiftScaffolding",
  server: createOpenCodePlugin(new URL(".", import.meta.url)),
};
