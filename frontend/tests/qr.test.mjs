// Run with:  node --test tests/
// qr.golden.json holds matrices that were read back by a QR scanner (OpenCV) when they
// were generated, so a change to the encoder that breaks scanning fails here.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { encodeQr } from '../src/qr.js';

const golden = JSON.parse(readFileSync(new URL('./qr.golden.json', import.meta.url), 'utf8'));
const asRows = (matrix) => matrix.map((row) => row.map((v) => (v ? '1' : '0')).join(''));

for (const { text, ecc, rows } of golden) {
  test(`matches the scanned reference: ${ecc} ${text.slice(0, 24)}`, () => {
    assert.deepEqual(asRows(encodeQr(text, ecc)), rows);
  });
}

test('size follows the version (21 modules for version 1, +4 per version)', () => {
  assert.equal(encodeQr('HELLO', 'M').length, 21);
  assert.equal((encodeQr('http://192.168.137.1:8080/play/ABCDE', 'M').length - 17) % 4, 0);
});

test('the three finder patterns are in place', () => {
  const m = encodeQr('http://10.0.0.5:8080/play/K7M2X', 'M');
  const n = m.length;
  for (const [x, y] of [[0, 0], [n - 7, 0], [0, n - 7]]) {
    assert.ok(m[y][x] && m[y + 6][x + 6] && m[y][x + 6] && m[y + 6][x], 'outer ring corners');
    assert.ok(!m[y + 1][x + 1] && !m[y + 5][x + 5], 'light ring');
    assert.ok(m[y + 3][x + 3], 'dark centre');
  }
});

test('is deterministic', () => {
  assert.deepEqual(encodeQr('same text'), encodeQr('same text'));
});

test('lower error correction fits more text in a smaller code', () => {
  const text = 'x'.repeat(40);
  assert.ok(encodeQr(text, 'L').length <= encodeQr(text, 'M').length);
});

test('refuses text that does not fit', () => {
  assert.throws(() => encodeQr('x'.repeat(400)), /too long/);
  assert.throws(() => encodeQr('x', 'Q'), /ecc/);
});
