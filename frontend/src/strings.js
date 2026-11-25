export { initialLang, setLang, getLang, t } from './i18n.js';
import { useLang } from './lang.jsx';
import { t as tFn } from './i18n.js';

/** Hook that returns the `t` function and subscribes to language changes. */
export function useT() {
  const { lang } = useLang();
  // Force re-render when lang changes by reading it here.
  void lang;
  return tFn;
}
