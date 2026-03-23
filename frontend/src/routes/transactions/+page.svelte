<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { api } from '$lib/api.js';
  import { formatEur, formatDate } from '$lib/format.js';

  let data = { total: 0, items: [] };
  let loading = true;
  let error = null;

  let filters = {
    account_number: $page.url.searchParams.get('account_number') || '',
    transaction_type: '',
    owner_unit: '',
    year: new Date().getFullYear(),
    month: '',
  };

  const txTypes = ['hausgeld', 'ausgabe', 'rücklage', 'bankgebühr', 'abschluss', 'sonstiges'];

  async function load() {
    loading = true;
    error = null;
    try {
      const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== ''));
      data = await api.getTransactions(params);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  onMount(load);

  function txColor(amount) {
    return amount > 0 ? 'text-green-600' : 'text-red-600';
  }
</script>

<div class="space-y-6">
  <h2 class="text-2xl font-bold">Buchungen</h2>

  <!-- Filter bar -->
  <div class="card">
    <div class="flex flex-wrap gap-3 items-end">
      <div>
        <label class="text-xs text-gray-600 block mb-1">Konto</label>
        <select bind:value={filters.account_number} class="border rounded-lg px-3 py-1.5 text-sm">
          <option value="">Alle</option>
          <option value="6023543">Betriebskonto (6023543)</option>
          <option value="6023550">Rücklagenkonto (6023550)</option>
        </select>
      </div>
      <div>
        <label class="text-xs text-gray-600 block mb-1">Typ</label>
        <select bind:value={filters.transaction_type} class="border rounded-lg px-3 py-1.5 text-sm">
          <option value="">Alle</option>
          {#each txTypes as t}
            <option value={t}>{t}</option>
          {/each}
        </select>
      </div>
      <div>
        <label class="text-xs text-gray-600 block mb-1">Einheit</label>
        <select bind:value={filters.owner_unit} class="border rounded-lg px-3 py-1.5 text-sm">
          <option value="">Alle</option>
          {#each ['WE-001', 'WE-002', 'WE-003', 'WE-004'] as u}
            <option value={u}>{u}</option>
          {/each}
        </select>
      </div>
      <div>
        <label class="text-xs text-gray-600 block mb-1">Jahr</label>
        <select bind:value={filters.year} class="border rounded-lg px-3 py-1.5 text-sm">
          {#each [2025, 2026] as y}
            <option value={y}>{y}</option>
          {/each}
        </select>
      </div>
      <button class="btn-primary text-sm" on:click={load}>Filtern</button>
    </div>
  </div>

  {#if loading}
    <div class="text-gray-500 text-center py-12">Lade…</div>
  {:else if error}
    <div class="bg-red-50 text-red-700 rounded-xl p-4">Fehler: {error}</div>
  {:else}
    <div class="card">
      <div class="flex justify-between items-center mb-3">
        <p class="text-sm text-gray-500">{data.total} Buchungen</p>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-gray-500">
            <tr>
              <th class="text-left px-3 py-2 font-medium">Datum</th>
              <th class="text-left px-3 py-2 font-medium">Auftraggeber / Name</th>
              <th class="text-left px-3 py-2 font-medium">Verwendungszweck</th>
              <th class="text-left px-3 py-2 font-medium">Typ</th>
              <th class="text-left px-3 py-2 font-medium">Einheit</th>
              <th class="text-right px-3 py-2 font-medium">Betrag</th>
            </tr>
          </thead>
          <tbody>
            {#each data.items as tx}
              <tr class="border-t hover:bg-gray-50">
                <td class="px-3 py-2 text-gray-500 text-xs whitespace-nowrap">{formatDate(tx.booking_date)}</td>
                <td class="px-3 py-2 max-w-[180px] truncate">{tx.counterparty_name || '–'}</td>
                <td class="px-3 py-2 max-w-[300px] truncate text-gray-600 text-xs">{tx.purpose || tx.booking_text || '–'}</td>
                <td class="px-3 py-2">
                  <span class="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-700">{tx.transaction_type || '–'}</span>
                </td>
                <td class="px-3 py-2">
                  {#if tx.owner_unit}
                    <span class="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">{tx.owner_unit}</span>
                  {/if}
                </td>
                <td class="px-3 py-2 text-right font-semibold {txColor(tx.amount)}">{formatEur(tx.amount)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}
</div>
