/**
 * Shell syntax highlighter using an ohm.js PEG grammar.
 *
 * All whitespace (spaces, tabs, newlines) is emitted as explicit AST nodes so
 * the token list is a lossless representation of the source. The renderer
 * never needs to split strings — newline tokens act as line separators.
 *
 * Returns Token[][] compatible with prism-react-renderer:
 *   Token = { types: string[], content: string }
 *
 * Falls back to null on any parse error — caller should use Prism then.
 *
 * IMPORTANT: All grammar rules are lowercase (lexical rules) so ohm does NOT
 * auto-skip spaces between tokens. Whitespace is always explicit.
 */

import * as ohm from 'ohm-js';

// ---------------------------------------------------------------------------
// Grammar — stored as string array to avoid ${} JS template literal conflicts.
// All rules lowercase = lexical (no implicit space skipping by ohm).
// Whitespace is modelled explicitly:
//   ws       = zero or more spaces/tabs on a single line
//   nl       = newline (one token per physical line break)
//   wsArg    = ws arg       — space(s) + one argument, keeps space with its arg
//   wsFlagOrArg = ws flagOrArg — same for flags-only lines
// ---------------------------------------------------------------------------

/* eslint-disable no-useless-escape */
const GRAMMAR_SOURCE = [
  'ShellCode {',
  '  lines = line (nl line)*',
  '',
  '  line  = ws assignment ws        -- assignment',
  '        | ws flagsContinued ws    -- flagsContinued',
  '        | ws flagsOnly ws         -- flagsOnly',
  '        | ws comment              -- comment',
  '        | ws pipeline ws          -- pipeline',
  '        | ws                      -- blank',
  '',
  '  flagsContinued = flagsOnly ws "\\\\"',
  '  flagsOnly      = firstFlag wsFlagOrArg*',
  '  firstFlag      = flagWithVal | flag',
  '  wsFlagOrArg    = ws flagOrArg',
  '  flagOrArg      = flagWithVal | flag | atom',
  '',
  '  pipeline   = command (ws binaryOp ws command)* (ws trailingOp)?',
  '  trailingOp = "\\\\" | "&"',
  '',
  '  command = cmdName wsArg*',
  '  wsArg   = ws arg',
  '  cmdName = varWithPath    -- varPath',
  '          | atom            -- atom',
  '',
  '  arg = flagWithVal',
  '      | flag',
  '      | string',
  '      | varWithPath',
  '      | cmdSubst',
  '      | url',
  '      | placeholder',
  '      | number',
  '      | keyval',
  '      | path',
  '      | atom',
  '',
  '  keyval     = envname "=" assignVal',
  '  varWithPath = variable pathSuffix    -- withSuffix',
  '              | variable               -- bare',
  '',
  '  assignment  = "export" ws envname "=" assignVal    -- export',
  '              | "export" ws envname                  -- exportBare',
  '              | envname "=" assignVal                -- plain',
  '  assignVal   = assignPart+',
  '  assignPart  = flagWithVal | flag | string | varWithPath | url | placeholder | number | path | atom',
  '  envname     = (letter | "_") (alnum | "_" | ".")*',
  '',
  '  cmdSubst    = "$(" (~")" any)+ ")"',
  '',
  '  atom        = atomChar+',
  '  atomChar    = ~space ~"\\\\" ~"\\"" ~"\'" ~"$" ~"<" ~">" ~"|" ~";" ~"&" any',
  '',
  '  path        = pathStart pathBodyChar*',
  '  pathStart   = "~/" | "./" | "/"',
  '  pathBodyChar = ~space ~nl any',
  '',
  '  pathSuffix  = pathChar+',
  '  pathChar    = ~space ~"\\\\" ~"$" ~nl any',
  '',
  '  flagWithVal  = flagStem "=" flagValSeq',
  '  flagValSeq   = flagValPart (flagValSep flagValPart)*',
  '  flagValSep   = ";" | "="',
  '  flagValPart  = flagValChar*',
  '  flagValChar  = ~space ~nl ~";" ~"=" any',
  '  flagStem    = "-" "-"? letter flagStemRest*',
  '  flagStemRest = ~space ~nl ~"=" any',
  '  flag        = "-" "-"? letter flagRest*',
  '  flagRest    = ~space ~nl any',
  '',
  '  string      = "\\"" dqChar* "\\"" | "\'" sqChar* "\'"',
  '  dqChar      = "\\\\" any    -- escaped',
  '              | ~"\\"" ~"\\n" any  -- safe',
  '  sqChar      = "\\\\" any    -- escaped',
  '              | ~"\'" ~"\\n" any  -- safe',
  '',
  '  variable    = "${" (~"}" any)+ "}"    -- braced',
  '              | "$" (letter | "_") (alnum | "_")*  -- bare',
  '',
  '  url         = ("https://" | "http://") urlChar+',
  '  urlChar     = ~space ~nl any',
  '',
  '  placeholder     = "<" placeholderChar+ ">"',
  '  placeholderChar = letter | digit | "-" | "." | "_"',
  '',
  '  number      = digit+ ("." digit+)? unit?',
  '  unit        = "s" | "m" | "g" | "k" | "M" | "G" | "K" | "b" | "B" | "%"',
  '',
  '  comment     = "#" (~nl any)*',
  '  binaryOp    = "&&" | "||" | ">>" | "2>&1" | "2>" | ">&" | ">" | "<" | "|" | ";" | "\\\\"',
  '',
  '  ws  = (" " | "\\t")*',
  '  nl  = "\\n" | "\\r\\n" | "\\r"',
  '}',
].join('\n');

// ---------------------------------------------------------------------------
// Grammar + semantics (initialised once, lazily)
// ---------------------------------------------------------------------------

let _grammar = null;
let _semantics = null;

function getGrammar() {
  if (!_grammar) _grammar = ohm.grammar(GRAMMAR_SOURCE);
  return _grammar;
}

// tok(type, content) — shorthand
function tok(type, content) { return { type, content }; }

function buildSemantics(grammar) {
  const sem = grammar.createSemantics();

  sem.addOperation('emit', {

    // lines = line (nl line)*
    lines(first, nls, rest) {
      const out = [...first.emit()];
      for (let i = 0; i < nls.children.length; i++) {
        out.push(...nls.children[i].emit());   // newline token
        out.push(...rest.children[i].emit());  // next line
      }
      return out;
    },

    // nl emits an explicit newline token
    nl(_) { return [tok('plain', '\n')]; },

    // line variants — trailing ws is part of the line (emitted as plain)
    line_assignment(_ws1, asgn, _ws2) { return [..._ws1.emit(), ...asgn.emit(), ..._ws2.emit()]; },
    line_flagsContinued(_ws1, fc, _ws2) { return [..._ws1.emit(), ...fc.emit(), ..._ws2.emit()]; },
    line_flagsOnly(_ws1, fl, _ws2)    { return [..._ws1.emit(), ...fl.emit(), ..._ws2.emit()]; },
    line_comment(_ws, c)              { return [..._ws.emit(), ...c.emit()]; },
    line_pipeline(_ws1, pip, _ws2)    { return [..._ws1.emit(), ...pip.emit(), ..._ws2.emit()]; },
    line_blank(ws)                    { return ws.emit(); },

    // flagsContinued = flagsOnly ws "\\"
    flagsContinued(fl, _ws, _bs) {
      return [...fl.emit(), ..._ws.emit(), tok('operator', '\\')];
    },

    // flagsOnly = firstFlag wsFlagOrArg*
    flagsOnly(first, wsFoa) {
      return [...first.emit(), ...wsFoa.emit()];
    },
    firstFlag(n) { return n.emit(); },

    // wsFlagOrArg = ws flagOrArg  — space is part of this node
    wsFlagOrArg(_ws, flagOrArg) {
      return [..._ws.emit(), ...flagOrArg.emit()];
    },
    flagOrArg(n) { return n.emit(); },

    // pipeline = command (ws binaryOp ws command)* (ws trailingOp)?
    pipeline(first, _ws1, ops, _ws2, cmds, _ws3, trailing) {
      const out = [...first.emit()];
      for (let i = 0; i < ops.children.length; i++) {
        out.push(
          ..._ws1.children[i].emit(),
          ...ops.children[i].emit(),
          ..._ws2.children[i].emit(),
          ...cmds.children[i].emit(),
        );
      }
      out.push(..._ws3.emit(), ...trailing.emit());
      return out;
    },
    trailingOp(_) { return [tok('operator', this.sourceString)]; },
    binaryOp(_)   { return [tok('operator', this.sourceString)]; },

    // command = cmdName wsArg*
    command(name, wsArgs) {
      return [
        ...name.emit().map(t =>
          t.type === 'plain' || t.type === 'variable' ? { ...t, type: 'command' } : t
        ),
        ...wsArgs.emit(),
      ];
    },

    // wsArg = ws arg  — space is attached to its argument node
    wsArg(_ws, arg) { return [..._ws.emit(), ...arg.emit()]; },

    cmdName_varPath(vwp) { return vwp.emit(); },
    cmdName_atom(a)      { return a.emit(); },

    arg(n) { return n.emit(); },

    varWithPath_withSuffix(variable, pathSuffix) {
      return [tok('variable', variable.sourceString), tok('path', pathSuffix.sourceString)];
    },
    varWithPath_bare(variable) {
      return [tok('variable', variable.sourceString)];
    },

    assignment_export(_kw, _ws, name, _eq, val) {
      return [tok('command', _kw.sourceString), ..._ws.emit(), tok('plain', name.sourceString), tok('operator', '='), ...val.emit()];
    },
    assignment_exportBare(_kw, _ws, name) {
      return [tok('command', _kw.sourceString), ..._ws.emit(), tok('plain', name.sourceString)];
    },
    assignment_plain(name, _eq, val) {
      return [tok('plain', name.sourceString), tok('operator', '='), ...val.emit()];
    },

    assignVal(parts)  { return parts.emit(); },
    assignPart(n)     { return n.emit(); },

    keyval(name, _eq, val) {
      return [tok('plain', name.sourceString), tok('operator', '='), ...val.emit()];
    },

    cmdSubst(_open, _inner, _close) { return [tok('plain', this.sourceString)]; },

    atom(_chars)      { return [tok('plain',    this.sourceString)]; },
    atomChar(_)       { return []; },

    path(_start, _body) { return [tok('path', this.sourceString)]; },
    pathStart(_)        { return []; },
    pathBodyChar(_)     { return []; },

    pathSuffix(_)     { return [tok('path',    this.sourceString)]; },
    pathChar(_)       { return []; },

    flagWithVal(_stem, _eq, seq) {
      return [tok('flag', _stem.sourceString), tok('operator', '='), ...seq.emit()];
    },
    flagValSeq(first, seps, rest) {
      const out = [...first.emit()];
      for (let i = 0; i < seps.children.length; i++) {
        out.push(...seps.children[i].emit(), ...rest.children[i].emit());
      }
      return out;
    },
    flagValSep(_)    { return [tok('operator', this.sourceString)]; },
    flagValPart(_)   {
      const s = this.sourceString;
      if (!s) return [];
      if (/^[~./]/.test(s)) return [tok('path', s)];
      if (/^\d/.test(s)) return [tok('number', s)];
      return [tok('plain', s)];
    },
    flagValChar(_)   { return []; },
    flagStem(_d1, _d2, _l, _rest) { return []; },
    flagStemRest(_)  { return []; },

    flag(_d1, _d2, _l, _rest) { return [tok('flag', this.sourceString)]; },
    flagRest(_)       { return []; },

    string(_open, _chars, _close) { return [tok('string', this.sourceString)]; },
    dqChar_escaped(_bs, _ch) { return []; },
    dqChar_safe(_ch)          { return []; },
    sqChar_escaped(_bs, _ch) { return []; },
    sqChar_safe(_ch)          { return []; },

    variable_braced(_open, _inner, _close) { return [tok('variable', this.sourceString)]; },
    variable_bare(_dollar, _first, _rest)  { return [tok('variable', this.sourceString)]; },

    url(_scheme, _rest) { return [tok('url', this.sourceString)]; },
    urlChar(_)          { return []; },

    placeholder(_lt, _chars, _gt) { return [tok('placeholder', this.sourceString)]; },
    placeholderChar(_) { return []; },

    number(_int, _dot, _frac, _unit) { return [tok('number', this.sourceString)]; },
    unit(_) { return []; },

    comment(_hash, _rest) { return [tok('comment', this.sourceString)]; },

    envname(_first, _rest) { return []; },

    // ws emits spaces/tabs as a single plain token (or nothing if empty)
    ws(chars) {
      const s = this.sourceString;
      return s ? [tok('plain', s)] : [];
    },

    _iter(...children) { return children.flatMap(c => c.emit()); },
    _terminal()        { return []; },
  });

  return sem;
}

// ---------------------------------------------------------------------------
// Flat token list → Token[][] (one array per physical line)
// Newline tokens act as line separators — no string splitting needed.
// ---------------------------------------------------------------------------

function splitIntoLines(flatTokens) {
  const lines = [[]];
  for (const tok of flatTokens) {
    if (tok.content === '\n') {
      lines.push([]);
    } else {
      lines[lines.length - 1].push({ types: [tok.type], content: tok.content });
    }
  }
  return lines;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Highlight shell/bash code using the ohm.js PEG grammar.
 * @param {string} code
 * @returns {Array<Array<{types: string[], content: string}>>|null}  null on parse failure
 */
export function highlightShell(code) {
  try {
    const grammar = getGrammar();
    if (!_semantics) _semantics = buildSemantics(grammar);
    const result = grammar.match(code, 'lines');
    if (result.failed()) return null;
    const flat = _semantics(result).emit();
    return splitIntoLines(flat);
  } catch (_) {
    return null;
  }
}
