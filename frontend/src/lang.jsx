import { createContext, useContext, useEffect, useState } from 'react';
import { setLang as setLangGlobal, initialLang } from './i18n.js';

const LangContext = createContext();

const LANG_KEY = 'game_lang';

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(initialLang);

  useEffect(() => {
    try { sessionStorage.setItem(LANG_KEY, lang); } catch {}
    setLangGlobal(lang);
  }, [lang]);

  return (
    <LangContext.Provider value={{ lang, setLang: setLangState }}>
      {children}
    </LangContext.Provider>
  );
}

export function useLang() {
  return useContext(LangContext);
}
