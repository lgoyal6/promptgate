// Runs the repository's own parsers, in the browser.
//
// The two regexes are not retyped here: scripts/make_page_data.py lifts them
// out of parse.py and ships them in parser.json, along with what the real
// Python classify() returned for every example. On load this file re-runs those
// examples through the JavaScript copy and compares. If the two ever disagree,
// the page says so rather than quietly showing the wrong answer.

const el = (id) => document.getElementById(id);
const state = { data: null, re: null };

function classify(text) {
  const { verify, feedback, comment } = state.re;
  const v = verify.exec(text || '');
  const strict = v ? v[1].toLowerCase() : null;
  let tolerant = strict;
  let tag = strict ? 'manager_verify' : null;
  if (!strict) {
    const f = feedback.exec(text || '');
    if (f) {
      tolerant = f[1].toLowerCase();
      tag = 'manager_feedback';
    }
  }
  const c = comment.exec(text || '');
  return {
    strict_verdict: strict,
    tolerant_verdict: tolerant,
    tag_used: tag,
    has_comment: c !== null,
    strict_missed: strict === null && tolerant !== null,
    silently_dropped_reject: strict === null && tolerant === 'reject',
  };
}

function render() {
  const text = el('input').value;
  const r = classify(text);

  const show = (id, value) => {
    const node = el(id);
    node.textContent = value === null ? 'no verdict found' : value;
    node.className = value === null ? 'none' : '';
  };
  show('v-strict', r.strict_verdict);
  show('v-tolerant', r.tolerant_verdict === null ? null : `${r.tolerant_verdict}, in <${r.tag_used}>`);
  el('v-comment').textContent = r.has_comment ? 'yes' : 'none';
  el('v-comment').className = r.has_comment ? '' : 'none';

  const gate = el('gate');
  if (r.silently_dropped_reject) {
    gate.className = 'gate slip';
    gate.textContent =
      'The manager rejected this call. A strict parser found no verdict, and a gate that ' +
      'treats no verdict as no objection lets the tool call through.';
  } else if (r.strict_verdict === 'reject') {
    gate.className = 'gate stop';
    gate.textContent = 'Rejected, and the gate can see it. The tool call is blocked.';
  } else if (r.strict_verdict === 'accept') {
    gate.className = 'gate go';
    gate.textContent = 'Accepted. The tool call proceeds, which is what both parsers agree on.';
  } else {
    gate.className = 'gate';
    gate.textContent =
      'No verdict from either parser. The manager said nothing a gate can act on, which ' +
      'looks exactly like the case above.';
  }
}

function selfCheck() {
  const keys = ['strict_verdict', 'tolerant_verdict', 'tag_used', 'silently_dropped_reject'];
  const bad = state.data.examples.filter((ex) => {
    const mine = classify(ex.text);
    return keys.some((k) => mine[k] !== ex[k]);
  });
  const cap = el('cap-check');
  if (bad.length) {
    cap.textContent = `disagrees with the Python parser on ${bad.length} of ${state.data.examples.length}`;
    el('parse-banner').className = 'banner alarm';
    el('parse-banner').textContent =
      'This page and the parser in the repository do not agree. Trust the repository.';
    return false;
  }
  cap.textContent = `agrees with the Python parser on all ${state.data.examples.length} examples`;
  return true;
}

function contract() {
  const rows = state.data.contract;
  const majority = rows
    .map((r) => r.tag)
    .sort(
      (a, b) =>
        rows.filter((r) => r.tag === b).length - rows.filter((r) => r.tag === a).length,
    )[0];
  const head = '<tr><th>line</th><th>tag it names for a reject</th><th></th></tr>';
  const body = rows
    .map((r) => {
      const odd = r.tag !== majority;
      return (
        `<tr class="${odd ? 'odd' : ''}"><td class="num">${r.line}</td>` +
        `<td class="tag">&lt;${r.tag}&gt;</td>` +
        `<td>${odd ? 'the one that disagrees' : ''}</td></tr>`
      );
    })
    .join('');
  el('contract').innerHTML = `<thead>${head}</thead><tbody>${body}</tbody>`;
  const odd = rows.find((r) => r.tag !== majority);
  el('contract-banner').textContent =
    `${rows.length} statements of how to reject, ${rows.length - 1} of them agreeing. ` +
    `The one that does not is line ${odd.line}, the first one a reader meets.`;
}

function picker(node, items, onPick) {
  node.innerHTML = '';
  items.forEach((it, i) => {
    const b = document.createElement('button');
    b.textContent = it.label;
    b.setAttribute('aria-pressed', String(i === 0));
    b.addEventListener('click', () => {
      onPick(it);
      [...node.children].forEach((c) => c.setAttribute('aria-pressed', String(c === b)));
    });
    node.appendChild(b);
  });
}

async function main() {
  const res = await fetch('./data/parser.json');
  if (!res.ok) {
    el('parse-banner').textContent = `Could not load the parser (HTTP ${res.status}).`;
    return;
  }
  state.data = await res.json();
  const p = state.data.patterns;
  state.re = {
    verify: new RegExp(p.verify, 'i'),
    feedback: new RegExp(p.feedback, 'i'),
    comment: new RegExp(p.comment, 'is'),
  };

  contract();
  const ok = selfCheck();

  const examples = state.data.examples;
  picker(el('examples'), examples.map((e) => ({ label: e.label, text: e.text })), (it) => {
    el('input').value = it.text;
    render();
  });
  el('input').value = examples[0].text;
  el('input').addEventListener('input', render);
  render();

  if (ok) {
    el('parse-banner').className = 'banner';
    el('parse-banner').textContent =
      'Both parsers run here, from the regexes in parse.py. Edit the box and the verdicts follow.';
  }
}

main();
