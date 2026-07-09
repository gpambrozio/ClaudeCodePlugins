import { createOpenCodePlugin } from "./common/opencode-plugin.js";

export default {
  id: "PluginBase",
  server: createOpenCodePlugin(new URL(".", import.meta.url)),
};
