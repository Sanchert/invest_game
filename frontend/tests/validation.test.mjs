import assert from 'node:assert/strict';
import test from 'node:test';
import { validateGameForm, validateJoin } from '../src/validation.js';

const ok = { turns: '3', minutes: '10', seconds: '0', startups: '5' };

test('a normal game is valid and its length includes the pauses between turns', () => {
  const r = validateGameForm(ok, { turnsAvailable: 3, startupsAvailable: 5 });
  assert.equal(r.valid, true);
  assert.equal(r.turnSeconds, 600);
  assert.equal(r.totalSeconds, 3 * 600 + 2 * 15);
});

test('empty and non-numeric fields are reported', () => {
  assert.equal(validateGameForm({ ...ok, turns: '' }).errors.turns.key, 'errRequired');
  assert.equal(validateGameForm({ ...ok, turns: '2.5' }).errors.turns.key, 'errWhole');
  assert.equal(validateGameForm({ ...ok, turns: '-1' }).errors.turns.key, 'errWhole');
  assert.equal(validateGameForm({ ...ok, minutes: 'abc' }).errors.minutes.key, 'errWhole');
});

test('ranges', () => {
  assert.equal(validateGameForm({ ...ok, turns: '0' }).errors.turns.key, 'errRange');
  assert.equal(validateGameForm({ ...ok, turns: '21' }).errors.turns.key, 'errRange');
  assert.equal(validateGameForm({ ...ok, seconds: '60' }).errors.seconds.key, 'errRange');
  assert.equal(validateGameForm({ ...ok, startups: '13' }).errors.startups.key, 'errRange');
});

test('a turn must last 10 seconds to an hour', () => {
  assert.equal(validateGameForm({ ...ok, minutes: '0', seconds: '9' }).errors.duration.key, 'errTurnShort');
  assert.equal(validateGameForm({ ...ok, minutes: '0', seconds: '10' }).valid, true);
  assert.equal(validateGameForm({ ...ok, minutes: '60', seconds: '1' }).errors.duration.key, 'errTurnLong');
  assert.equal(validateGameForm({ ...ok, minutes: '60', seconds: '0' }).valid, true);
});

test('the library limits what can be asked for', () => {
  const library = { turnsAvailable: 3, startupsAvailable: 5 };
  const turns = validateGameForm({ ...ok, turns: '4' }, library).errors.turns;
  assert.deepEqual(turns, { key: 'errTurnsLibrary', vars: { n: 3 } });
  const startups = validateGameForm({ ...ok, startups: '6' }, library).errors.startups;
  assert.deepEqual(startups, { key: 'errStartupsLibrary', vars: { n: 5 } });
  assert.equal(validateGameForm({ ...ok, turns: '9' }, {}).errors.turns, undefined);
});

test('join: room code, name length and taken names', () => {
  assert.equal(validateJoin({ code: 'abcde', name: 'Team' }).valid, true);
  assert.equal(validateJoin({ code: 'ABCD', name: 'Team' }).errors.code.key, 'errCode');
  assert.equal(validateJoin({ code: 'ABCD0', name: 'Team' }).errors.code.key, 'errCode'); // 0 is never used
  assert.equal(validateJoin({ code: '', name: 'Team' }).errors.code.key, 'errRequired');
  assert.equal(validateJoin({ code: 'ABCDE', name: '   ' }).errors.name.key, 'errRequired');
  assert.equal(validateJoin({ code: 'ABCDE', name: 'x'.repeat(31) }).errors.name.key, 'errName');
  assert.equal(validateJoin({ code: 'ABCDE', name: '  Red   Pandas ' }, { takenNames: ['Red Pandas'] }).errors.name.key, 'errNameTaken');
  assert.equal(validateJoin({ name: 'Team' }, { needCode: false }).valid, true);
});
