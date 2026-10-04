/// <reference types="vite/client" />

import "./style.css";

type AsOfDate = "2025-12-31" | "2026-01-02" | "2026-10-01" | "2027-07-02";

interface Address {
  address_id: string;
  street_address: string;
  postal_city: string;
  state: string;
  zip: string;
  legal_city: string | null;
  stack: string[];
  jurisdiction_confidence: string;
  geocode: {
    matched: boolean;
    method: string;
    place_name: string | null;
    county: string | null;
  };
  facts: {
    year_built: number | null;
    units: number | null;
    units_range: [number | null, number | null];
    units_source: string;
    flags: string[];
  };
}

interface Rule {
  team_rule_id?: string;
  category: string;
  citation: string;
  confidence?: number;
  corpus_text?: boolean;
  jurisdiction: string;
  level: string;
  status?: string;
  title: string;
  requirement: string;
  key_value?: string | null;
  quoted_span?: string | null;
  source_doc_id?: string | null;
  source_url?: string | null;
  retrieved_at?: string | null;
}

interface LookupItem {
  team_rule_id: string;
  result: string;
  explanation: string;
  conflict_flag?: boolean;
  conflict_note?: string | null;
}

interface LookupPayload {
  as_of?: string;
  lookups?: Record<string, LookupItem[]>;
}

interface ChangeRecord {
  affected_address_ids: string[];
  conflict_flag_address_ids: string[];
  notes: string;
}

interface ChangesDetail {
  [key: string]: {
    rules?: Record<string, {
      affected_address_ids?: string[];
      conflict_flag_address_ids?: string[];
      team_rule_ids?: string[];
    }>;
  };
}

interface Manifest {
  files: Record<string, string>;
}

type ActiveTab = "address" | "changes";

const AS_OF_DATES: AsOfDate[] = ["2025-12-31", "2026-01-02", "2026-10-01", "2027-07-02"];

const CATEGORIES = [
  ["rent_increase_limits", "Rent increase limits"],
  ["just_cause_eviction", "Just cause eviction"],
  ["security_deposits", "Security deposits"],
  ["application_screening_fees", "Application screening fees"],
  ["screening_restrictions", "Screening restrictions"],
  ["algorithmic_rent_setting", "Algorithmic rent setting"],
] as const;

const root = (() => {
  const element = document.querySelector<HTMLDivElement>("#app");
  if (!element) throw new Error("The app root is missing.");
  return element;
})();

const state: {
  manifest: Manifest;
  addresses: Address[];
  rules: Rule[];
  changes: Record<string, ChangeRecord>;
  changesDetail: ChangesDetail;
  lookups: Partial<Record<AsOfDate, LookupPayload>>;
  selectedAddressId: string;
  query: string;
  asOf: AsOfDate;
  activeTab: ActiveTab;
} = {
  manifest: { files: {} },
  addresses: [],
  rules: [],
  changes: {},
  changesDetail: {},
  lookups: {},
  selectedAddressId: "",
  query: "",
  asOf: "2026-10-01",
  activeTab: "address",
};

const dataUrl = (filename: string) => `${import.meta.env.BASE_URL}data/${filename}`;

async function loadJson<T>(filename: string): Promise<T> {
  const response = await fetch(dataUrl(filename), { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${filename} returned ${response.status}.`);
  }
  return (await response.json()) as T;
}

function escapeHtml(value: unknown): string {
  return String(value ?? "Not available").replace(/[&<>"']/g, (character) => {
    const entities: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[character];
  });
}

function displayDate(value: string | null | undefined): string {
  if (!value) return "Not recorded";
  const parsed = new Date(`${value.slice(0, 10)}T12:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat("en-US", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(parsed);
}

function titleCase(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function selectedAddress(): Address {
  const address = state.addresses.find((candidate) => candidate.address_id === state.selectedAddressId);
  if (!address) throw new Error("The selected address no longer exists in the exported data.");
  return address;
}

function addressLabel(address: Address): string {
  return `${address.street_address}, ${address.postal_city}, ${address.state} ${address.zip}`;
}

function addressSearchMatches(): Address[] {
  const query = state.query.trim().toLowerCase();
  if (!query) return state.addresses.slice(0, 8);
  return state.addresses
    .filter((address) => `${address.address_id} ${addressLabel(address)} ${address.legal_city ?? ""}`.toLowerCase().includes(query))
    .slice(0, 12);
}

function ruleMatchesAddress(rule: Rule, address: Address): boolean {
  return rule.jurisdiction === address.state || rule.jurisdiction === address.legal_city;
}

function lookupFor(rule: Rule, address: Address): LookupItem | undefined {
  const items = state.lookups[state.asOf]?.lookups?.[address.address_id] ?? [];
  return items.find((item) => item.team_rule_id === rule.team_rule_id);
}

function resultFor(rule: Rule, lookup: LookupItem | undefined): string {
  if (lookup) return lookup.result;
  if (rule.status === "pending") return "pending";
  if (rule.status === "not_yet_effective") return "not_yet_effective";
  return "awaiting_lookup";
}

function resultLabel(result: string): string {
  const labels: Record<string, string> = {
    applies: "Applies",
    unknown: "Unknown",
    superseded: "Superseded",
    pending: "Pending",
    not_yet_effective: "Not yet effective",
    awaiting_lookup: "Awaiting lookup",
  };
  return labels[result] ?? titleCase(result);
}

function fallbackExplanation(rule: Rule): string {
  if (rule.status === "pending") {
    return "This proposed rule is listed for the selected jurisdiction. Address-specific coverage has not yet been generated.";
  }
  if (rule.status === "not_yet_effective") {
    return "This rule is not yet effective on the selected date. Address-specific coverage has not yet been generated.";
  }
  return "This source rule matches the selected jurisdiction stack. Address-specific coverage has not yet been generated.";
}

function dataStatus(): string {
  const lookup = state.lookups[state.asOf]?.lookups;
  if (lookup) return `Address-specific lookup results are available for ${displayDate(state.asOf)}.`;
  return "Address-specific coverage is not yet exported. Jurisdiction-matched source rules are shown instead.";
}

function sourceLink(rule: Rule): string {
  if (!rule.source_url) return "<span class=\"source-missing\">Source link unavailable</span>";
  return `<a class=\"source-link\" href=\"${escapeHtml(rule.source_url)}\" target=\"_blank\" rel=\"noreferrer\">Open source</a>`;
}

function renderRule(rule: Rule, lookup: LookupItem | undefined): string {
  const result = resultFor(rule, lookup);
  const explanation = lookup?.explanation || fallbackExplanation(rule);
  const conflictNote = lookup?.conflict_note || (lookup?.conflict_flag
    ? "A conflict flag is recorded. Human review is recommended."
    : "No conflict note is currently recorded.");
  const quote = rule.quoted_span
    ? `<details class=\"quote\"><summary>View verified source excerpt</summary><blockquote>${escapeHtml(rule.quoted_span)}</blockquote></details>`
    : "<p class=\"quote-empty\">No source excerpt is available for this record.</p>";
  const researchTag = rule.corpus_text === false
    ? "<span class=\"research-tag\">Research copy, not corpus</span>"
    : "";
  const keyValue = rule.key_value
    ? `<p class=\"key-value\"><span>Key value</span>${escapeHtml(rule.key_value)}</p>`
    : "";

  return `
    <article class=\"rule-card\">
      <div class=\"rule-card-top\">
        <div>
          <p class=\"rule-meta\">${escapeHtml(rule.level)} rule${rule.source_doc_id ? ` · ${escapeHtml(rule.source_doc_id)}` : ""}</p>
          <h3>${escapeHtml(rule.title)}</h3>
        </div>
        <span class=\"result-badge result-${escapeHtml(result)}\">${escapeHtml(resultLabel(result))}</span>
      </div>
      ${researchTag}
      <p class=\"rule-explanation\">${escapeHtml(explanation)}</p>
      ${keyValue}
      <dl class=\"rule-details\">
        <div><dt>Citation</dt><dd>${escapeHtml(rule.citation)}</dd></div>
        <div><dt>Retrieved</dt><dd>${escapeHtml(displayDate(rule.retrieved_at))}</dd></div>
      </dl>
      <p class=\"conflict-note\"><strong>Conflict note:</strong> ${escapeHtml(conflictNote)}</p>
      <div class=\"rule-footer\">${sourceLink(rule)}${quote}</div>
    </article>
  `;
}

function renderCategory(category: string, label: string, address: Address): string {
  const rules = state.rules
    .filter((rule) => rule.category === category && ruleMatchesAddress(rule, address))
    .sort((left, right) => left.citation.localeCompare(right.citation));

  const ruleCards = rules.length
    ? rules.map((rule) => renderRule(rule, lookupFor(rule, address))).join("")
    : `<div class=\"empty-category\"><p>No source rule is currently available for this category in the selected jurisdiction stack.</p></div>`;

  return `
    <section class=\"category-section\" aria-labelledby=\"category-${escapeHtml(category)}\">
      <div class=\"category-heading\">
        <h2 id=\"category-${escapeHtml(category)}\">${escapeHtml(label)}</h2>
        <span>${rules.length} ${rules.length === 1 ? "record" : "records"}</span>
      </div>
      <div class=\"rule-list\">${ruleCards}</div>
    </section>
  `;
}

function factsSummary(address: Address): string {
  const facts = address.facts;
  const year = facts.year_built ?? "Not recorded";
  const units = facts.units ?? `${facts.units_range[0] ?? "?"}${facts.units_range[1] ? `-${facts.units_range[1]}` : "+"}`;
  const flags = facts.flags.length ? facts.flags.join(", ") : "None recorded";
  return `
    <dl class=\"fact-grid\">
      <div><dt>Year built</dt><dd>${escapeHtml(year)}</dd></div>
      <div><dt>Units</dt><dd>${escapeHtml(units)}</dd></div>
      <div><dt>Fact source</dt><dd>${escapeHtml(titleCase(facts.units_source))}</dd></div>
      <div><dt>Flags</dt><dd>${escapeHtml(flags)}</dd></div>
    </dl>
  `;
}

function renderAddressResults(): void {
  const target = root.querySelector<HTMLDivElement>("#address-results");
  if (!target) return;
  const matches = addressSearchMatches();
  const count = root.querySelector<HTMLElement>("#address-result-count");
  if (count) {
    count.textContent = state.query.trim()
      ? `${matches.length} matching ${matches.length === 1 ? "address" : "addresses"}`
      : "Recent addresses";
  }
  target.innerHTML = matches.length
    ? matches.map((address) => `
      <button class=\"address-option${address.address_id === state.selectedAddressId ? " is-selected" : ""}\" type=\"button\" data-address-id=\"${escapeHtml(address.address_id)}\">
        <strong>${escapeHtml(address.address_id)}</strong>
        <span>${escapeHtml(addressLabel(address))}</span>
      </button>
    `).join("")
    : "<p class=\"search-empty\">No addresses match that search.</p>";
  bindAddressChoices();
}

function bindAddressChoices(): void {
  root.querySelectorAll<HTMLButtonElement>("[data-address-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedAddressId = button.dataset.addressId ?? state.selectedAddressId;
      state.query = "";
      render();
    });
  });
}

function renderAddressTab(address: Address): string {
  return `
    <div class="workspace">
      <aside class="search-panel" aria-label="Address search">
        <div class="panel-heading">
          <span>Address index</span>
          <strong>${state.addresses.length}</strong>
        </div>
        <label for="address-search">Find an address</label>
        <p class="field-help">Search by address ID, street, postal city, or legal city.</p>
        <input id="address-search" type="search" autocomplete="off" value="${escapeHtml(state.query)}" placeholder="A0001 or De Longpre" />
        <p id="address-result-count" class="address-result-count" aria-live="polite">Recent addresses</p>
        <div id="address-results" class="address-results"></div>
      </aside>
      <main class="address-workspace">
        <section class="jurisdiction-card" aria-labelledby="jurisdiction-heading">
          <div class="jurisdiction-title-row">
            <div class="section-title">
              <p>Jurisdiction profile</p>
              <h2 id="jurisdiction-heading">${escapeHtml(addressLabel(address))}</h2>
            </div>
            <span class="confidence-chip">${escapeHtml(titleCase(address.jurisdiction_confidence))} confidence</span>
          </div>
          <div class=\"jurisdiction-grid\">
            <div><span>Postal city</span><strong>${escapeHtml(`${address.postal_city}, ${address.state}`)}</strong></div>
            <div><span>Legal city</span><strong>${escapeHtml(address.legal_city ?? "No incorporated place")}</strong></div>
            <div><span>Confidence</span><strong>${escapeHtml(titleCase(address.jurisdiction_confidence))}</strong></div>
            <div><span>Geocode method</span><strong>${escapeHtml(titleCase(address.geocode.method))}</strong></div>
          </div>
          ${factsSummary(address)}
        </section>
        <p class=\"data-notice\">${escapeHtml(dataStatus())}</p>
        <div class=\"categories\">
          ${CATEGORIES.map(([category, label]) => renderCategory(category, label, address)).join("")}
        </div>
      </main>
    </div>
  `;
}

function renderAddressIdList(ids: string[], label: string): string {
  if (!ids.length) return `<p class=\"list-empty\">No ${escapeHtml(label.toLowerCase())} are recorded.</p>`;
  return `
    <details class=\"address-list-details\">
      <summary>View ${ids.length} ${escapeHtml(label.toLowerCase())}</summary>
      <p class=\"address-id-list\">${ids.map(escapeHtml).join(" ")}</p>
    </details>
  `;
}

function renderChangeDetails(testId: string): string {
  const rules = state.changesDetail[testId]?.rules;
  if (!rules || !Object.keys(rules).length) return "";
  return `
    <details class=\"per-rule-details\">
      <summary>View rule-level breakdown</summary>
      ${Object.entries(rules).map(([ruleId, record]) => `
        <div class=\"per-rule-row\">
          <strong>${escapeHtml(ruleId)}</strong>
          <span>${record.affected_address_ids?.length ?? 0} affected</span>
          <span>${record.conflict_flag_address_ids?.length ?? 0} conflict flags</span>
        </div>
      `).join("")}
    </details>
  `;
}

function renderChangesTab(): string {
  const tests = ["T1", "T2", "T3", "T4", "T5"];
  return `
    <main class=\"changes-workspace\">
      <section class="changes-intro">
        <p>Scenario tests</p>
        <h2>How the supplied test cases change the answer</h2>
        <span>Counts and address lists reflect the current exported change artifacts.</span>
      </section>
      <div class=\"change-grid\">
        ${tests.map((testId) => {
          const record = state.changes[testId];
          if (!record) {
            return `<section class=\"change-card\"><h3>${testId}</h3><p>Change output is not exported yet.</p></section>`;
          }
          return `
            <section class=\"change-card\" aria-labelledby=\"${testId.toLowerCase()}-heading\">
              <div class=\"change-card-heading\"><h3 id=\"${testId.toLowerCase()}-heading\">${testId}</h3><span>Current data</span></div>
              <div class=\"change-counts\"><div><strong>${record.affected_address_ids.length}</strong><span>Affected addresses</span></div><div><strong>${record.conflict_flag_address_ids.length}</strong><span>Conflict flags</span></div></div>
              <p class=\"change-notes\">${escapeHtml(record.notes)}</p>
              ${renderAddressIdList(record.affected_address_ids, "Affected address IDs")}
              ${renderAddressIdList(record.conflict_flag_address_ids, "Conflict-flagged address IDs")}
              ${renderChangeDetails(testId)}
            </section>
          `;
        }).join("")}
      </div>
    </main>
  `;
}

function render(): void {
  const address = selectedAddress();
  const rulesCount = state.rules.length;
  root.innerHTML = `
    <div class="site-shell">
      <a class="skip-link" href="#content">Skip to navigator content</a>
      <div class="legal-banner"><span>Legal notice</span> Not legal advice. Prototype for a hackathon.</div>
      <header class="topbar">
        <a class="brand" href="#top" aria-label="Rental Housing Law Navigator home">
          <span class="brand-mark" aria-hidden="true">RL</span>
          <span><strong>Rental Housing Law Navigator</strong><small>Static research navigator</small></span>
        </a>
        <div class="data-summary" aria-label="Current data volume">
          <span><strong>${rulesCount}</strong> source rules</span>
          <i aria-hidden="true"></i>
          <span><strong>${state.addresses.length}</strong> resolved addresses</span>
        </div>
      </header>
      <div id="top" class="page-frame">
        <section class="page-intro">
          <div>
            <p>Address and date review</p>
            <h1>Understand the rules that may apply to one rental address.</h1>
            <div class="intro-meta"><span>6 rule categories</span><span>4 effective dates</span><span>Static local evidence</span></div>
          </div>
          <div class="as-of-control">
            <label for="as-of-select">As of date</label>
            <select id="as-of-select">${AS_OF_DATES.map((date) => `<option value="${date}"${date === state.asOf ? " selected" : ""}>${displayDate(date)}</option>`).join("")}</select>
            <span class="control-caption">Review results for a specific effective date.</span>
          </div>
        </section>
        <div id="content" tabindex="-1">
          <nav class="tabs" aria-label="Navigator views">
            <button class="tab-button${state.activeTab === "address" ? " is-active" : ""}" type="button" data-tab="address">Address review</button>
            <button class="tab-button${state.activeTab === "changes" ? " is-active" : ""}" type="button" data-tab="changes">Change tests</button>
          </nav>
          ${state.activeTab === "address" ? renderAddressTab(address) : renderChangesTab()}
        </div>
      </div>
      <footer>All rule and address data shown here are local, static exports. As of ${displayDate(state.asOf)}. Not legal advice.</footer>
    </div>
  `;

  const search = root.querySelector<HTMLInputElement>("#address-search");
  search?.addEventListener("input", () => {
    state.query = search.value;
    renderAddressResults();
  });
  root.querySelector<HTMLSelectElement>("#as-of-select")?.addEventListener("change", (event) => {
    state.asOf = (event.currentTarget as HTMLSelectElement).value as AsOfDate;
    render();
  });
  root.querySelectorAll<HTMLButtonElement>("[data-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeTab = button.dataset.tab as ActiveTab;
      render();
    });
  });
  renderAddressResults();
}

async function initialize(): Promise<void> {
  root.innerHTML = `
    <div class=\"loading-shell\">
      <div class=\"legal-banner\">Not legal advice. Prototype for a hackathon.</div>
      <main class=\"loading-content\"><p>Loading the local address and rule exports.</p><div class=\"loading-lines\"><span></span><span></span><span></span></div></main>
    </div>
  `;
  try {
    state.manifest = await loadJson<Manifest>("data_manifest.json");
    const [addresses, rulesPayload, changes, changesDetail] = await Promise.all([
      loadJson<Address[]>("addresses_resolved.json"),
      loadJson<{ rules: Rule[] }>("rules.json"),
      state.manifest.files["changes.json"] ? loadJson<Record<string, ChangeRecord>>("changes.json") : Promise.resolve({}),
      state.manifest.files["changes_detail.json"] ? loadJson<ChangesDetail>("changes_detail.json") : Promise.resolve({}),
    ]);
    state.addresses = addresses;
    state.rules = rulesPayload.rules;
    state.changes = changes;
    state.changesDetail = changesDetail;
    state.selectedAddressId = addresses[0]?.address_id ?? "";

    await Promise.all(AS_OF_DATES.map(async (date) => {
      const filename = `lookups_${date}.json`;
      if (state.manifest.files[filename]) state.lookups[date] = await loadJson<LookupPayload>(filename);
    }));

    if (!state.selectedAddressId) throw new Error("The address export is empty.");
    render();
  } catch (error) {
    const message = error instanceof Error ? error.message : "An unknown error occurred.";
    root.innerHTML = `
      <div class=\"error-shell\">
        <div class=\"legal-banner\">Not legal advice. Prototype for a hackathon.</div>
        <main class=\"error-content\"><p>Data could not load.</p><h1>The static export is not ready.</h1><span>${escapeHtml(message)}</span><code>python -m navigator.export_web</code></main>
      </div>
    `;
  }
}

void initialize();
