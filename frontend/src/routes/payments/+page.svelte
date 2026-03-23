<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { formatEur, formatDate, monthName } from '$lib/format.js';

  let year = new Date().getFullYear();
  let paymentData = [];
  let loading = true;
  let error = null;
  let expandedBka = {};   // { unit_id: true/false }

  async function load() {
    loading = true;
    error = null;
    try {
      paymentData = await api.getPaymentStatus(year);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  onMount(load);
  $: if (year) load();

  function toggleBka(unit) {
    expandedBka = { ...expandedBka, [unit]: !expandedBka[unit] };
  }

  // ── Status helpers ────────────────────────────────────────────────────────
  function cellBg(status) {
    return {
      ok:      'bg-green-100 text-green-800 border-green-200',
      shifted: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      prepaid: 'bg-blue-100 text-blue-800 border-blue-200',
      missing: 'bg-red-100 text-red-600 border-red-200',
    }[status] || 'bg-gray-100 text-gray-500';
  }

  function cellIcon(status) {
    return { ok: '✓', shifted: '↻', prepaid: '↑', missing: '✗' }[status] || '?';
  }

  function cellTitle(month) {
    if (month.status === 'ok') return `Bezahlt am ${month.date || ''}`;
    if (month.status === 'shifted') return `Verspätet: ${month.shift_days} Tage nach dem 1. (${month.date || ''})`;
    if (month.status === 'prepaid') return `Vorauszahlung: ${Math.abs(month.shift_days)} Tage vor dem 1.`;
    return 'Nicht bezahlt';
  }

  function bkaTypeLabel(type) {
    return type === 'bka' ? 'BKA' : 'Überschuss';
  }
  function bkaTypeBadge(type) {
    return type === 'bka'
      ? 'bg-orange-100 text-orange-700'
      : 'bg-purple-100 text-purple-700';
  }

  $: allYears = [...new Set(
    paymentData.flatMap(o => (o.bka_payments || []).map(b => b.year_ref))
  )].sort();
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between flex-wrap gap-3">
    <h2 class="text-2xl font-bold">Hausgeld-Kontrolle</h2>
    <div class="flex items-center gap-3">
      <select bind:value={year} on:change={load} class="border rounded-lg px-3 py-1.5 text-sm">
        {#each [2024, 2025, 2026] as y}<option value={y}>{y}</option>{/each}
      </select>
    </div>
  </div>

  <!-- Legend -->
  <div class="flex gap-3 flex-wrap text-xs">
    <span class="flex items-center gap-1"><span class="w-5 h-5 rounded flex items-center justify-center bg-green-100 text-green-800 font-bold">✓</span> Pünktlich</span>
    <span class="flex items-center gap-1"><span class="w-5 h-5 rounded flex items-center justify-center bg-yellow-100 text-yellow-800 font-bold">↻</span> Verschoben (kam im Folgemonat an)</span>
    <span class="flex items-center gap-1"><span class="w-5 h-5 rounded flex items-center justify-center bg-blue-100 text-blue-800 font-bold">↑</span> Vorauszahlung</span>
    <span class="flex items-center gap-1"><span class="w-5 h-5 rounded flex items-center justify-center bg-red-100 text-red-600 font-bold">✗</span> Fehlend</span>
  </div>

  {#if loading}
    <div class="text-gray-500 text-center py-12 animate-pulse">Lade…</div>
  {:else if error}
    <div class="bg-red-50 text-red-700 rounded-xl p-4">Fehler: {error}</div>
  {:else}
    <!-- ── Per-owner cards ─────────────────────────────────────────────────── -->
    <div class="grid gap-5">
      {#each paymentData as owner}
        {@const sc = owner.status_counts || {}}
        {@const hasBka = owner.bka_payments && owner.bka_payments.length > 0}

        <div class="card overflow-hidden">
          <!-- Owner header -->
          <div class="flex flex-wrap justify-between items-start gap-2 mb-4">
            <div class="flex items-center gap-3 flex-wrap">
              <span class="font-mono font-bold text-primary-700 bg-primary-50 px-2 py-1 rounded">
                {owner.unit_id}
              </span>
              <span class="font-semibold text-gray-800 text-lg">{owner.name}</span>
              <span class="text-sm text-gray-400">{formatEur(owner.monthly_expected)}/Monat</span>
            </div>
            <div class="flex flex-col items-end text-sm gap-0.5">
              <div>
                <span class="text-gray-500">Regulär:</span>
                <span class="font-semibold ml-1">{formatEur(owner.total_regular_paid)}</span>
                <span class="text-gray-400 mx-1">/</span>
                <span class="text-gray-500">{formatEur(owner.total_expected)}</span>
              </div>
              {#if owner.total_bka_paid > 0}
                <div class="text-orange-600">
                  <span>BKA/Sonder:</span>
                  <span class="font-semibold ml-1">+{formatEur(owner.total_bka_paid)}</span>
                </div>
              {/if}
              <div class="font-bold text-base {owner.balance >= 0 ? 'text-green-600' : 'text-red-600'}">
                Saldo: {owner.balance >= 0 ? '+' : ''}{formatEur(owner.balance)}
              </div>
            </div>
          </div>

          <!-- Status summary pills -->
          <div class="flex gap-2 mb-3 flex-wrap">
            {#if sc.ok > 0}
              <span class="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">{sc.ok}× pünktlich</span>
            {/if}
            {#if sc.shifted > 0}
              <span class="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700">{sc.shifted}× verschoben</span>
            {/if}
            {#if sc.prepaid > 0}
              <span class="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">{sc.prepaid}× vorab</span>
            {/if}
            {#if sc.missing > 0}
              <span class="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700">{sc.missing}× fehlend</span>
            {/if}
          </div>

          <!-- Monthly grid -->
          <div class="grid grid-cols-6 gap-1.5 sm:grid-cols-12">
            {#each owner.months as month}
              <div class="flex flex-col items-center" title={cellTitle(month)}>
                <span class="text-[10px] text-gray-400 mb-0.5">{monthName(month.month)}</span>
                <div class="w-full aspect-square flex flex-col items-center justify-center rounded border text-xs font-bold cursor-default {cellBg(month.status)}">
                  <span>{cellIcon(month.status)}</span>
                  {#if month.status === 'shifted'}
                    <span class="text-[9px] font-normal leading-tight">+{month.shift_days}d</span>
                  {/if}
                </div>
                {#if month.paid > 0}
                  <span class="text-[9px] text-gray-400 mt-0.5 leading-none">{formatEur(month.paid).replace('€','').trim()}</span>
                {/if}
              </div>
            {/each}
          </div>

          <!-- BKA section (collapsible) -->
          {#if hasBka}
            <div class="mt-4 border-t pt-3">
              <button
                class="flex items-center gap-2 text-sm font-semibold text-orange-700 hover:text-orange-800 w-full text-left"
                on:click={() => toggleBka(owner.unit_id)}
              >
                <span class="text-base">{expandedBka[owner.unit_id] ? '▾' : '▸'}</span>
                BKA / Sonderzahlungen
                <span class="ml-1 text-xs font-normal text-orange-500">
                  ({owner.bka_payments.length} Einträge, {formatEur(owner.total_bka_paid)} gesamt)
                </span>
              </button>

              {#if expandedBka[owner.unit_id]}
                <div class="mt-3 overflow-x-auto">
                  <table class="w-full text-sm">
                    <thead class="text-xs text-gray-500 border-b">
                      <tr>
                        <th class="text-left py-1.5 pr-4 font-medium">Datum</th>
                        <th class="text-left py-1.5 pr-4 font-medium">Betrag</th>
                        <th class="text-left py-1.5 pr-4 font-medium">Art</th>
                        <th class="text-left py-1.5 pr-4 font-medium">Bezugsjahr</th>
                        <th class="text-left py-1.5 font-medium">Verwendungszweck</th>
                      </tr>
                    </thead>
                    <tbody>
                      {#each owner.bka_payments as bka}
                        <tr class="border-b last:border-0 hover:bg-gray-50 {bka.cross_year ? 'bg-orange-50' : ''}">
                          <td class="py-2 pr-4 text-gray-500 text-xs whitespace-nowrap">
                            {formatDate(bka.date)}
                          </td>
                          <td class="py-2 pr-4 font-semibold {bka.amount >= 0 ? 'text-green-600' : 'text-red-600'} whitespace-nowrap">
                            {formatEur(bka.amount)}
                          </td>
                          <td class="py-2 pr-4">
                            <span class="text-xs px-1.5 py-0.5 rounded-full {bkaTypeBadge(bka.type)}">
                              {bkaTypeLabel(bka.type)}
                            </span>
                          </td>
                          <td class="py-2 pr-4">
                            <span class="text-xs font-mono {bka.cross_year ? 'text-orange-600 font-bold' : 'text-gray-500'}">
                              {bka.year_ref}
                              {#if bka.cross_year}
                                <span class="ml-1 text-[10px]" title="Jahresübergreifende Abrechnung">⚠</span>
                              {/if}
                            </span>
                          </td>
                          <td class="py-2 text-xs text-gray-600 max-w-xs truncate" title={bka.purpose}>
                            {bka.purpose || '–'}
                          </td>
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              {/if}
            </div>
          {/if}
        </div>
      {/each}
    </div>

    <!-- ── Cross-year BKA summary ──────────────────────────────────────────── -->
    {@const crossYearAll = paymentData.flatMap(o =>
      (o.bka_payments || [])
        .filter(b => b.cross_year)
        .map(b => ({ ...b, unit_id: o.unit_id, name: o.name }))
    )}
    {#if crossYearAll.length > 0}
      <div class="card border-orange-200 bg-orange-50">
        <h3 class="font-semibold text-orange-800 mb-3">⚠ Jahresübergreifende Abrechnungen</h3>
        <p class="text-xs text-orange-700 mb-3">
          Diese Zahlungen wurden im Jahr {year} eingezogen, beziehen sich aber auf ein anderes Abrechnungsjahr.
        </p>
        <table class="w-full text-sm">
          <thead class="text-xs text-orange-600 border-b border-orange-200">
            <tr>
              <th class="text-left py-1.5 pr-4 font-medium">Eigentümer</th>
              <th class="text-left py-1.5 pr-4 font-medium">Datum</th>
              <th class="text-left py-1.5 pr-4 font-medium">Bezugsjahr</th>
              <th class="text-right py-1.5 font-medium">Betrag</th>
            </tr>
          </thead>
          <tbody>
            {#each crossYearAll as bka}
              <tr class="border-b border-orange-100 last:border-0">
                <td class="py-2 pr-4">
                  <span class="font-mono text-xs text-primary-700">{bka.unit_id}</span>
                  <span class="ml-2 text-gray-700">{bka.name}</span>
                </td>
                <td class="py-2 pr-4 text-xs text-gray-500">{formatDate(bka.date)}</td>
                <td class="py-2 pr-4">
                  <span class="text-xs font-bold text-orange-700">{bka.year_ref}</span>
                </td>
                <td class="py-2 text-right font-semibold {bka.amount >= 0 ? 'text-green-600' : 'text-red-600'}">
                  {formatEur(bka.amount)}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  {/if}
</div>

