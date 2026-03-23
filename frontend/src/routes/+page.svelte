<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { formatEur, formatDate } from '$lib/format.js';

  let year = new Date().getFullYear();
  let dashboard = null;
  let error = null;
  let loading = true;

  async function load() {
    loading = true;
    error = null;
    try {
      dashboard = await api.getDashboard(year);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  onMount(load);

  $: if (year) load();

  function txColor(amount) {
    return amount > 0 ? 'text-green-600' : 'text-red-600';
  }

  function txType(t) {
    const map = {
      hausgeld: '🏠 Hausgeld',
      ausgabe: '💸 Ausgabe',
      rücklage: '💰 Rücklage',
      bankgebühr: '🏦 Bankgebühr',
      sonstiges: '📄 Sonstiges',
      abschluss: '📈 Abschluss',
    };
    return map[t] || t || '–';
  }
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <h2 class="text-2xl font-bold">Dashboard</h2>
    <div class="flex items-center gap-2">
      <label class="text-sm text-gray-600">Jahr:</label>
      <select bind:value={year} class="border rounded-lg px-3 py-1.5 text-sm">
        {#each [2025, 2026] as y}
          <option value={y}>{y}</option>
        {/each}
      </select>
    </div>
  </div>

  {#if loading}
    <div class="text-gray-500 text-center py-12">Lade Daten…</div>
  {:else if error}
    <div class="bg-red-50 text-red-700 rounded-xl p-4">Fehler: {error}</div>
  {:else if dashboard}
    <!-- KPI Row -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {#each dashboard.accounts as acc}
        <div class="card">
          <p class="text-xs text-gray-500 uppercase tracking-wide">{acc.name}</p>
          <p class="text-2xl font-bold mt-1 {acc.current_balance >= 0 ? 'text-green-700' : 'text-red-600'}">
            {formatEur(acc.current_balance)}
          </p>
          <p class="text-xs text-gray-400 mt-1">{acc.account_type}</p>
        </div>
      {/each}

      <div class="card">
        <p class="text-xs text-gray-500 uppercase tracking-wide">Hausgeld {year}</p>
        <p class="text-2xl font-bold mt-1 text-green-700">
          {formatEur(dashboard.stats.total_hausgeld_income)}
        </p>
        <p class="text-xs text-gray-400 mt-1">Einnahmen</p>
      </div>

      <div class="card {dashboard.stats.missing_payments > 0 ? 'border-red-300 bg-red-50' : ''}">
        <p class="text-xs text-gray-500 uppercase tracking-wide">Fehlende Zahlungen</p>
        <p class="text-2xl font-bold mt-1 {dashboard.stats.missing_payments > 0 ? 'text-red-600' : 'text-green-600'}">
          {dashboard.stats.missing_payments}
        </p>
        <p class="text-xs text-gray-400 mt-1">Monate ohne Zahlung</p>
      </div>
    </div>

    <!-- Payment Matrix Overview -->
    <div class="card">
      <h3 class="font-semibold mb-4 text-gray-700">Hausgeld-Übersicht {year}</h3>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-gray-500 border-b">
              <th class="text-left pb-2 font-medium">Einheit</th>
              <th class="text-left pb-2 font-medium">Eigentümer</th>
              {#each Array(12).fill(0).map((_, i) => i + 1) as m}
                <th class="text-center pb-2 font-medium w-10">
                  {['J','F','M','A','M','J','J','A','S','O','N','D'][m-1]}
                </th>
              {/each}
              <th class="text-right pb-2 font-medium">Bilanz</th>
            </tr>
          </thead>
          <tbody>
            {#each dashboard.payment_overview as owner}
              <tr class="border-b last:border-0 hover:bg-gray-50">
                <td class="py-2 font-mono text-xs font-semibold text-primary-700">{owner.unit_id}</td>
                <td class="py-2 pr-4 text-gray-700">{owner.name}</td>
                {#each owner.months as month}
                  <td class="text-center py-2">
                    {#if month.paid > 0 && month.ok}
                      <span class="badge-ok">✓</span>
                    {:else if month.paid > 0}
                      <span class="badge-partial">~</span>
                    {:else}
                      <span class="badge-missing">✗</span>
                    {/if}
                  </td>
                {/each}
                <td class="text-right py-2 font-semibold {owner.balance >= 0 ? 'text-green-600' : 'text-red-600'}">
                  {formatEur(owner.balance)}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>

    <!-- Recent Transactions -->
    <div class="card">
      <h3 class="font-semibold mb-4 text-gray-700">Letzte Buchungen</h3>
      <div class="space-y-2">
        {#each dashboard.recent_transactions as tx}
          <div class="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50 text-sm">
            <div class="flex items-center gap-3">
              <span class="text-xs text-gray-400 w-20 shrink-0">{formatDate(tx.booking_date)}</span>
              <span class="text-gray-400 text-xs">{txType(tx.transaction_type)}</span>
              <span class="text-gray-700 truncate max-w-xs">
                {tx.counterparty_name || tx.purpose || '–'}
              </span>
              {#if tx.owner_unit}
                <span class="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">{tx.owner_unit}</span>
              {/if}
            </div>
            <span class="font-semibold shrink-0 ml-4 {txColor(tx.amount)}">
              {formatEur(tx.amount)}
            </span>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>
