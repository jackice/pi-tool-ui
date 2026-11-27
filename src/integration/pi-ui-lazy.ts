import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const cache = new Map<string, unknown>();

export function loadPiUi<T>(specifier: string): T {
  const cached = cache.get(specifier);
  if (cached !== undefined) return cached as T;
  const loaded = require(specifier) as T;
  cache.set(specifier, loaded);
  return loaded;
}
