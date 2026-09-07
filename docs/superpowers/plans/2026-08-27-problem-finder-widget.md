# Problem Finder Decision Tree Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "What problem are you trying to solve?" decision tree widget to the top of the jvm-tools page that guides visitors to the right tool in 2–3 clicks, open by default, driven entirely by a single YAML data file.

**Architecture:** A flat node map in `data/jvm-tools/problem-finder.yaml` defines every question and result. A Hugo partial (`layouts/partials/problem-finder.html`) reads this YAML at build time, builds a tool-metadata lookup from all section static.yaml files, and renders every node into the DOM. Alpine.js tracks only `cur` (current node ID) and `hist` (back-stack) — `x-show` on each node does the rest. Adding or changing a path requires editing only the YAML file.

**Tech Stack:** Hugo (Go templates, `index .Site.Data`, `range`, `dict`), Alpine.js v3 (`x-data`, `x-show`, `x-cloak`, `@click`), Tailwind CSS v3 (existing utility classes only — no new CSS)

---

## File Map

| File | Status | Responsibility |
|---|---|---|
| `data/jvm-tools/problem-finder.yaml` | **Create** | Entire tree: all question nodes, all result nodes, tool IDs, notes, follow-ons |
| `themes/projects-theme/layouts/partials/problem-finder.html` | **Create** | Hugo partial: build tool lookup, render all nodes, Alpine state |
| `themes/projects-theme/layouts/collection/list.html` | **Modify** (2 lines) | Include the partial after page header, guarded to jvm-tools only |

No changes to `main.js`, `main.css`, `config.yaml`, or any `static.yaml`.

---

## Task 1: Create the YAML tree data file

**Files:**
- Create: `data/jvm-tools/problem-finder.yaml`

- [ ] **Step 1: Create the file with the full tree**

Create `/Users/i560383_1/code/experiments/parttimenerd.github.io/data/jvm-tools/problem-finder.yaml` with this exact content:

```yaml
# Decision tree for the "Have a problem?" widget on /jvm-tools/
# Each key is a node ID. Two types: question (shows options) and result (shows tools).
# To add a tool: add a result node and wire an option in the relevant question to it.
# Start node is always "start".

start:
  type: question
  text: "What problem are you trying to solve?"
  options:
    - label: "My app is slow or unresponsive — I need to find out why"
      next: q-slow
    - label: "My JVM crashed, froze, or is behaving strangely"
      next: q-crash
    - label: "I want to dig into a JFR recording or set up continuous profiling"
      next: q-jfr
    - label: "I have a heap dump to analyse or share"
      next: q-heap
    - label: "I want to speed up my build, tests, or JAR packaging"
      next: q-build
    - label: "I want to learn how JVM profiling works from the inside"
      next: r-learn

q-slow:
  type: question
  text: "How do you want to investigate?"
  options:
    - label: "It's happening right now — I need answers in seconds"
      next: q-slow-env
    - label: "I have a JFR recording and want to see a flame graph"
      next: r-jfr-visual
    - label: "I want to query JFR data with SQL and see GC/allocation charts"
      next: r-jfr-query
    - label: "I want to record continuously for days without filling the disk"
      next: r-condensed

q-slow-env:
  type: question
  text: "Where is the JVM running?"
  options:
    - label: "On Cloud Foundry — I can't SSH into the container"
      next: r-cf
    - label: "Anywhere else (local, staging, production server)"
      next: r-jstall

q-crash:
  type: question
  text: "What do you have in hand?"
  options:
    - label: "A crash file (hs_err_pid…)"
      next: r-jhserr
    - label: "A thread dump from jstack or jcmd"
      next: r-jthreaddump
    - label: "A heap dump (OutOfMemoryError or manual capture)"
      next: r-hprof-analyze
    - label: "A deadlock or race condition that's hard to reproduce"
      next: r-deadlock
    - label: "Something unexplained — I suspect a Java agent is involved"
      next: r-meta-agent
    - label: "Confusing -Xlog output — I don't know what flags to use"
      next: r-jdklogs

q-jfr:
  type: question
  text: "What do you want to do with it?"
  options:
    - label: "View it as a flame graph or share it with my team"
      next: r-jfr-visual
    - label: "Query it with SQL — GC pauses, allocations, CPU correlation"
      next: r-jfr-query
    - label: "Record continuously for days or weeks with minimal disk use"
      next: r-condensed
    - label: "Look up what JFR events exist and what fields they have"
      next: r-jfrevents

q-heap:
  type: question
  text: "What do you need to do?"
  options:
    - label: "Analyse it — find leak suspects and top memory consumers"
      next: r-hprof-analyze
    - label: "Redact sensitive strings before sharing with my team or support"
      next: r-hprof-redact
    - label: "Both — redact it, then analyse the sanitised file"
      next: r-hprof-both

q-build:
  type: question
  text: "What's the bottleneck?"
  options:
    - label: "Tests take ages and failures only appear at the end of the run"
      next: r-test-order
    - label: "I want to ship a single executable file without java -jar"
      next: r-execjar
    - label: "A Java agent is causing problems, or I'm building one"
      next: r-meta-agent

# ── Result nodes ──────────────────────────────────────────────────────────────

r-jstall:
  type: result
  headline: "You need instant insight into a running JVM."
  tools:
    - id: jstall
      note: "Also available as an IntelliJ plugin (JetBrains marketplace) and VS Code extension."
  followon:
    heading: "Want to keep monitoring this JVM over time?"
    tools:
      - id: condensed-data
        note: "Attach to the JVM and store JFR events compactly for days or weeks."
      - id: jfr-query
        note: "Query the recordings with SQL — GC pauses, allocations, CPU."
  related:
    - label: "Race condition that only appears sometimes?"
      tools:
        - id: concurrency-fuzz-scheduler
          section: experiments
          note: "eBPF scheduler that forces unusual thread interleavings to surface races."
        - id: taskcontrol
          section: experiments
          note: "Deterministic thread interleaving control in tests."

r-cf:
  type: result
  headline: "You need JVM inspection inside a Cloud Foundry container without SSH."
  tools:
    - id: cf-cli-java-plugin
      note: "Bundles jstall internally — you get jstall-style inspection from the CF CLI."
  followon:
    heading: "Want to keep monitoring this JVM over time?"
    tools:
      - id: condensed-data
        note: "Attach and store JFR events compactly for days or weeks."
      - id: jfr-query
        note: "Query the recordings with SQL."

r-jfr-visual:
  type: result
  headline: "You want to explore your JFR recording as a flame graph."
  tools:
    - id: jfr-profiling
      note: "Converts JFR to Firefox Profiler format; includes an IntelliJ plugin for in-IDE profiling."
    - id: firefox-profiler
      note: "Standalone hosted web app — open .jfr or .cjfr files natively in the browser, no install."

r-jfr-query:
  type: result
  headline: "You want to query JFR data with SQL and visualise GC, allocations, and CPU."
  tools:
    - id: jfr-query
      note: "DuckDB-powered notebook with built-in GC pause, allocation, and CPU views. Works on .jfr and .cjfr files."
  followon:
    heading: "Need multi-day recordings to feed into it?"
    tools:
      - id: condensed-data
        note: "Attach to a running JVM and store events compactly — jfr-query reads the .cjfr files directly."

r-condensed:
  type: result
  headline: "You need continuous JFR recording that won't fill your disk."
  tools:
    - id: condensed-data
      note: "Live-attach to a running JVM; stores events in the compact .cjfr format, significantly smaller than raw JFR."
  followon:
    heading: "Once you have recordings, analyse them with:"
    tools:
      - id: jfr-query
        note: "SQL notebook — GC pauses, allocations, CPU correlation, built-in views."
      - id: firefox-profiler
        note: "Visual flame graph viewer — also opens .cjfr files natively in the browser."

r-jfrevents:
  type: result
  headline: "You need a reference for JFR event types and their fields."
  tools:
    - id: jfrevents
      note: "Lists every JFR event across JDK versions with field names, types, and benchmark-derived examples."

r-jhserr:
  type: result
  headline: "You need to parse or redact a JVM crash file."
  tools:
    - id: jhserr
      note: "Parses hs_err_pid files into a typed Java model. Also available as a web UI for one-off redaction."

r-jthreaddump:
  type: result
  headline: "You need to parse or diff a thread dump programmatically."
  tools:
    - id: jthreaddump
      note: "Handles all JDK thread dump formats including virtual threads."
  related:
    - label: "Need to inspect threads live instead?"
      tools:
        - id: jstall
          note: "Live TUI, deadlock detection, and hot thread analysis without a persistent agent."

r-hprof-analyze:
  type: result
  headline: "You need to find what's consuming memory or leaking."
  tools:
    - id: hprof-analyzer
      note: "Handles >10 GiB dumps that Eclipse MAT can't open. Also a web WASM tool for dumps up to ~3 GiB."
  related:
    - label: "Dump contains sensitive data you need to redact first?"
      tools:
        - id: hprof-redact
          note: "Stream-redacts strings without loading the full file into memory."

r-hprof-redact:
  type: result
  headline: "You need to redact sensitive strings from a heap dump before sharing."
  tools:
    - id: hprof-redact
      note: "Stream-based — handles large dumps without loading them fully into memory. Preserves HPROF structure."
  related:
    - label: "Want to analyse the redacted dump afterwards?"
      tools:
        - id: hprof-analyzer
          note: "Fast Rust-based analyser — handles very large dumps that Eclipse MAT can't open."

r-hprof-both:
  type: result
  headline: "Redact first, then analyse."
  tools:
    - id: hprof-redact
      note: "Step 1 — stream-redact sensitive strings while preserving the HPROF structure."
    - id: hprof-analyzer
      note: "Step 2 — analyse the sanitised dump for leak suspects and top consumers."

r-deadlock:
  type: result
  headline: "You have a deadlock or race condition that's hard to reproduce."
  tools:
    - id: jstall
      note: "Start here — live deadlock detection and hot thread analysis in seconds."
  followon:
    heading: "If the race only appears under specific thread interleavings:"
    tools:
      - id: concurrency-fuzz-scheduler
        section: experiments
        note: "eBPF scheduler that deliberately perturbs thread scheduling to force races to the surface."
      - id: taskcontrol
        section: experiments
        note: "Java API for deterministic thread interleaving control in tests."

r-meta-agent:
  type: result
  headline: "You need to see exactly what a Java agent is doing to your classes."
  tools:
    - id: meta-agent
      note: "Wraps any agent and intercepts its ClassFileTransformer — shows which classes are transformed, bytecode before/after, and timing."

r-jdklogs:
  type: result
  headline: "You want to understand what a -Xlog config will actually produce."
  tools:
    - id: jdklogs
      note: "Interactive browser tool — enter your -Xlog config and see exactly which log statements match, with source context."

r-test-order:
  type: result
  headline: "You want failing tests to surface earlier in your CI run."
  tools:
    - id: test-order
      note: "Zero-config Maven/Gradle plugin — reorders the suite so tests covering recently changed code run first."

r-execjar:
  type: result
  headline: "You want users to run your JAR as a plain command."
  tools:
    - id: execjar
      note: "Wraps the fat JAR in a shell stub — a single directly executable file, no launcher script."
  related:
    - label: "Want to shrink the JAR first?"
      tools:
        - id: femtojar
          section: femto
          note: "Cross-class compression + optional ProGuard integration. Combine: shrink with femtojar, then wrap with execjar."

r-learn:
  type: result
  headline: "You want to understand how JVM profilers work from the inside out."
  tools:
    - id: writing-a-profiler
      note: "Step-by-step blog series with code — from a basic safepoint-biased sampler to AsyncGetCallTrace."
    - id: tiny-profiler
      note: "A minimal working profiler readable in an afternoon. Companion to the blog series."
```

- [ ] **Step 2: Verify Hugo can parse it**

```bash
cd /Users/i560383_1/code/experiments/parttimenerd.github.io
hugo --quiet 2>&1 | head -20
```

Expected: no errors, build completes. If you see "unmarshal" errors, check YAML indentation — every list item under `tools:` must be consistently indented.

- [ ] **Step 3: Commit**

```bash
cd /Users/i560383_1/code/experiments/parttimenerd.github.io
git add data/jvm-tools/problem-finder.yaml
git commit -m "feat: add problem-finder decision tree data"
```

---

## Task 2: Create the Hugo partial

**Files:**
- Create: `themes/projects-theme/layouts/partials/problem-finder.html`

This partial:
1. Builds a `$toolMeta` lookup map from all three section static.yaml files
2. Reads the tree from `site.Data.jvm-tools.problem-finder`
3. Renders the Alpine wrapper with `hidden` + `cur` + `hist` state
4. Renders every node into the DOM (hidden by default via `x-show`)
5. Question nodes render option buttons; result nodes render tool cards + callouts

- [ ] **Step 1: Create the partials directory and file**

```bash
mkdir -p /Users/i560383_1/code/experiments/parttimenerd.github.io/themes/projects-theme/layouts/partials
```

- [ ] **Step 2: Create the partial with full content**

Create `themes/projects-theme/layouts/partials/problem-finder.html` with:

```html
{{/* ─────────────────────────────────────────────────────────────────────────
     problem-finder.html
     Decision tree widget for /jvm-tools/. Data lives entirely in
     data/jvm-tools/problem-finder.yaml — edit that file to add/change paths.
     ───────────────────────────────────────────────────────────────────────── */}}

{{/* Build a flat tool-metadata lookup map across all three sections.
     Keys are tool IDs; values are the static.yaml entry objects.
     This lets result nodes reference tools from femto/ and experiments/ too. */}}
{{ $toolMeta := dict }}
{{ range site.Data.jvm_tools.static }}
  {{ $toolMeta = merge $toolMeta (dict .id .) }}
{{ end }}
{{ range site.Data.femto.static }}
  {{ $toolMeta = merge $toolMeta (dict .id .) }}
{{ end }}
{{ range site.Data.experiments.static }}
  {{ $toolMeta = merge $toolMeta (dict .id .) }}
{{ end }}

{{ $tree := site.Data.jvm_tools.problem_finder }}

<div
  x-data="{
    hidden: false,
    cur: 'start',
    hist: [],
    labels: {},
    go(id, label) {
      this.hist.push({ id: this.cur, label: label });
      this.cur = id;
    },
    back() {
      if (this.hist.length) {
        const prev = this.hist.pop();
        this.cur = prev.id;
      }
    },
    reset() { this.cur = 'start'; this.hist = []; }
  }"
  x-cloak
  x-show="!hidden"
  class="border border-gray-200 rounded-xl p-5 mb-6 bg-white"
>

  {{/* Header row: title + hide button */}}
  <div class="flex items-center justify-between mb-4">
    <p class="text-sm font-semibold text-gray-700">Not sure which tool you need? Answer a few questions.</p>
    <button
      @click="hidden = true"
      class="text-xs text-gray-400 hover:text-gray-600 transition-colors ml-4 shrink-0"
    >Hide ✕</button>
  </div>

  {{/* Breadcrumb: shows selected path, back + reset buttons */}}
  <div x-show="hist.length > 0" class="flex flex-wrap gap-x-3 gap-y-1 items-center mb-4 text-xs text-gray-400">
    <button @click="reset()" class="hover:text-blue-600 transition-colors">Start over</button>
    <span>·</span>
    <template x-for="(crumb, i) in hist" :key="i">
      <span class="flex items-center gap-1">
        <span x-text="crumb.label" class="max-w-[16rem] truncate"></span>
        <span x-show="i < hist.length - 1" class="text-gray-300">›</span>
      </span>
    </template>
    <span>·</span>
    <button @click="back()" class="hover:text-blue-600 transition-colors">← Back</button>
  </div>

  {{/* Render every tree node; Alpine shows only the current one */}}
  {{ range $nodeId, $node := $tree }}
  <div x-show="cur === '{{ $nodeId }}'" x-cloak>

    {{ if eq $node.type "question" }}
    {{/* ── Question node ───────────────────────────────────────────────── */}}
    <p class="text-base font-semibold text-gray-900 mb-3">{{ $node.text }}</p>
    <div class="flex flex-col gap-2">
      {{ range $node.options }}
      {{ $label := .label }}
      {{ $next  := .next }}
      <button
        @click="go('{{ $next }}', '{{ $label | htmlEscape }}')"
        class="w-full text-left border border-gray-200 rounded-lg px-4 py-3 text-sm text-gray-700 hover:border-blue-400 hover:bg-blue-50 transition-all cursor-pointer"
      >{{ $label }}</button>
      {{ end }}
    </div>

    {{ else if eq $node.type "result" }}
    {{/* ── Result node ─────────────────────────────────────────────────── */}}
    <p class="text-sm font-semibold text-gray-900 mb-4">{{ $node.headline }}</p>

    {{/* Primary tool cards */}}
    <div class="flex flex-col gap-3 mb-4">
      {{ range $node.tools }}
      {{ $meta    := index $toolMeta .id }}
      {{ $section := .section | default "jvm-tools" }}
      {{ $href    := printf "#%s" .id }}
      {{ if ne $section "jvm-tools" }}{{ $href = printf "/%s/#%s" $section .id }}{{ end }}
      {{ $extLink := $meta.github_pages | default $meta.github_url | default (printf "https://github.com/parttimenerd/%s" .id) }}
      <div class="project-card">
        <div class="flex items-start justify-between gap-2">
          <div class="flex flex-wrap items-baseline gap-x-2 gap-y-1 min-w-0">
            <span class="font-semibold text-gray-900">{{ .id }}</span>
            {{ with $meta.tag }}<span class="badge badge-{{ . }}">{{ . }}</span>{{ end }}
          </div>
          <a href="{{ $extLink }}" target="_blank" rel="noopener"
             class="text-gray-300 hover:text-blue-500 transition-colors shrink-0 mt-0.5"
             title="Open project page">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
            </svg>
          </a>
        </div>
        {{ with $meta.tagline_short }}<p class="text-sm text-gray-600 mt-1">{{ . }}</p>{{ end }}
        {{ with .note }}<p class="text-xs text-gray-500 mt-1">{{ . }}</p>{{ end }}
        <a href="{{ $href }}" class="text-xs text-blue-600 hover:underline mt-2 inline-block">Go to tool ↓</a>
      </div>
      {{ end }}
    </div>

    {{/* Follow-on callout (blue) */}}
    {{ with $node.followon }}
    <div class="bg-blue-50 border border-blue-100 rounded-lg p-3 mt-2 mb-3">
      <p class="text-xs font-semibold text-blue-800 mb-2">{{ .heading }}</p>
      <div class="flex flex-col gap-2">
        {{ range .tools }}
        {{ $fMeta    := index $toolMeta .id }}
        {{ $fSection := .section | default "jvm-tools" }}
        {{ $fHref    := printf "#%s" .id }}
        {{ if ne $fSection "jvm-tools" }}{{ $fHref = printf "/%s/#%s" $fSection .id }}{{ end }}
        <div class="flex items-start gap-2">
          <div class="min-w-0">
            <a href="{{ $fHref }}" class="text-xs font-semibold text-blue-700 hover:underline">{{ .id }}</a>
            {{ with .note }}<span class="text-xs text-blue-700"> — {{ . }}</span>{{ end }}
          </div>
        </div>
        {{ end }}
      </div>
    </div>
    {{ end }}

    {{/* Related callouts (amber) */}}
    {{ range $node.related }}
    <div class="bg-amber-50 border border-amber-100 rounded-lg p-3 mt-2">
      <p class="text-xs font-semibold text-amber-800 mb-2">{{ .label }}</p>
      <div class="flex flex-col gap-2">
        {{ range .tools }}
        {{ $rSection := .section | default "jvm-tools" }}
        {{ $rHref    := printf "#%s" .id }}
        {{ if ne $rSection "jvm-tools" }}{{ $rHref = printf "/%s/#%s" $rSection .id }}{{ end }}
        <div>
          <a href="{{ $rHref }}" class="text-xs font-semibold text-amber-700 hover:underline">{{ .id }}</a>
          {{ with .note }}<span class="text-xs text-amber-700"> — {{ . }}</span>{{ end }}
        </div>
        {{ end }}
      </div>
    </div>
    {{ end }}

    {{/* Start over link at bottom of result */}}
    <button @click="reset()" class="mt-4 text-xs text-gray-400 hover:text-blue-600 transition-colors">
      ← Start over
    </button>

    {{ end }}{{/* end result node */}}
  </div>
  {{ end }}{{/* end range $tree */}}

</div>

{{/* Collapsed state: shown when hidden=true */}}
<div x-show="hidden" x-cloak class="mb-6">
  <button
    @click="hidden = false"
    class="text-sm text-blue-600 hover:underline"
  >Not sure which tool you need? Show guide ▸</button>
</div>
```

- [ ] **Step 3: Verify Hugo builds without errors**

```bash
cd /Users/i560383_1/code/experiments/parttimenerd.github.io
hugo --quiet 2>&1 | head -30
```

Expected: clean build, no template errors. Common mistakes to check if it errors:
- Hugo uses underscores for data keys with hyphens: `site.Data.jvm_tools` not `site.Data.jvm-tools`, and `problem_finder` not `problem-finder`
- `merge` requires both arguments to be `dict` — `$toolMeta` must start as `dict`

- [ ] **Step 4: Commit**

```bash
cd /Users/i560383_1/code/experiments/parttimenerd.github.io
git add themes/projects-theme/layouts/partials/problem-finder.html
git commit -m "feat: add problem-finder Hugo partial"
```

---

## Task 3: Wire the partial into the jvm-tools page

**Files:**
- Modify: `themes/projects-theme/layouts/collection/list.html` (after line 32, before line 34)

The insertion point is after the closing `</div>` of the page header block and before the `#tool-nav` div. Currently lines 29–33 look like:

```html
  {{/* Page header */}}
  <div class="mb-8">
    <h1 class="font-['Vollkorn'] text-4xl font-bold mb-3">{{ .Title }}</h1>
    <p class="text-gray-600 text-lg max-w-2xl leading-relaxed">{{ .Content }}</p>
  </div>

  {{/* Sticky anchor nav */}}
```

- [ ] **Step 1: Insert the partial include**

Open `themes/projects-theme/layouts/collection/list.html` and add these two lines between the page header `</div>` and the `{{/* Sticky anchor nav */}}` comment:

```html
  {{/* Problem finder decision tree — jvm-tools only */}}
  {{ if eq .Section "jvm-tools" }}{{ partial "problem-finder.html" . }}{{ end }}
```

After the edit the relevant section should read:

```html
  {{/* Page header */}}
  <div class="mb-8">
    <h1 class="font-['Vollkorn'] text-4xl font-bold mb-3">{{ .Title }}</h1>
    <p class="text-gray-600 text-lg max-w-2xl leading-relaxed">{{ .Content }}</p>
  </div>

  {{/* Problem finder decision tree — jvm-tools only */}}
  {{ if eq .Section "jvm-tools" }}{{ partial "problem-finder.html" . }}{{ end }}

  {{/* Sticky anchor nav */}}
```

- [ ] **Step 2: Build and verify no errors**

```bash
cd /Users/i560383_1/code/experiments/parttimenerd.github.io
hugo --quiet 2>&1 | head -20
```

Expected: clean build.

- [ ] **Step 3: Commit**

```bash
cd /Users/i560383_1/code/experiments/parttimenerd.github.io
git add themes/projects-theme/layouts/collection/list.html
git commit -m "feat: include problem-finder widget on jvm-tools page"
```

---

## Task 4: Manual verification

**Files:** none (verification only)

- [ ] **Step 1: Start the dev server**

```bash
cd /Users/i560383_1/code/experiments/parttimenerd.github.io
npx tailwindcss -i themes/projects-theme/assets/css/main.css -o /tmp/tw-out.css --content "themes/projects-theme/layouts/**/*.html" 2>&1 | tail -5
hugo serve --disableFastRender
```

Navigate to `http://localhost:1313/jvm-tools/`

- [ ] **Step 2: Verify widget appears open by default**

The widget should be visible immediately between the page description and the sticky tool-nav. It should show the question "What problem are you trying to solve?" with 6 option buttons. No click should be required to see it.

- [ ] **Step 3: Walk the slow-app path**

Click "My app is slow or unresponsive" → "It's happening right now" → "Anywhere else".

Expected result node `r-jstall`:
- Headline: "You need instant insight into a running JVM."
- jstall card with badge, tagline_short, note about IntelliJ/VS Code plugins, "Go to tool ↓" link
- Blue follow-on callout: condensed-data + jfr-query
- "← Start over" link

- [ ] **Step 4: Walk the Cloud Foundry path**

Start over → "My app is slow" → "Right now" → "On Cloud Foundry".

Expected: cf-cli-java-plugin card with note "Bundles jstall internally". Same blue follow-on.

- [ ] **Step 5: Walk the deadlock path**

Start over → "My JVM crashed, froze, or is behaving strangely" → "A deadlock or race condition".

Expected: jstall card + amber follow-on with concurrency-fuzz-scheduler and taskcontrol linking to `/experiments/#concurrency-fuzz-scheduler`.

- [ ] **Step 6: Walk the heap → both path**

Start over → "I have a heap dump" → "Both — redact it, then analyse".

Expected: hprof-redact card ("Step 1") + hprof-analyzer card ("Step 2") shown together.

- [ ] **Step 7: Walk the execjar path**

Start over → "I want to speed up my build" → "I want to ship a single executable file".

Expected: execjar card + amber related callout for femtojar linking to `/femto/#femtojar`.

- [ ] **Step 8: Test back navigation**

Click through 2–3 options. Verify:
- Breadcrumb shows the labels you selected
- "← Back" steps to the previous node
- "Start over" jumps back to the root

- [ ] **Step 9: Test hide/show**

Click "Hide ✕". Widget collapses to "Not sure which tool you need? Show guide ▸". Click it — widget re-opens at `start`.

- [ ] **Step 10: Check femto and experiments pages are unaffected**

Navigate to `http://localhost:1313/femto/` and `http://localhost:1313/experiments/`. The widget must NOT appear on those pages.

- [ ] **Step 11: Check "Go to tool ↓" links**

From the jstall result, click "Go to tool ↓". The page should scroll to the `#jstall` section on the same page. From a result with a cross-section tool (e.g. femtojar), clicking the link should navigate to `/femto/#femtojar`.

- [ ] **Step 12: Verify tool metadata is not hardcoded**

Open browser devtools and inspect any tool card. The tagline_short text must match what's in `data/jvm-tools/static.yaml` exactly (e.g. jstall: "Instant JVM insight — deadlocks, hot threads, flamegraphs — no agent needed."). It should not be duplicated or hardcoded in the partial.

- [ ] **Step 13: Final build check**

```bash
cd /Users/i560383_1/code/experiments/parttimenerd.github.io
hugo --quiet 2>&1
```

Expected: zero errors, zero warnings about missing templates or data keys.

---

## Task 5: Fix x-cloak FOUC (if needed)

`x-cloak` hides elements before Alpine initialises. This only works if the CSS rule exists. Check whether it's already present:

- [ ] **Step 1: Check for existing x-cloak rule**

```bash
grep -n "x-cloak" /Users/i560383_1/code/experiments/parttimenerd.github.io/themes/projects-theme/assets/css/main.css
```

Expected output: `[style*="display:none"]` or `[x-cloak] { display: none; }` — if it already exists, this task is done.

- [ ] **Step 2: Add x-cloak rule if missing**

If step 1 returned no output, open `themes/projects-theme/assets/css/main.css` and add this line immediately after the `@tailwind base;` line at the top:

```css
[x-cloak] { display: none !important; }
```

- [ ] **Step 3: Rebuild and verify no flash**

```bash
cd /Users/i560383_1/code/experiments/parttimenerd.github.io
hugo serve --disableFastRender
```

Hard-refresh `/jvm-tools/`. The widget should appear fully rendered with no flash of raw Alpine markup.

- [ ] **Step 4: Commit if changed**

Only commit if you added the x-cloak rule in step 2:

```bash
cd /Users/i560383_1/code/experiments/parttimenerd.github.io
git add themes/projects-theme/assets/css/main.css
git commit -m "fix: add x-cloak display:none rule"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| YAML-driven tree, single file to edit | Task 1 |
| Flat node map, question + result types | Task 1 |
| Tool metadata resolved from static.yaml (no duplication) | Task 2 |
| Cross-section tools link to correct section | Task 2 |
| Widget open by default | Task 2 |
| Hide / show collapsed state | Task 2 |
| Back navigation + breadcrumb | Task 2 |
| All result nodes: headline, tool cards, follow-on, related | Task 2 |
| Wire into jvm-tools page only | Task 3 |
| femto/experiments pages unaffected | Task 4 step 10 |
| x-cloak prevents FOUC | Task 5 |
| `hugo build` clean | Task 4 step 13 |

**Placeholder scan:** none found — all code is complete and explicit.

**Type consistency:**
- `$toolMeta` is built as `dict` and accessed via `index $toolMeta .id` consistently throughout Task 2
- Node IDs in the YAML (`r-jstall`, `q-slow`, etc.) match the `cur === '{{ $nodeId }}'` checks exactly
- `go(id, label)` in Alpine state matches `@click="go('{{ $next }}', '{{ $label | htmlEscape }}')"` in template
- `back()` pops `{ id, label }` objects and reads `.id` — matches what `go()` pushes
- Hugo data key: `site.Data.jvm_tools.problem_finder` (underscores) — noted in Task 2 step 3 troubleshooting
