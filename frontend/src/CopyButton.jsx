import { useEffect, useRef, useState } from 'react';
import { useT } from './strings.js';

/** Copies text to the clipboard. The modern clipboard API only exists on secure pages
 *  (https or localhost), so on a plain http address in the classroom it falls back to
 *  the older method. */
async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const field = document.createElement('textarea');
    field.value = text;
    field.setAttribute('readonly', '');
    field.style.position = 'fixed';
    field.style.opacity = '0';
    document.body.appendChild(field);
    field.select();
    let ok = false;
    try {
      ok = document.execCommand('copy');
    } catch {
      ok = false;
    }
    document.body.removeChild(field);
    return ok;
  }
}

export default function CopyButton({ text }) {
  const t = useT();
  const [copied, setCopied] = useState(false);
  const timer = useRef();
  useEffect(() => () => clearTimeout(timer.current), []);
  const copy = async () => {
    if (await copyText(text)) {
      setCopied(true);
      clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopied(false), 2000);
    }
  };
  return (
    <button type="button" className="btn ghost copy-btn" onClick={copy}>
      {copied ? t('copied') : t('copy')}
    </button>
  );
}
