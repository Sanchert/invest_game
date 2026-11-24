import { t } from './strings.js';

/** Turns an error description from validation.js into text. */
export const message = (error) => (error ? t(error.key, error.vars) : '');

/** A labelled input that shows its problem (or a hint) right under it. */
export default function Field({ id, label, error, hint, ok, ...input }) {
  const noteId = `${id}-note`;
  const note = error ? message(error) : (ok || hint);
  return (
    <div className={`field ${error ? 'has-error' : ''}`}>
      <label htmlFor={id}>{label}</label>
      <input id={id} aria-invalid={error ? 'true' : undefined}
        aria-describedby={note ? noteId : undefined} {...input} />
      {note && (
        <p id={noteId} aria-live="polite"
          className={error ? 'field-error' : ok ? 'field-ok' : 'field-hint'}>
          {note}
        </p>
      )}
    </div>
  );
}
