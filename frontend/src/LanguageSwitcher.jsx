import { useEffect, useState } from 'react';
import { useLang } from './lang.jsx';
import { setLang, getLang } from './strings.js';
import { useT } from './strings.js';

const LANGUAGES = [
  { code: 'en', label: 'EN' },
  { code: 'ru', label: 'RU' },
];

export default function LanguageSwitcher() {
  const { lang, setLang: setLangCtx } = useLang();
  const t = useT();
  const [current, setCurrent] = useState(getLang());

  useEffect(() => {
    setCurrent(getLang());
  }, [lang]);

  const pick = (code) => {
    setLang(code);
    setLangCtx(code);
  };

  return (
    <div className="lang-switcher" role="group" aria-label={t('language')}>
      {LANGUAGES.map(({ code, label }) => (
        <button
          key={code}
          className={`lang-btn ${current === code ? 'active' : ''}`}
          onClick={() => pick(code)}
          aria-pressed={current === code}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
