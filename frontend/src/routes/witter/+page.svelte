<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';

  // ─── State ──────────────────────────────────────────────────────────────────
  let year = new Date().getFullYear();
  const YEARS = [2025, 2026, 2027];
  let ref2024 = null;
  let data = null;
  let saving = false;
  let saved = false;
  let prefilling = false;
  let prefillResult = null; // summary of what was auto-filled
  let prefilledFields = {}; // key → true for green highlighting of auto-filled cells
  let error = null;
  let activeTab = 'nutzer'; // 'nutzer' | 'nebenkosten' | 'heizkosten'

  // ─── Load ───────────────────────────────────────────────────────────────────
  onMount(async () => {
    await load();
  });

  async function load() {
    error = null;
    try {
      [ref2024, data] = await Promise.all([
        api.getWitterRef2024(),
        api.getWitter(year),
      ]);
    } catch (e) {
      error = e.message;
    }
  }

  async function changeYear(y) {
    year = y;
    data = null;
    prefillResult = null;
    prefilledFields = {};
    await load();
  }

  // ─── Prefill helpers ─────────────────────────────────────────────────────────
  /** CSS class for a table row that may have been auto-filled */
  function pfRowCls(key) {
    return 'border-b border-gray-100' + (prefilledFields[key] ? ' bg-emerald-50/50' : '');
  }
  /** CSS class for an input that may have been auto-filled (pass extra classes like 'text-right') */
  function pfInputCls(key, extra = '') {
    const pf = prefilledFields[key];
    return `rounded px-2 py-1 text-xs focus:ring-1 focus:ring-primary-400${extra ? ' ' + extra : ''} ${pf ? 'border border-emerald-400 bg-emerald-50' : 'border'}`;
  }

  // ─── Prefill from transactions ───────────────────────────────────────────────
  async function prefill() {
    prefilling = true; prefillResult = null; error = null;
    try {
      const pf = await api.prefillWitter(year);
      let filled = 0;

      // Merge Nebenkosten
      pf.nebenkosten.forEach((pfRow) => {
        const row = data.nebenkosten.find(r => r.kategorie === pfRow.kategorie);
        if (row && pfRow._matched) {
          if (pfRow.betrag_brutto != null) { row.betrag_brutto = pfRow.betrag_brutto; filled++; }
          if (pfRow.lieferant)    row.lieferant = pfRow.lieferant;
          if (pfRow.rechnungsdatum) row.rechnungsdatum = pfRow.rechnungsdatum;
          if (pfRow.nr)            row.nr = pfRow.nr;
          prefilledFields[`nk:${pfRow.kategorie}`] = true;
        }
      });

      // Merge Wasserkosten
      pf.wasserkosten.forEach((pfRow) => {
        const row = data.wasserkosten.find(r => r.kategorie === pfRow.kategorie);
        if (row && pfRow._matched) {
          if (pfRow.betrag_brutto != null) { row.betrag_brutto = pfRow.betrag_brutto; filled++; }
          if (pfRow.lieferant)    row.lieferant = pfRow.lieferant;
          if (pfRow.rechnungsdatum) row.rechnungsdatum = pfRow.rechnungsdatum;
          prefilledFields[`wk:${pfRow.kategorie}`] = true;
        }
      });

      // Merge Heiznebenkosten
      pf.heiznebenkosten.forEach((pfRow) => {
        const row = data.heiznebenkosten.find(r => r.kategorie === pfRow.kategorie);
        if (row && pfRow._matched) {
          if (pfRow.betrag_brutto != null) { row.betrag_brutto = pfRow.betrag_brutto; filled++; }
          if (pfRow.datum) row.datum = pfRow.datum;
          prefilledFields[`hk:${pfRow.kategorie}`] = true;
        }
      });

      // Merge Vorauszahlungen per Wohnungsnutzer
      const vz = pf.wohnungsnutzer_vorauszahlungen || {};
      data.wohnungsnutzer.forEach((row) => {
        if (vz[row.whg_nr] != null) {
          row.vorauszahlungen = vz[row.whg_nr];
          filled++;
          prefilledFields[`vz:${row.whg_nr}`] = true;
        }
      });

      // Merge Brennstoffkosten Einkäufe (Berechnungsgrundlage Seite 2)
      if (pf.brennstoffkosten?._matched && pf.brennstoffkosten.einkaufe?.length > 0) {
        data.brennstoffkosten.einkaufe = pf.brennstoffkosten.einkaufe.map(e => ({
          datum: e.datum,
          menge: null,
          betrag_brutto: e.betrag_brutto,
        }));
        filled += pf.brennstoffkosten.einkaufe.length;
        prefilledFields['brennstoff'] = true;
      }

      // Force Svelte reactivity
      prefilledFields = prefilledFields;
      data = { ...data };

      const matchedRows = [...pf.nebenkosten, ...pf.wasserkosten, ...pf.heiznebenkosten].filter(r => r._matched);
      const details = matchedRows.map(r => `${r.kategorie}: ${r.betrag_brutto?.toLocaleString('de-DE', {minimumFractionDigits: 2}) ?? '—'} € (${r._count} Buchung${r._count !== 1 ? 'en' : ''})`);
      if (pf.brennstoffkosten?._matched) {
        details.push(`Brennstoffeinkauf: ${pf.brennstoffkosten._total?.toLocaleString('de-DE', {minimumFractionDigits: 2}) ?? '—'} € (${pf.brennstoffkosten._count} Buchung${pf.brennstoffkosten._count !== 1 ? 'en' : ''})`);
      }
      prefillResult = { filled, details };
    } catch (e) {
      error = e.message;
    } finally {
      prefilling = false;
    }
  }

  // ─── Save ───────────────────────────────────────────────────────────────────
  async function save() {
    saving = true; saved = false; error = null;
    try {
      await api.saveWitter(year, data);
      saved = true;
      setTimeout(() => { saved = false; }, 3000);
    } catch (e) {
      error = e.message;
    } finally {
      saving = false;
    }
  }

  // ─── Helpers ────────────────────────────────────────────────────────────────
  function fmtRef(v) {
    if (v == null) return '—';
    if (typeof v === 'number') return v.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return v;
  }

  function refNK(idx, field) {
    return ref2024?.nebenkosten?.[idx]?.[field] ?? null;
  }
  function refWK(idx, field) {
    return ref2024?.wasserkosten?.[idx]?.[field] ?? null;
  }
  function refHN(idx, field) {
    return ref2024?.heiznebenkosten?.[idx]?.[field] ?? null;
  }
  function refWN(idx, field) {
    return ref2024?.wohnungsnutzer?.[idx]?.[field] ?? null;
  }
  function refBK(field) {
    return ref2024?.brennstoffkosten?.[field] ?? null;
  }
  function refBKEinkauf(idx, field) {
    return ref2024?.brennstoffkosten?.einkaufe?.[idx]?.[field] ?? null;
  }

  // Brennstoffeinkauf rows
  function addEinkauf() {
    data.brennstoffkosten.einkaufe = [...data.brennstoffkosten.einkaufe, { datum: null, menge: null, betrag_brutto: null }];
  }
  function removeEinkauf(i) {
    data.brennstoffkosten.einkaufe = data.brennstoffkosten.einkaufe.filter((_, idx) => idx !== i);
  }

  // Computed Gesamtverbrauch
  $: gesamtverbrauch = (() => {
    if (!data) return null;
    const bk = data.brennstoffkosten;
    const vor = bk.vorjahresbestand_menge ?? 0;
    const ein = (bk.einkaufe || []).reduce((s, e) => s + (e.menge ?? 0), 0);
    const end = bk.jahresendbestand_menge ?? 0;
    return vor + ein - end;
  })();
</script>

<div class="max-w-5xl mx-auto">
  <!-- ── Header ── -->
  <div class="flex items-center justify-between mb-6">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">Witter Berechnungsgrundlage</h1>
      <p class="text-sm text-gray-500 mt-1">Eingabedaten für das Witter Heizkostenabrechnung-Formular (Nr. 25737)</p>
    </div>
    <div class="flex items-center gap-3">
      <!-- Year selector -->
      <div class="flex gap-1 bg-gray-100 rounded-lg p-1">
        {#each YEARS as y}
          <button
            on:click={() => changeYear(y)}
            class="px-4 py-1.5 text-sm font-medium rounded-md transition-colors
              {year === y ? 'bg-white shadow text-primary-700' : 'text-gray-500 hover:text-gray-700'}"
          >{y}</button>
        {/each}
      </div>
      <button
        on:click={prefill}
        disabled={prefilling || !data}
        class="px-4 py-2 text-sm font-medium rounded-lg border border-primary-300
          bg-primary-50 hover:bg-primary-100 text-primary-700 transition-colors disabled:opacity-50"
      >
        {#if prefilling}⏳ Erkenne Buchungen…{:else}⚡ Aus Buchungen vorbefüllen{/if}
      </button>
      <button
        on:click={save}
        disabled={saving || !data}
        class="px-4 py-2 text-sm font-medium rounded-lg transition-colors
          {saved ? 'bg-green-600 text-white' : 'bg-primary-600 hover:bg-primary-700 text-white disabled:opacity-50'}"
      >
        {#if saving}Speichern…{:else if saved}✓ Gespeichert{:else}💾 Speichern{/if}
      </button>
    </div>
  </div>

  {#if error}
    <div class="bg-red-50 border border-red-200 rounded-lg p-4 mb-4 text-red-700 text-sm">{error}</div>
  {/if}

  {#if prefillResult}
    <div class="bg-green-50 border border-green-200 rounded-lg px-4 py-3 mb-4 text-sm text-green-800">
      <div class="flex items-center justify-between">
        <span class="font-semibold">⚡ {prefillResult.filled} Felder aus Buchungen vorbefüllt</span>
        <button on:click={() => prefillResult = null} class="text-green-500 hover:text-green-700 text-lg leading-none">×</button>
      </div>
      {#if prefillResult.details.length > 0}
        <ul class="mt-2 space-y-0.5">
          {#each prefillResult.details as d}
            <li class="text-xs text-green-700">✓ {d}</li>
          {/each}
        </ul>
      {/if}
      <p class="text-xs text-green-600 mt-2">Fehlende Felder (z.B. Grundsteuer, Müllentsorgung) bitte manuell eintragen. Anschließend speichern.</p>
    </div>
  {/if}

  {#if !data}
    <div class="text-center py-16 text-gray-400">Lade…</div>
  {:else}

  <!-- ── Hint ── -->
  <div class="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 mb-5 text-sm text-blue-800 flex items-start gap-2">
    <span class="text-lg leading-none mt-0.5">ℹ</span>
    <div>
      Die <span class="font-semibold">grauen Werte</span> sind die Referenzwerte aus dem
      <span class="font-semibold">gescannten 2024er Formular</span>. Klicke <span class="font-semibold">„Aus Buchungen vorbefüllen"</span> um Beträge
      automatisch aus den gespeicherten Buchungen des Jahres {year} zu übernehmen. Dann fehlende Felder manuell ergänzen.
    </div>
  </div>

  <!-- ── Tabs ── -->
  <div class="flex gap-1 border-b border-gray-200 mb-6">
    {#each [['nutzer','📋 Wohnungsnutzer (Seite 3)'],['nebenkosten','💧 Neben- & Wasserkosten (Seite 1)'],['heizkosten','🔥 Heizkosten (Seite 2)']] as [tab, label]}
      <button
        on:click={() => activeTab = tab}
        class="px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px
          {activeTab === tab
            ? 'border-primary-600 text-primary-700'
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
      >{label}</button>
    {/each}
  </div>


  <!-- ══════════════════ TAB: WOHNUNGSNUTZER ══════════════════ -->
  {#if activeTab === 'nutzer'}
  <div class="space-y-4">

    <!-- Kopfdaten -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">Kopfdaten / Liegenschaft</h2>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
        <div>
          <label class="block text-xs text-gray-500 mb-1">Kundennummer</label>
          <input bind:value={data.kundennummer} class="w-full border rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-primary-500" />
          <p class="text-xs text-gray-400 mt-0.5">2024: {ref2024.kundennummer}</p>
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">Abrechnungszeitraum von</label>
          <input type="date" bind:value={data.von} class="w-full border rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-primary-500" />
          <p class="text-xs text-gray-400 mt-0.5">2024: {ref2024.von}</p>
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">Abrechnungszeitraum bis</label>
          <input type="date" bind:value={data.bis} class="w-full border rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-primary-500" />
          <p class="text-xs text-gray-400 mt-0.5">2024: {ref2024.bis}</p>
        </div>
      </div>
    </div>

    <!-- Wohnungsnutzer-Tabelle -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div class="px-5 py-4 border-b border-gray-100">
        <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Wohnungsnutzer-Tabelle</h2>
        <p class="text-xs text-gray-500 mt-1">Entspricht der Tabelle auf Seite 3 des Witter-Formulars. Vorauszahlungen = Jahres-Hausgeld je Wohnung.</p>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50">
            <tr class="text-xs text-gray-500 border-b border-gray-200">
              <th class="px-3 py-2.5 text-left font-medium">Whg. Nr.</th>
              <th class="px-3 py-2.5 text-left font-medium">Lage der Wohnung</th>
              <th class="px-3 py-2.5 text-left font-medium">Whg. Eigentümer</th>
              <th class="px-3 py-2.5 text-left font-medium">Whg. Nutzer</th>
              <th class="px-3 py-2.5 text-right font-medium">Wohnfläche m²</th>
              <th class="px-3 py-2.5 text-right font-medium">Beheizte Wohnfl. m²</th>
              <th class="px-3 py-2.5 text-right font-medium">Personen</th>
              <th class="px-3 py-2.5 text-right font-medium">Vorauszahl. €¹⁾</th>
              <th class="px-3 py-2.5 text-left font-medium pl-4">Nutzerwechsel</th>
            </tr>
            <!-- 2024 reference row -->
            <tr class="text-xs text-blue-400 bg-blue-50/50 border-b border-blue-100">
              <th class="px-3 py-1 text-left font-normal italic">2024 →</th>
              {#each ['lage','eigentuemer','nutzer','wohnflaeche','beheizte_wohnflaeche','personen','vorauszahlungen'] as f}
                <th class="px-3 py-1 text-right font-normal italic">
                  {['lage','eigentuemer','nutzer'].includes(f) ? '— text —' : '— Zahl —'}
                </th>
              {/each}
              <th></th>
            </tr>
          </thead>
          <tbody>
            {#each data.wohnungsnutzer as row, i}
              <tr class="border-b border-gray-50 hover:bg-gray-50/50">
                <td class="px-3 py-2">
                  <span class="font-mono text-xs bg-primary-100 text-primary-700 rounded px-1.5 py-0.5">{row.whg_nr}</span>
                </td>
                <td class="px-3 py-2">
                  <input bind:value={row.lage} class="w-20 border rounded px-1.5 py-1 text-xs focus:ring-1 focus:ring-primary-400" />
                  <div class="text-xs text-gray-400 mt-0.5">2024: {fmtRef(refWN(i,'lage'))}</div>
                </td>
                <td class="px-3 py-2">
                  <input bind:value={row.eigentuemer} class="w-28 border rounded px-1.5 py-1 text-xs focus:ring-1 focus:ring-primary-400" />
                  <div class="text-xs text-gray-400 mt-0.5">2024: {fmtRef(refWN(i,'eigentuemer'))}</div>
                </td>
                <td class="px-3 py-2">
                  <input bind:value={row.nutzer} class="w-28 border rounded px-1.5 py-1 text-xs focus:ring-1 focus:ring-primary-400" />
                  <div class="text-xs text-gray-400 mt-0.5">2024: {fmtRef(refWN(i,'nutzer'))}</div>
                </td>
                <td class="px-3 py-2 text-right">
                  <input type="number" step="0.01" bind:value={row.wohnflaeche} class="w-16 border rounded px-1.5 py-1 text-xs text-right focus:ring-1 focus:ring-primary-400" />
                  <div class="text-xs text-gray-400 mt-0.5">{fmtRef(refWN(i,'wohnflaeche'))}</div>
                </td>
                <td class="px-3 py-2 text-right">
                  <input type="number" step="0.01" bind:value={row.beheizte_wohnflaeche} class="w-16 border rounded px-1.5 py-1 text-xs text-right focus:ring-1 focus:ring-primary-400" />
                  <div class="text-xs text-gray-400 mt-0.5">{fmtRef(refWN(i,'beheizte_wohnflaeche'))}</div>
                </td>
                <td class="px-3 py-2 text-right">
                  <input type="number" min="0" bind:value={row.personen} class="w-12 border rounded px-1.5 py-1 text-xs text-right focus:ring-1 focus:ring-primary-400" />
                  <div class="text-xs text-gray-400 mt-0.5">{fmtRef(refWN(i,'personen'))}</div>
                </td>
                <td class="px-3 py-2 text-right">
                  <input type="number" step="0.01" bind:value={row.vorauszahlungen} placeholder="0,00" class="w-24 text-right {pfInputCls(`vz:${row.whg_nr}`)}" />
                  <div class="text-xs text-gray-400 mt-0.5">{fmtRef(refWN(i,'vorauszahlungen'))} €</div>
                </td>
                <td class="px-3 py-2 pl-4">
                  <div class="flex gap-2 items-center">
                    <div>
                      <label class="text-xs text-gray-500">Einzug</label>
                      <input type="date" bind:value={row.einzug} class="block w-32 border rounded px-1.5 py-1 text-xs focus:ring-1 focus:ring-primary-400 mt-0.5" />
                    </div>
                    <div>
                      <label class="text-xs text-gray-500">Auszug</label>
                      <input type="date" bind:value={row.auszug} class="block w-32 border rounded px-1.5 py-1 text-xs focus:ring-1 focus:ring-primary-400 mt-0.5" />
                    </div>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <div class="px-5 py-3 bg-gray-50 text-xs text-gray-500 border-t border-gray-100">
        ¹⁾ Bitte den Gesamtbetrag des Jahres für den vollständigen Abrechnungszeitraum eingeben.
      </div>
    </div>
  </div>
  {/if}


  <!-- ══════════════════ TAB: NEBEN- & WASSERKOSTEN ══════════════════ -->
  {#if activeTab === 'nebenkosten'}
  <div class="space-y-6">

    <!-- Nebenkosten -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div class="px-5 py-4 border-b border-gray-100">
        <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Nebenkosten</h2>
        <p class="text-xs text-gray-500 mt-1">Linke Tabelle auf Seite 1 des Witter-Formulars.</p>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50">
            <tr class="text-xs text-gray-500 border-b border-gray-200">
              <th class="px-3 py-2.5 text-left font-medium w-44">Kostenkategorie</th>
              <th class="px-3 py-2.5 text-left font-medium">Lieferant / Vertragspartner</th>
              <th class="px-3 py-2.5 text-left font-medium">Nr.</th>
              <th class="px-3 py-2.5 text-left font-medium">Rechnungsdatum</th>
              <th class="px-3 py-2.5 text-right font-medium">Betrag Brutto €</th>
              <th class="px-3 py-2.5 text-right font-medium">Gesamtbetrag €<br><span class="font-normal">(Mischrechnung)</span></th>
              <th class="px-3 py-2.5 text-right font-medium">Anteil Arbeitskosten<br>Brutto €</th>
              <th class="px-3 py-2.5 text-left font-medium">Umlagebereift<br>Whg. Nr.</th>
            </tr>
          </thead>
          <tbody>
            {#each data.nebenkosten as row, i}
              <tr class={pfRowCls(`nk:${row.kategorie}`)}>
                <td class="px-3 py-2.5">
                  <span class="text-xs font-medium text-gray-800">{row.kategorie}</span>
                  {#if prefilledFields[`nk:${row.kategorie}`]}<span class="ml-1 text-emerald-500 text-xs" title="Automatisch aus Buchungen">⚡</span>{/if}
                </td>
                <td class="px-3 py-2">
                  <input bind:value={row.lieferant} placeholder="Lieferant eingeben" class="w-full border rounded px-2 py-1 text-xs focus:ring-1 focus:ring-primary-400" />
                  <div class="text-xs text-blue-400 mt-0.5">2024: {fmtRef(refNK(i,'lieferant'))}</div>
                </td>
                <td class="px-3 py-2">
                  <input bind:value={row.nr} placeholder="Rechnungs-Nr." class="w-24 border rounded px-2 py-1 text-xs focus:ring-1 focus:ring-primary-400" />
                  <div class="text-xs text-blue-400 mt-0.5">2024: {fmtRef(refNK(i,'nr'))}</div>
                </td>
                <td class="px-3 py-2">
                  <input type="date" bind:value={row.rechnungsdatum} class="w-32 {pfInputCls(`nk:${row.kategorie}`)}" />
                  <div class="text-xs text-blue-400 mt-0.5">2024: {fmtRef(refNK(i,'rechnungsdatum'))}</div>
                </td>
                <td class="px-3 py-2 text-right">
                  <input type="number" step="0.01" bind:value={row.betrag_brutto} placeholder="0,00" class="w-24 text-right {pfInputCls(`nk:${row.kategorie}`)}" />
                  <div class="text-xs text-blue-400 mt-0.5">{fmtRef(refNK(i,'betrag_brutto'))} €</div>
                </td>
                <td class="px-3 py-2 text-right">
                  <input type="number" step="0.01" bind:value={row.gesamtbetrag} placeholder="—" class="w-24 border rounded px-2 py-1 text-xs text-right focus:ring-1 focus:ring-primary-400" />
                  <div class="text-xs text-blue-400 mt-0.5">{fmtRef(refNK(i,'gesamtbetrag'))}</div>
                </td>
                <td class="px-3 py-2 text-right">
                  <input type="number" step="0.01" bind:value={row.anteil_arbeitskosten} placeholder="—" class="w-24 border rounded px-2 py-1 text-xs text-right focus:ring-1 focus:ring-primary-400" />
                  <div class="text-xs text-blue-400 mt-0.5">{fmtRef(refNK(i,'anteil_arbeitskosten'))}</div>
                </td>
                <td class="px-3 py-2">
                  <input bind:value={row.whg_nr} placeholder="alle" class="w-16 border rounded px-2 py-1 text-xs focus:ring-1 focus:ring-primary-400" />
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>

    <!-- Wasserkosten -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div class="px-5 py-4 border-b border-gray-100">
        <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Wasserkosten</h2>
        <p class="text-xs text-gray-500 mt-1">Rechte Tabelle auf Seite 1 des Witter-Formulars.</p>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50">
            <tr class="text-xs text-gray-500 border-b border-gray-200">
              <th class="px-3 py-2.5 text-left font-medium w-56">Kostenkategorie</th>
              <th class="px-3 py-2.5 text-left font-medium">Lieferant</th>
              <th class="px-3 py-2.5 text-left font-medium">Nr.</th>
              <th class="px-3 py-2.5 text-left font-medium">Rechnungsdatum</th>
              <th class="px-3 py-2.5 text-right font-medium">Betrag Brutto €</th>
              <th class="px-3 py-2.5 text-right font-medium">Gesamtbetrag €<br><span class="font-normal">(Mischrechnung)</span></th>
              <th class="px-3 py-2.5 text-right font-medium">Anteil Arbeitskosten<br>Brutto €</th>
              <th class="px-3 py-2.5 text-left font-medium">Umlagebereift<br>Whg. Nr.</th>
            </tr>
          </thead>
          <tbody>
            {#each data.wasserkosten as row, i}
              <tr class={pfRowCls(`wk:${row.kategorie}`)}>
                <td class="px-3 py-2.5">
                  <span class="text-xs font-medium text-gray-800">{row.kategorie}</span>
                  {#if prefilledFields[`wk:${row.kategorie}`]}<span class="ml-1 text-emerald-500 text-xs" title="Automatisch aus Buchungen">⚡</span>{/if}
                </td>
                <td class="px-3 py-2">
                  <input bind:value={row.lieferant} placeholder="Lieferant" class="w-full border rounded px-2 py-1 text-xs focus:ring-1 focus:ring-primary-400" />
                  <div class="text-xs text-blue-400 mt-0.5">2024: {fmtRef(refWK(i,'lieferant'))}</div>
                </td>
                <td class="px-3 py-2">
                  <input bind:value={row.nr} placeholder="Nr." class="w-24 border rounded px-2 py-1 text-xs focus:ring-1 focus:ring-primary-400" />
                </td>
                <td class="px-3 py-2">
                  <input type="date" bind:value={row.rechnungsdatum} class="w-32 {pfInputCls(`wk:${row.kategorie}`)}" />
                </td>
                <td class="px-3 py-2 text-right">
                  <input type="number" step="0.01" bind:value={row.betrag_brutto} placeholder="0,00" class="w-24 text-right {pfInputCls(`wk:${row.kategorie}`)}" />
                  <div class="text-xs text-blue-400 mt-0.5">{fmtRef(refWK(i,'betrag_brutto'))} €</div>
                </td>
                <td class="px-3 py-2 text-right">
                  <input type="number" step="0.01" bind:value={row.gesamtbetrag} placeholder="—" class="w-24 border rounded px-2 py-1 text-xs text-right focus:ring-1 focus:ring-primary-400" />
                </td>
                <td class="px-3 py-2 text-right">
                  <input type="number" step="0.01" bind:value={row.anteil_arbeitskosten} placeholder="—" class="w-24 border rounded px-2 py-1 text-xs text-right focus:ring-1 focus:ring-primary-400" />
                </td>
                <td class="px-3 py-2">
                  <input bind:value={row.whg_nr} placeholder="alle" class="w-16 border rounded px-2 py-1 text-xs focus:ring-1 focus:ring-primary-400" />
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>

  </div>
  {/if}


  <!-- ══════════════════ TAB: HEIZKOSTEN ══════════════════ -->
  {#if activeTab === 'heizkosten'}
  <div class="space-y-6">

    <!-- Stammdaten Heizanlage -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">Stammdaten Heizanlage</h2>
      <p class="text-xs text-gray-500 mb-4">Linke Spalte auf Seite 2. Diese Werte bleiben meistens konstant.</p>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
        <div>
          <label class="block text-xs text-gray-500 mb-1">Brennstoffart</label>
          <select bind:value={data.stammdaten_heizung.brennstoffart} class="w-full border rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-primary-500">
            <option>Heizöl</option><option>Erdgas</option><option>Pellets</option><option>Flüssiggas</option>
          </select>
          <p class="text-xs text-blue-400 mt-0.5">2024: {ref2024.stammdaten_heizung.brennstoffart}</p>
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">Mengenangabe (Einheit)</label>
          <select bind:value={data.stammdaten_heizung.mengeneinheit} class="w-full border rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-primary-500">
            <option>Liter</option><option>m³</option><option>kWh</option><option>kg</option>
          </select>
          <p class="text-xs text-blue-400 mt-0.5">2024: {ref2024.stammdaten_heizung.mengeneinheit}</p>
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">Heizwert je Einheit (kWh)</label>
          <input type="number" step="0.1" bind:value={data.stammdaten_heizung.heizwert} class="w-full border rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-primary-500" />
          <p class="text-xs text-blue-400 mt-0.5">2024: {ref2024.stammdaten_heizung.heizwert}</p>
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">Emissionsfaktor (kg CO₂/kWh)</label>
          <input type="number" step="0.001" bind:value={data.stammdaten_heizung.emissionsfaktor} placeholder="optional" class="w-full border rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-primary-500" />
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">Warmwasser Grundkostenanteil (%)</label>
          <input type="number" step="0.01" bind:value={data.stammdaten_heizung.warmwasser_grundkostenanteil} class="w-full border rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-primary-500" />
          <p class="text-xs text-blue-400 mt-0.5">2024: {ref2024.stammdaten_heizung.warmwasser_grundkostenanteil} %</p>
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">Heizung Grundkostenanteil (%)</label>
          <input type="number" step="0.01" bind:value={data.stammdaten_heizung.heizung_grundkostenanteil} class="w-full border rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-primary-500" />
          <p class="text-xs text-blue-400 mt-0.5">2024: {ref2024.stammdaten_heizung.heizung_grundkostenanteil} %</p>
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">Warmwassertemperatur (°C)</label>
          <input type="number" bind:value={data.stammdaten_heizung.warmwasser_temperatur} class="w-full border rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-primary-500" />
          <p class="text-xs text-blue-400 mt-0.5">2024: {ref2024.stammdaten_heizung.warmwasser_temperatur} °C</p>
        </div>
      </div>
    </div>

    <!-- Brennstoffkosten -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-1">Brennstoffkosten</h2>
      <p class="text-xs text-gray-500 mb-4">Untere Tabelle auf Seite 2. Zeilen: Brennstoffrest vom Vorjahr + alle Einkäufe im Jahr.</p>

      <!-- Spalten-Legende -->
      <div class="grid grid-cols-3 gap-3 mb-3 text-xs font-medium text-gray-500 border-b border-gray-100 pb-2">
        <span>Datum</span>
        <span>Menge ({data.stammdaten_heizung.mengeneinheit})</span>
        <span>Betrag Brutto €</span>
      </div>

      <!-- Brennstoffrest Vorjahr -->
      <div class="mb-4">
        <p class="text-xs font-semibold text-gray-600 mb-2">Brennstoffrest vom Vorjahr <span class="font-normal text-gray-400">(z.B. Heizöl, Pellets – Bestand am Anfang des Abrechnungsjahres)</span></p>
        <div class="grid grid-cols-3 gap-3">
          <div>
            <input type="date" bind:value={data.brennstoffkosten.vorjahresbestand_datum} class="w-full border rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-primary-500" />
            <p class="text-xs text-blue-400 mt-0.5">2024: {fmtRef(refBK('vorjahresbestand_datum'))}</p>
          </div>
          <div>
            <input type="number" step="1" bind:value={data.brennstoffkosten.vorjahresbestand_menge} placeholder="Menge" class="w-full border rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-primary-500" />
            <p class="text-xs text-blue-400 mt-0.5">2024: {fmtRef(refBK('vorjahresbestand_menge'))}</p>
          </div>
          <div>
            <input type="number" step="0.01" bind:value={data.brennstoffkosten.vorjahresbestand_betrag} placeholder="0,00" class="w-full border rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-primary-500" />
            <p class="text-xs text-blue-400 mt-0.5">2024: {fmtRef(refBK('vorjahresbestand_betrag'))} €</p>
          </div>
        </div>
      </div>

      <!-- Brennstoffeinkäufe -->
      <div class="mb-4">
        <p class="text-xs font-semibold text-gray-600 mb-2">Brennstoffeinkäufe im Abrechnungsjahr</p>
        {#each data.brennstoffkosten.einkaufe as einkauf, i}
          <div class="grid grid-cols-3 gap-3 mb-2 items-start {prefilledFields['brennstoff'] ? 'bg-emerald-50/30 rounded-lg p-1' : ''}">
            <div>
              <input type="date" bind:value={einkauf.datum} class="w-full border rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-primary-500 {prefilledFields['brennstoff'] ? 'border-emerald-400 bg-emerald-50' : ''}" />
              {#if i === 0}<p class="text-xs text-blue-400 mt-0.5">2024: {fmtRef(refBKEinkauf(0,'datum'))}</p>{/if}
            </div>
            <div>
              <input type="number" step="1" bind:value={einkauf.menge} placeholder="Menge" class="w-full border rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-primary-500" />
              {#if i === 0}<p class="text-xs text-blue-400 mt-0.5">2024: {fmtRef(refBKEinkauf(0,'menge'))}</p>{/if}
            </div>
            <div class="flex gap-2">
              <div class="flex-1">
                <input type="number" step="0.01" bind:value={einkauf.betrag_brutto} placeholder="0,00" class="w-full border rounded px-2 py-1.5 text-sm text-right focus:ring-1 focus:ring-primary-500 {prefilledFields['brennstoff'] ? 'border-emerald-400 bg-emerald-50' : ''}" />
                {#if i === 0}<p class="text-xs text-blue-400 mt-0.5">2024: {fmtRef(refBKEinkauf(0,'betrag_brutto'))} €</p>{/if}
              </div>
              {#if data.brennstoffkosten.einkaufe.length > 1}
                <button on:click={() => removeEinkauf(i)} class="mt-0.5 text-red-400 hover:text-red-600 text-lg leading-none">×</button>
              {/if}
            </div>
          </div>
        {/each}
        <button on:click={addEinkauf} class="mt-1 text-xs text-primary-600 hover:text-primary-800 font-medium">+ Weiteren Einkauf hinzufügen</button>
      </div>

      <!-- Jahresendbestand -->
      <div class="mb-4 border-t border-gray-100 pt-4">
        <p class="text-xs font-semibold text-gray-600 mb-2">Rest bei Ende der Heizperiode (Jahresendbestand) <span class="font-normal text-gray-400">− wird abgezogen</span></p>
        <div class="grid grid-cols-3 gap-3">
          <div class="col-span-1">
            <input type="number" step="1" bind:value={data.brennstoffkosten.jahresendbestand_menge} placeholder="Menge" class="w-full border rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-primary-500" />
            <p class="text-xs text-blue-400 mt-0.5">2024: {fmtRef(ref2024.brennstoffkosten.jahresendbestand_menge)}</p>
          </div>
        </div>
      </div>

      <!-- Gesamtverbrauch (berechnet) -->
      <div class="bg-gray-50 rounded-lg px-4 py-3 border border-gray-200 text-sm">
        <div class="flex items-center justify-between">
          <span class="font-semibold text-gray-700">= Gesamtverbrauch (berechnet)</span>
          <span class="font-mono font-bold text-lg {gesamtverbrauch != null && gesamtverbrauch > 0 ? 'text-gray-900' : 'text-gray-400'}">
            {gesamtverbrauch != null ? gesamtverbrauch.toLocaleString('de-DE', {minimumFractionDigits: 0, maximumFractionDigits: 0}) : '—'} {data.stammdaten_heizung.mengeneinheit}
          </span>
        </div>
        <p class="text-xs text-gray-500 mt-1">Formel: Vorjahresbestand + Σ Einkäufe − Jahresendbestand</p>
        <p class="text-xs text-blue-400">2024: 5.250 + 3.503 − 5.000 = <strong>3.753 Liter</strong></p>
      </div>
    </div>

    <!-- Heiznebenkosten -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div class="px-5 py-4 border-b border-gray-100">
        <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Heiznebenkosten</h2>
        <p class="text-xs text-gray-500 mt-1">Obere Tabelle auf Seite 2 des Witter-Formulars.</p>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50">
            <tr class="text-xs text-gray-500 border-b border-gray-200">
              <th class="px-3 py-2.5 text-left font-medium w-56">Kostenkategorie</th>
              <th class="px-3 py-2.5 text-left font-medium">Rechnungsdatum</th>
              <th class="px-3 py-2.5 text-left font-medium">Rechnungs-Nr.</th>
              <th class="px-3 py-2.5 text-right font-medium">Betrag Brutto €</th>
              <th class="px-3 py-2.5 text-right font-medium">Gesamtbetrag €<br><span class="font-normal">(Mischrechnung)</span></th>
              <th class="px-3 py-2.5 text-right font-medium">Anteil Arbeitskosten<br>Brutto €</th>
            </tr>
          </thead>
          <tbody>
            {#each data.heiznebenkosten as row, i}
              <tr class={pfRowCls(`hk:${row.kategorie}`)}>
                <td class="px-3 py-2.5">
                  <span class="text-xs font-medium text-gray-800">{row.kategorie}</span>
                  {#if prefilledFields[`hk:${row.kategorie}`]}<span class="ml-1 text-emerald-500 text-xs" title="Automatisch aus Buchungen">⚡</span>{/if}
                </td>
                <td class="px-3 py-2">
                  <input type="date" bind:value={row.datum} class="w-32 {pfInputCls(`hk:${row.kategorie}`)}" />
                  <div class="text-xs text-blue-400 mt-0.5">2024: {fmtRef(refHN(i,'datum'))}</div>
                </td>
                <td class="px-3 py-2">
                  <input bind:value={row.nr} placeholder="Nr." class="w-24 border rounded px-2 py-1 text-xs focus:ring-1 focus:ring-primary-400" />
                </td>
                <td class="px-3 py-2 text-right">
                  <input type="number" step="0.01" bind:value={row.betrag_brutto} placeholder="0,00" class="w-24 text-right {pfInputCls(`hk:${row.kategorie}`)}" />
                  <div class="text-xs text-blue-400 mt-0.5">{fmtRef(refHN(i,'betrag_brutto'))} €</div>
                </td>
                <td class="px-3 py-2 text-right">
                  <input type="number" step="0.01" bind:value={row.gesamtbetrag} placeholder="—" class="w-24 border rounded px-2 py-1 text-xs text-right focus:ring-1 focus:ring-primary-400" />
                  <div class="text-xs text-blue-400 mt-0.5">{fmtRef(refHN(i,'gesamtbetrag'))}</div>
                </td>
                <td class="px-3 py-2 text-right">
                  <input type="number" step="0.01" bind:value={row.anteil_arbeitskosten} placeholder="—" class="w-24 border rounded px-2 py-1 text-xs text-right focus:ring-1 focus:ring-primary-400" />
                  <div class="text-xs text-blue-400 mt-0.5">{fmtRef(refHN(i,'anteil_arbeitskosten'))}</div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>

  </div>
  {/if}

  <!-- ── Bottom save bar ── -->
  <div class="mt-6 flex justify-end gap-3">
    {#if error}
      <span class="text-sm text-red-600">{error}</span>
    {/if}
    <button
      on:click={save}
      disabled={saving}
      class="px-6 py-2 text-sm font-medium rounded-lg transition-colors
        {saved ? 'bg-green-600 text-white' : 'bg-primary-600 hover:bg-primary-700 text-white disabled:opacity-50'}"
    >
      {#if saving}Speichern…{:else if saved}✓ Daten gespeichert{:else}💾 Daten speichern{/if}
    </button>
  </div>

  {/if}
</div>
