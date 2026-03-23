<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { formatEur, formatDate } from '$lib/format.js';

  let year = new Date().getFullYear();
  let expenses = [];
  let income = null;
  let loading = true;
  let error = null;
  let expandedOther = false;

  async function load() {
    loading = true;
    error = null;
    try {
      [expenses, income] = await Promise.all([
        api.getExpenses(year),
        api.getIncome(year),
      ]);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  onMount(load);
  $: if (year) load();

  $: totalExpenses = expenses.reduce((s, e) => s + e.total, 0);

  // Group expenses by normalized category, sort within each group by total ascending
  $: grouped = (() => {
    const acc = {};
    for (const e of expenses) {
      const cat = e.category || 'Sonstiges';
      if (!acc[cat]) acc[cat] = { total: 0, items: [] };
      acc[cat].total += e.total;
      acc[cat].items.push(e);
    }
    // Sort items within each group
    for (const g of Object.values(acc)) {
      g.items.sort((a, b) => a.total - b.total);
    }
    return acc;
  })();

  // Category icon map
  const catIcon = {
    'Strom':             '⚡',
    'Versicherung':      '🛡️',
    'Wasser':            '💧',
    'Abwasser/Kanal':    '🚰',
    'Heizung':           '🔥',
    'Hausverwaltung':    '🏢',
    'Rücklage':          '🏦',
    'Bankgebühren':      '💳',
    'Instandhaltung':    '🔧',
    'Steuer/Finanzamt':  '🏛️',
    'Sonstiges':         '📋',
  };

  // Sort categories by absolute total (largest first)
  $: sortedCategories = Object.entries(grouped).sort(([, a], [, b]) => a.total - b.total);
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between flex-wrap gap-3">
    <h2 class="text-2xl font-bold">Einnahmen & Ausgaben</h2>
    <select bind:value={year} on:change={load} class="border rounded-lg px-3 py-1.5 text-sm">
      {#each [2024, 2025, 2026] as y}<option value={y}>{y}</option>{/each}
    </select>
  </div>

  {#if loading}
    <div class="text-gray-500 text-center py-12 animate-pulse">Lade…</div>
  {:else if error}
    <div class="bg-red-50 text-red-700 rounded-xl p-4">Fehler: {error}</div>
  {:else}

    <!-- ── Gesamtübersicht ─────────────────────────────────────────────────── -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="card bg-green-50 border-green-200">
        <p class="text-xs font-medium text-green-600 uppercase tracking-wide mb-1">Einnahmen {year}</p>
        <p class="text-2xl font-bold text-green-700">{formatEur(income?.totals?.total ?? 0)}</p>
        <p class="text-xs text-green-500 mt-1">
          Hausgeld {formatEur(income?.totals?.regular ?? 0)}
          {#if (income?.totals?.bka ?? 0) > 0}
            + BKA {formatEur(income.totals.bka)}
          {/if}
        </p>
      </div>
      <div class="card bg-red-50 border-red-200">
        <p class="text-xs font-medium text-red-600 uppercase tracking-wide mb-1">Ausgaben {year}</p>
        <p class="text-2xl font-bold text-red-700">{formatEur(totalExpenses)}</p>
        <p class="text-xs text-red-400 mt-1">{expenses.length} Positionen</p>
      </div>
      <div class="card {(income?.totals?.total ?? 0) + totalExpenses >= 0 ? 'bg-blue-50 border-blue-200' : 'bg-orange-50 border-orange-200'}">
        <p class="text-xs font-medium {(income?.totals?.total ?? 0) + totalExpenses >= 0 ? 'text-blue-600' : 'text-orange-600'} uppercase tracking-wide mb-1">Saldo {year}</p>
        <p class="text-2xl font-bold {(income?.totals?.total ?? 0) + totalExpenses >= 0 ? 'text-blue-700' : 'text-orange-700'}">
          {formatEur((income?.totals?.total ?? 0) + totalExpenses)}
        </p>
      </div>
    </div>

    <!-- ── Einnahmen ───────────────────────────────────────────────────────── -->
    {#if income}
      <div class="card">
        <h3 class="font-semibold text-gray-700 mb-4">💰 Einnahmen {year}</h3>

        <!-- Reguläres Hausgeld pro Eigentümer -->
        <h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Reguläres Hausgeld</h4>
        <table class="w-full text-sm mb-4">
          <thead class="text-xs text-gray-400 border-b">
            <tr>
              <th class="text-left py-1.5 pr-4 font-medium">Einheit</th>
              <th class="text-left py-1.5 pr-4 font-medium">Eigentümer</th>
              <th class="text-right py-1.5 pr-3 font-medium">Zahlungen</th>
              <th class="text-right py-1.5 font-medium">Betrag</th>
            </tr>
          </thead>
          <tbody>
            {#each income.by_owner as o}
              <tr class="border-b last:border-0 hover:bg-gray-50">
                <td class="py-2 pr-4">
                  <span class="font-mono text-xs text-primary-700 bg-primary-50 px-1.5 py-0.5 rounded">{o.unit_id}</span>
                </td>
                <td class="py-2 pr-4 text-gray-700">{o.name}</td>
                <td class="py-2 pr-3 text-right text-gray-400 text-xs">{o.count}×</td>
                <td class="py-2 text-right font-semibold text-green-600">{formatEur(o.total)}</td>
              </tr>
            {/each}
            <tr class="border-t-2 border-green-200 bg-green-50">
              <td colspan="3" class="py-2 pr-3 text-sm font-semibold text-green-700">Summe Hausgeld</td>
              <td class="py-2 text-right font-bold text-green-700">{formatEur(income.totals.regular)}</td>
            </tr>
          </tbody>
        </table>

        <!-- BKA / Nachzahlungen -->
        {#if income.bka.length > 0}
          <h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 mt-4">BKA / Nachzahlungen</h4>
          <table class="w-full text-sm mb-4">
            <thead class="text-xs text-gray-400 border-b">
              <tr>
                <th class="text-left py-1.5 pr-4 font-medium">Datum</th>
                <th class="text-left py-1.5 pr-4 font-medium">Einheit</th>
                <th class="text-left py-1.5 pr-4 font-medium">Verwendungszweck</th>
                <th class="text-right py-1.5 font-medium">Betrag</th>
              </tr>
            </thead>
            <tbody>
              {#each income.bka as b}
                <tr class="border-b last:border-0 hover:bg-gray-50">
                  <td class="py-2 pr-4 text-xs text-gray-400">{formatDate(b.date)}</td>
                  <td class="py-2 pr-4">
                    <span class="font-mono text-xs text-primary-700 bg-primary-50 px-1.5 py-0.5 rounded">{b.unit_id}</span>
                  </td>
                  <td class="py-2 pr-4 text-xs text-gray-600 max-w-sm truncate" title={b.purpose}>{b.purpose || '–'}</td>
                  <td class="py-2 text-right font-semibold text-green-600">{formatEur(b.amount)}</td>
                </tr>
              {/each}
              <tr class="border-t-2 border-orange-200 bg-orange-50">
                <td colspan="3" class="py-2 pr-3 text-sm font-semibold text-orange-700">Summe BKA</td>
                <td class="py-2 text-right font-bold text-orange-700">{formatEur(income.totals.bka)}</td>
              </tr>
            </tbody>
          </table>
        {/if}

        <!-- Sonstige Eingänge (collapsible) -->
        {#if income.other.length > 0}
          <button
            class="text-xs font-semibold text-gray-500 hover:text-gray-700 flex items-center gap-1 mt-2"
            on:click={() => expandedOther = !expandedOther}
          >
            {expandedOther ? '▾' : '▸'} Sonstige Eingänge ({income.other.length})
            <span class="font-normal ml-1 text-gray-400">{formatEur(income.totals.other)}</span>
          </button>
          {#if expandedOther}
            <table class="w-full text-sm mt-2">
              <tbody>
                {#each income.other as o}
                  <tr class="border-b last:border-0 hover:bg-gray-50">
                    <td class="py-1.5 pr-4 text-xs text-gray-400">{formatDate(o.date)}</td>
                    <td class="py-1.5 pr-4 text-gray-700 text-xs">{o.counterparty || '–'}</td>
                    <td class="py-1.5 text-xs text-gray-500 truncate max-w-xs" title={o.purpose}>{o.purpose || '–'}</td>
                    <td class="py-1.5 text-right text-green-600 font-medium">{formatEur(o.amount)}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          {/if}
        {/if}
      </div>
    {/if}

    <!-- ── Ausgaben nach Kategorie ─────────────────────────────────────────── -->
    <h3 class="text-lg font-semibold text-gray-700 mt-2">📊 Ausgaben nach Kategorie</h3>

    {#each sortedCategories as [cat, group]}
      <div class="card">
        <div class="flex justify-between items-center mb-3">
          <h4 class="font-semibold text-gray-700 flex items-center gap-2">
            <span>{catIcon[cat] || '📋'}</span>
            <span>{cat}</span>
          </h4>
          <span class="font-bold text-red-600">{formatEur(group.total)}</span>
        </div>
        <table class="w-full text-sm">
          <tbody>
            {#each group.items as item}
              <tr class="border-t first:border-0 hover:bg-gray-50">
                <td class="py-1.5 pr-4 text-gray-700">{item.counterparty || '–'}</td>
                <td class="py-1.5 pr-3 text-right text-gray-400 text-xs">{item.count}×</td>
                <td class="py-1.5 text-right font-medium text-red-600">{formatEur(item.total)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/each}
  {/if}
</div>
