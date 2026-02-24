import { describe, it, expect } from 'vitest';
import { stripThink, pruneHistory, buildApiHistory } from '../src/utils.js';

describe('stripThink', () => {
  it('strips think blocks and returns remaining content', () => {
    expect(stripThink('<think>reasoning</think>The answer is 42.'))
      .toBe('The answer is 42.');
  });

  it('strips multiple think blocks', () => {
    expect(stripThink('<think>a</think>Hello <think>b</think>world'))
      .toBe('Hello world');
  });

  it('returns (continued) when only think blocks remain', () => {
    expect(stripThink('<think>just reasoning here</think>'))
      .toBe('(continued)');
  });

  it('returns (continued) for think block with only whitespace after', () => {
    expect(stripThink('<think>reasoning</think>   \n  '))
      .toBe('(continued)');
  });

  it('returns content unchanged when no think blocks', () => {
    expect(stripThink('plain answer')).toBe('plain answer');
  });

  it('handles multiline think blocks', () => {
    const input = '<think>\nline 1\nline 2\nline 3\n</think>\nFinal answer.';
    expect(stripThink(input)).toBe('Final answer.');
  });
});

describe('pruneHistory', () => {
  function msg(role, content) {
    return { role, content };
  }

  it('does nothing for short conversations', () => {
    const msgs = [
      msg('user', 'hello'),
      msg('assistant', 'hi'),
    ];
    pruneHistory(msgs);
    expect(msgs).toHaveLength(2);
    expect(msgs[0].content).toBe('hello');
  });

  it('strips think blocks from older messages but keeps recent 2', () => {
    const msgs = [
      msg('user', 'q1'),
      msg('assistant', '<think>old reasoning</think>answer 1'),
      msg('user', 'q2'),
      msg('assistant', '<think>recent reasoning</think>answer 2'),  // second to last
      msg('user', 'q3'),  // last
    ];
    pruneHistory(msgs);
    // Older assistant (index 1) should have think block stripped
    expect(msgs[1].content).toBe('answer 1');
    // Recent assistant (index 3) should keep think block
    expect(msgs[3].content).toContain('<think>');
  });

  it('replaces think-only older messages with (continued)', () => {
    const msgs = [
      msg('user', 'q1'),
      msg('assistant', '<think>only reasoning, no visible answer</think>'),
      msg('user', 'q2'),
      msg('assistant', 'visible answer'),
      msg('user', 'q3'),
    ];
    pruneHistory(msgs);
    expect(msgs[1].content).toBe('(continued)');
  });

  it('truncates long older messages', () => {
    const longContent = 'x'.repeat(5000);
    const msgs = [
      msg('user', 'q1'),
      msg('assistant', longContent),
      msg('user', 'q2'),
      msg('assistant', 'short'),
      msg('user', 'q3'),
    ];
    pruneHistory(msgs, { maxMsgChars: 3000 });
    expect(msgs[1].content.length).toBeLessThanOrEqual(3020); // 3000 + truncation marker
    expect(msgs[1].content).toContain('...(truncated)');
  });

  it('does not truncate the last 2 messages', () => {
    const longContent = 'x'.repeat(5000);
    const msgs = [
      msg('user', 'q1'),
      msg('assistant', 'short'),
      msg('user', longContent),  // second to last
      msg('assistant', longContent),  // last
    ];
    pruneHistory(msgs, { maxMsgChars: 3000 });
    expect(msgs[2].content).toBe(longContent);
    expect(msgs[3].content).toBe(longContent);
  });

  it('drops middle messages when over budget', () => {
    const big = 'x'.repeat(1000);
    const msgs = [
      msg('user', 'first'),       // kept (first)
      msg('assistant', big),      // middle — dropped
      msg('user', big),           // middle — dropped
      msg('assistant', big),      // middle — dropped
      msg('user', big),           // middle — dropped
      msg('assistant', big),      // recent (MIN_RECENT=4)
      msg('user', big),           // recent
      msg('assistant', big),      // recent
      msg('user', 'last'),        // recent
    ];
    pruneHistory(msgs, { maxChars: 3000, minRecent: 4 });
    // First message should be kept
    expect(msgs[0].content).toBe('first');
    // Last message should be kept
    expect(msgs[msgs.length - 1].content).toBe('last');
  });

  it('inserts pruned marker when all middle messages are dropped', () => {
    const big = 'x'.repeat(2000);
    const msgs = [
      msg('user', 'first'),
      msg('assistant', big),
      msg('user', big),
      msg('assistant', big),
      msg('user', big),
      msg('assistant', big),
      msg('user', big),
      msg('assistant', 'a7'),
      msg('user', 'last'),
    ];
    pruneHistory(msgs, { maxChars: 500, minRecent: 2 });
    const systemMsg = msgs.find(m => m.role === 'system');
    expect(systemMsg).toBeDefined();
    expect(systemMsg.content).toBe('[earlier messages pruned]');
  });

  it('budget ignores think blocks in recent messages', () => {
    // Big think block in recent message should NOT trigger pruning
    const bigThink = '<think>' + 'x'.repeat(5000) + '</think>short answer';
    const msgs = [
      msg('user', 'first'),
      msg('assistant', 'middle answer'),
      msg('user', 'q2'),
      msg('assistant', 'another middle'),
      msg('user', 'q3'),
      msg('assistant', bigThink),  // recent — huge think block
      msg('user', 'last'),
    ];
    const before = msgs.length;
    pruneHistory(msgs, { maxChars: 1000, minRecent: 4 });
    // The big think block has only ~12 chars of API content ("short answer")
    // so middle messages should be preserved
    expect(msgs.some(m => m.content === 'middle answer')).toBe(true);
  });
});

describe('buildApiHistory', () => {
  function msg(role, content) {
    return { role, content };
  }

  it('strips think blocks from assistant messages', () => {
    const msgs = [
      msg('user', 'hello'),
      msg('assistant', '<think>reasoning</think>The answer.'),
    ];
    const history = buildApiHistory(msgs);
    expect(history[1].content).toBe('The answer.');
  });

  it('preserves user messages unchanged', () => {
    const msgs = [
      msg('user', 'hello <think>not a real tag</think>'),
      msg('assistant', 'response'),
    ];
    const history = buildApiHistory(msgs);
    expect(history[0].content).toBe('hello <think>not a real tag</think>');
  });

  it('replaces think-only assistant messages with (continued)', () => {
    const msgs = [
      msg('user', 'q1'),
      msg('assistant', '<think>only reasoning</think>'),
      msg('user', 'q2'),
      msg('assistant', 'visible answer'),
    ];
    const history = buildApiHistory(msgs);
    expect(history).toHaveLength(4);
    expect(history[1].content).toBe('(continued)');
    expect(history[3].content).toBe('visible answer');
  });

  it('filters out empty messages', () => {
    const msgs = [
      msg('user', 'hello'),
      msg('assistant', ''),
      msg('user', 'world'),
    ];
    const history = buildApiHistory(msgs);
    expect(history).toHaveLength(2);
    expect(history[0].content).toBe('hello');
    expect(history[1].content).toBe('world');
  });

  it('preserves all turns across mode switches', () => {
    // Simulate: reason mode response, then normal mode follow-up
    const msgs = [
      msg('user', 'explain quantum computing'),
      msg('assistant', '<think>deep reasoning about qubits</think>Quantum computing uses qubits.'),
      msg('user', 'simplify that'),
      msg('assistant', 'Its like a coin that can be heads and tails at the same time.'),
    ];
    const history = buildApiHistory(msgs);
    expect(history).toHaveLength(4);
    expect(history[1].content).toBe('Quantum computing uses qubits.');
    expect(history[3].content).toBe('Its like a coin that can be heads and tails at the same time.');
  });

  it('handles the original bug: think-only R1 response then normal follow-up', () => {
    // This was the exact bug — R1 response with only think block would be dropped
    const msgs = [
      msg('user', 'reason about X'),
      msg('assistant', '<think>long reasoning about X with no visible content</think>'),
      msg('user', 'now tell me about Y based on that'),
      msg('assistant', 'Y is related to X because...'),
    ];
    const history = buildApiHistory(msgs);
    // All 4 turns must be present — the think-only one should be (continued)
    expect(history).toHaveLength(4);
    expect(history[1].content).toBe('(continued)');
  });
});
