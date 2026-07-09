import { createOpenCodePlugin } from "./common/opencode-plugin.js";

export default {
  id: "XcodeBuildTools",
  server: createOpenCodePlugin(new URL(".", import.meta.url)),
};
