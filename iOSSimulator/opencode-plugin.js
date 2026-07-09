import { createOpenCodePlugin } from "./common/opencode-plugin.js";

export default {
  id: "iOSSimulator",
  server: createOpenCodePlugin(new URL(".", import.meta.url)),
};
