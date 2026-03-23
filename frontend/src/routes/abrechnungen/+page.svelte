<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { formatDate } from '$lib/format.js';

  let year = 2025;
  let data = null;
  let loading = false;
  let error = null;
  let saving = false;
  let savedMsg = '';

  // Editable state (2025 only)
  let bka1Ges = '';
  let bka1Inputs = {}; // { 'WE-001': '1.560,46', ... }

  $: if (year) loadData();

  async function loadData() {
    loading = true;
    error = null;
    try {
      data = await api.getAbrechnung(year);
      initInputs();
    } catch (e) {
      error = e.message;
    }
    loading = false;
  }

  function initInputs() {
    if (!data) return;
    bka1Ges = data.bka1_ges_betrag != null ? toDE(data.bka1_ges_betrag) : '';
    bka1Inputs = {};
    for (const o of data.owners) {
      bka1Inputs[o.unit_id] = o.bka1_betrag_ant != null ? toDE(o.bka1_betrag_ant) : '';
    }
  }

  function parseDE(s) {
    if (!s && s !== 0) return null;
    const n = parseFloat(String(s).replace(/\./g, '').replace(',', '.'));
    return isNaN(n) ? null : n;
  }

  function toDE(v) {
    if (v == null) return '';
    return v.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function fmt(v) {
    if (v == null) return null;
    return v.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €';
  }

  function fmtMEA(v) {
    if (v == null) return '—';
    return v.toLocaleString('de-DE', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
  }

  function getBka1Ant(owner) {
    if (year !== 2025) return owner.bka1_betrag_ant;
    return parseDE(bka1Inputs[owner.unit_id]);
  }

  function getBka1Ges() {
    if (year !== 2025) return data ? data.bka1_ges_betrag : null;
    return parseDE(bka1Ges);
  }

  function computeGesamt(owner) {
    const bka1 = getBka1Ant(owner);
    if (bka1 === null) return null;
    return Math.round((owner.fixed_ant + bka1) * 100) / 100;
  }

  function computeNachzahlung(owner) {
    const g = computeGesamt(owner);
    if (g === null) return null;
    return Math.round((g - owner.vorauszahlung) * 100) / 100;
  }

  $: allComplete = data?.owners?.every(o => getBka1Ant(o) !== null) && getBka1Ges() !== null;

  function updateBka1Input(unitId, value) {
    bka1Inputs = { ...bka1Inputs, [unitId]: value };
  }

  async function save() {
    saving = true;
    savedMsg = '';
    try {
      const ownerBka1 = {};
      for (const [k, v] of Object.entries(bka1Inputs)) {
        const n = parseDE(v);
        if (n !== null) ownerBka1[k] = n;
      }
      data = await api.updateAbrechnung(year, {
        bka1_ges_betrag: parseDE(bka1Ges),
        owner_bka1: ownerBka1,
      });
      initInputs();
      savedMsg = '✓';
    } catch (e) {
      savedMsg = '✗ ' + e.message;
    }
    saving = false;
    setTimeout(() => (savedMsg = ''), 3000);
  }

  onMount(() => loadData());

  // Account balances (hardcoded from confirmed bank statements)
  const BALANCES = {
    2024: { giro_start: '3.527,48', giro_end: '3.333,80', rl_start: '8.067,85', rl_end: '10.281,93' },
    2025: { giro_start: '3.333,80', giro_end: '3.970,48', rl_start: '10.281,93',rl_end: '12.677,11' },
  };
</script>

<div class="p-6 max-w-7xl mx-auto space-y-5">

  <!-- ── Header ── -->
  <div class="flex flex-wrap items-center justify-between gap-4">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">📄 Jahresabrechnung</h1>
      <p class="text-sm text-gray-500 mt-0.5">WEG Tulpenstr. 31, Hilgertshausen-Tandern</p>
    </div>
    <div class="flex items-center gap-3">
      <!-- Year tabs -->
      <div class="flex rounded-lg border border-gray-200 overflow-hidden text-sm">
        {#each [2024, 2025] as y}
          <button
            class="px-5 py-2 font-medium transition-colors
              {year === y ? 'bg-primary-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}"
            on:click={() => { year = y; }}>
            {y}
            {#if y === 2024}<span class="ml-1 text-xs opacity-60">✓</span>{/if}
            {#if y === 2025 && !allComplete}<span class="ml-1 text-xs opacity-60">⏳</span>{/if}
          </button>
        {/each}
      </div>

      {#if year === 2025}
        <button
          on:click={save}
          disabled={saving}
          class="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium
                 hover:bg-primary-700 disabled:opacity-50 transition-colors">
          {saving ? '⏳ Speichere…' : '💾 Speichern'}
        </button>
        {#if savedMsg}
          <span class="text-sm font-medium {savedMsg.startsWith('✓') ? 'text-green-600' : 'text-red-600'}">{savedMsg}</span>
        {/if}
      {/if}
    </div>
  </div>

  {#if loading}
    <div class="text-center text-gray-400 py-20">Lade Daten…</div>

  {:else if error}
    <div class="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl">{error}</div>

  {:else if data}

    <!-- ── Status-Banner ── -->
    <div class="flex items-start gap-3 p-4 rounded-xl
      {allComplete ? 'bg-green-50 border border-green-200' : 'bg-amber-50 border border-amber-200'}">
      <span class="text-xl mt-0.5">{allComplete ? '✅' : '⏳'}</span>
      <div>
        <p class="font-semibold {allComplete ? 'text-green-800' : 'text-amber-800'}">
          Abrechnung {year} {allComplete ? 'vollständig' : '— BKA-1 ausstehend'}
        </p>
        {#if !allComplete && year === 2025}
          <p class="text-sm text-amber-700 mt-0.5">
            Bitte die Werte aus der Heiz- und Nebenkostenabrechnung der Fa. Witter eintragen.
          </p>
        {/if}
      </div>
    </div>

    <!-- ── Bekannte Gemeinschaftskosten + BKA-1-Gesamtbetrag ── -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <h2 class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">
        Gemeinschaftskosten {year}
      </h2>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-5">
        {#each [
          ['Rücklagen', data.kosten.ruecklagen],
          ['Hausverwaltung (Witter)', data.kosten.witter],
          ['Kontogebühren', data.kosten.kontogebuehren],
          ['Instandhaltung Objekt', data.kosten.instandhaltung],
        ] as [label, val]}
          <div class="bg-gray-50 rounded-lg p-3">
            <p class="text-xs text-gray-500 leading-tight">{label}</p>
            <p class="text-base font-semibold text-gray-900 mt-1 font-mono">{fmt(val)}</p>
          </div>
        {/each}
      </div>

      <!-- BKA-1 Gesamtbetrag (shared across all owners, from Witter) -->
      <div class="flex items-center gap-3 pt-4 border-t border-gray-100">
        <div class="flex-1">
          <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider">
            Gesamtkosten Betriebskostenabrechnung 1 (Witter Kurzübersicht)
          </p>
          <p class="text-xs text-gray-400 mt-0.5">
            Pos. 1 aus der Witter Heiz- und Nebenkostenabrechnung (selber Betrag für alle Einheiten)
          </p>
        </div>
        {#if year === 2025}
          <div class="flex items-center gap-2">
            <input
              type="text"
              value={bka1Ges}
              on:input={(e) => { bka1Ges = e.currentTarget.value; }}
              placeholder="z.B. 9.025,69"
              class="w-36 border {bka1Ges ? 'border-green-300 bg-green-50' : 'border-amber-300 bg-amber-50'}
                     rounded-lg px-3 py-1.5 text-sm font-mono text-right
                     focus:ring-2 focus:ring-primary-500 focus:border-transparent" />
            <span class="text-sm text-gray-400">€</span>
          </div>
        {:else}
          <span class="text-base font-semibold font-mono text-gray-900">{fmt(data.bka1_ges_betrag)}</span>
        {/if}
      </div>
    </div>

    <!-- ── Pro-Eigentümer-Karten ── -->
    {#each data.owners as owner (owner.unit_id)}
      {@const bka1_ant = getBka1Ant(owner)}
      {@const gesamt = computeGesamt(owner)}
      {@const nachzahlung = computeNachzahlung(owner)}
      {@const isComplete = bka1_ant !== null}

      <div class="bg-white rounded-xl shadow-sm border {isComplete ? 'border-green-200' : year === 2025 ? 'border-amber-200' : 'border-gray-100'} overflow-hidden">

        <!-- Card header -->
        <div class="flex items-center justify-between px-5 py-3 border-b border-gray-100
                    {isComplete ? 'bg-green-50' : year === 2025 ? 'bg-amber-50' : 'bg-gray-50'}">
          <div class="flex items-center gap-3">
            <span class="text-sm font-bold text-primary-700 bg-white border border-primary-200 rounded-md px-2.5 py-1">
              {owner.unit_id}
            </span>
            <div>
              <p class="font-semibold text-gray-900">{owner.name}</p>
              <p class="text-xs text-gray-500">{owner.address1} · {owner.city} · MEA {fmtMEA(owner.mea)}/1000</p>
            </div>
          </div>
          <div class="text-right">
            {#if isComplete}
              {@const nzs = owner.nachzahlung_status}
              {#if nzs?.status === 'paid_late'}
                <span class="text-xs font-medium text-orange-700 bg-orange-100 border border-orange-200 rounded-full px-3 py-1">⚠ Nachzahlung verspätet</span>
              {:else if nzs?.status === 'pending' && (computeNachzahlung(owner) || 0) > 0}
                <span class="text-xs font-medium text-red-700 bg-red-100 rounded-full px-3 py-1">✗ Nachzahlung ausstehend</span>
              {:else if nzs?.status === 'refund_pending'}
                <span class="text-xs font-medium text-red-700 bg-red-100 rounded-full px-3 py-1">✗ Rückzahlung ausstehend</span>
              {:else if nzs?.status === 'refunded_late'}
                <span class="text-xs font-medium text-orange-700 bg-orange-100 border border-orange-200 rounded-full px-3 py-1">⚠ Rückzahlung verspätet</span>
              {:else}
                <span class="text-xs font-medium text-green-700 bg-green-100 rounded-full px-3 py-1">✓ vollständig</span>
              {/if}
            {:else if year === 2025}
              <span class="text-xs font-medium text-amber-700 bg-amber-100 rounded-full px-3 py-1">⏳ BKA-1 fehlt</span>
            {/if}
          </div>
        </div>

        <!-- Abrechnung table -->
        <div class="px-5 py-4">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-xs text-gray-400 border-b border-gray-100">
                <th class="text-left pb-2 font-medium">Kostenkonto</th>
                <th class="text-left pb-2 font-medium hidden sm:table-cell">Umlageart</th>
                <th class="text-right pb-2 font-medium hidden md:table-cell">Umlage anteilig</th>
                <th class="text-right pb-2 font-medium">Ges. Betrag</th>
                <th class="text-right pb-2 font-medium">Betrag ant.</th>
              </tr>
            </thead>
            <tbody>
              {#each owner.positionen as pos}
                {@const isBka1 = pos.editable}
                <tr class="border-b border-gray-50 {isBka1 && !isComplete ? 'bg-amber-50/60' : ''}">
                  <td class="py-2 pr-3 text-xs font-medium text-gray-800 leading-snug">{pos.kostenkonto}</td>
                  <td class="py-2 pr-3 text-xs text-gray-400 hidden sm:table-cell">{pos.umlageart}</td>
                  <td class="py-2 pr-3 text-right font-mono text-xs text-gray-500 hidden md:table-cell">
                    {pos.umlage_anteilig != null ? fmtMEA(pos.umlage_anteilig) : '—'}
                  </td>

                  <!-- Ges. Betrag -->
                  <td class="py-2 pr-3 text-right font-mono text-xs">
                    {#if isBka1}
                      {#if getBka1Ges() != null}
                        <span class="text-gray-700">{fmt(getBka1Ges())}</span>
                      {:else}
                        <span class="text-amber-400 text-xs">—</span>
                      {/if}
                    {:else}
                      {fmt(pos.ges_betrag)}
                    {/if}
                  </td>

                  <!-- Betrag anteilig -->
                  <td class="py-2 text-right font-mono text-sm">
                    {#if isBka1 && year === 2025}
                      <input
                        type="text"
                        value={bka1Inputs[owner.unit_id]}
                        on:input={(e) => updateBka1Input(owner.unit_id, e.currentTarget.value)}
                        placeholder="0,00"
                        class="w-28 border {bka1Inputs[owner.unit_id] ? 'border-green-300 bg-green-50' : 'border-amber-300 bg-amber-50'}
                               rounded px-2 py-1 text-xs font-mono text-right
                               focus:ring-2 focus:ring-primary-500 focus:border-transparent" />
                    {:else}
                      <span class="{pos.betrag_ant != null ? 'text-gray-900 font-medium' : 'text-amber-400'}">
                        {fmt(pos.betrag_ant) ?? '—'}
                      </span>
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>

          <!-- Summary: Gesamt / Vorauszahlung / Ergebnis -->
          <div class="mt-4 pt-4 border-t border-gray-200 flex justify-end">
            <table class="text-sm w-72">
              <tr class="font-semibold">
                <td class="py-1.5 pr-6 text-gray-700">Gesamt</td>
                <td class="py-1.5 text-right font-mono">
                  {#if gesamt != null}
                    <span class="text-gray-900">{fmt(gesamt)}</span>
                  {:else}
                    <span class="text-amber-400 font-normal text-xs">ausstehend</span>
                  {/if}
                </td>
              </tr>
              <tr class="text-gray-500">
                <td class="py-1 pr-6">Abzügl. Vorauszahlung</td>
                <td class="py-1 text-right font-mono">−{fmt(owner.vorauszahlung)}</td>
              </tr>
              <tr class="border-t border-gray-200">
                <td class="pt-2 pr-6 font-bold {nachzahlung != null ? (nachzahlung >= 0 ? 'text-red-700' : 'text-green-700') : 'text-gray-600'}">
                  {#if nachzahlung != null}
                    {nachzahlung >= 0 ? 'Nachzahlung' : 'Rückzahlung'}
                  {:else}
                    Ergebnis
                  {/if}
                </td>
                <td class="pt-2 text-right font-mono font-bold text-base
                           {nachzahlung != null ? (nachzahlung >= 0 ? 'text-red-700' : 'text-green-700') : 'text-gray-300'}">
                  {#if nachzahlung != null}
                    {fmt(Math.abs(nachzahlung))}
                  {:else}
                    <span class="font-normal text-xs text-amber-400">ausstehend</span>
                  {/if}
                </td>
              </tr>
              {#if owner.nachzahlung_status && nachzahlung !== null && nachzahlung !== 0}
                <tr>
                  <td colspan="2" class="pt-2 text-right">
                    {#if owner.nachzahlung_status.status === 'paid'}
                      <span class="text-xs bg-green-100 text-green-700 rounded-full px-2 py-0.5">✓ Eingegangen {formatDate(owner.nachzahlung_status.date)}</span>
                    {:else if owner.nachzahlung_status.status === 'paid_late'}
                      <span class="text-xs bg-orange-100 text-orange-700 border border-orange-200 rounded-full px-2 py-0.5">⚠ Jahresübergreifend &ndash; eingegangen {formatDate(owner.nachzahlung_status.date)}</span>
                    {:else if owner.nachzahlung_status.status === 'pending'}
                      <span class="text-xs bg-red-100 text-red-600 rounded-full px-2 py-0.5">✗ Ausstehend</span>
                    {:else if owner.nachzahlung_status.status === 'refunded'}
                      <span class="text-xs bg-green-100 text-green-700 rounded-full px-2 py-0.5">✓ Überwiesen {formatDate(owner.nachzahlung_status.date)}</span>
                    {:else if owner.nachzahlung_status.status === 'refunded_late'}
                      <span class="text-xs bg-orange-100 text-orange-700 border border-orange-200 rounded-full px-2 py-0.5">⚠ Jahresübergreifend &ndash; überwiesen {formatDate(owner.nachzahlung_status.date)}</span>
                    {:else if owner.nachzahlung_status.status === 'refund_pending'}
                      <span class="text-xs bg-red-100 text-red-600 rounded-full px-2 py-0.5">✗ Noch nicht überwiesen</span>
                    {/if}
                  </td>
                </tr>
              {/if}
            </table>
          </div>
        </div>
      </div>
    {/each}

    <!-- ── Kontenentwicklung ── -->
    {#if BALANCES[year]}
      {@const b = BALANCES[year]}
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <h2 class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Kontenentwicklung {year}
        </h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-6 text-sm">
          <div>
            <p class="text-xs font-medium text-gray-500 mb-2">Girokonto (6023543)</p>
            <div class="space-y-1">
              <div class="flex justify-between">
                <span class="text-gray-600">01.01.{year}</span>
                <span class="font-mono text-gray-800">{b.giro_start} €</span>
              </div>
              <div class="flex justify-between font-medium">
                <span class="text-gray-600">31.12.{year}</span>
                <span class="font-mono text-gray-900">{b.giro_end} €</span>
              </div>
            </div>
          </div>
          <div>
            <p class="text-xs font-medium text-gray-500 mb-2">Rücklagenkonto (6023550)</p>
            <div class="space-y-1">
              <div class="flex justify-between">
                <span class="text-gray-600">01.01.{year}</span>
                <span class="font-mono text-gray-800">{b.rl_start} €</span>
              </div>
              <div class="flex justify-between font-medium">
                <span class="text-gray-600">31.12.{year}</span>
                <span class="font-mono text-gray-900">{b.rl_end} €</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    {/if}

  {/if}
</div>
