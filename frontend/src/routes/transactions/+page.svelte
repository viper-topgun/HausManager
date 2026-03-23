<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { api } from '$lib/api.js';
  import { formatEur, formatDate } from '$lib/format.js';
  import { currentUser } from '$lib/auth.js';

  let data = { total: 0, items: [] };
  let loading = true;
  let error = null;

  // Fehlbuchung modal
  let fehlbuchungModal = null; // { tx, note }
  let fehlbuchungSaving = false;

  let filters = {
    account_number: $page.url.searchParams.get('account_number') || '',
    transaction_type: '',
    owner_unit: '',
    year: new Date().getFullYear(),
    month: '',
    search: '',
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

  function openFehlbuchung(tx) {
    if (tx.is_fehlbuchung) {
      if (!confirm(`Fehlbuchungs-Markierung von "${tx.counterparty_name || 'dieser Buchung'}" entfernen?`)) return;
      api.markFehlbuchung(tx._id, { is_fehlbuchung: false }).then(() => load());
    } else {
      fehlbuchungModal = { tx, note: '' };
    }
  }

  async function saveFehlbuchung() {
    fehlbuchungSaving = true;
    try {
      await api.markFehlbuchung(fehlbuchungModal.tx._id, {
        is_fehlbuchung: true,
        fehlbuchung_note: fehlbuchungModal.note || null,
      });
      fehlbuchungModal = null;
      await load();
    } catch (e) {
      alert('Fehler: ' + e.message);
    } finally {
      fehlbuchungSaving = false;
    }
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
      {#if filters.search || filters.transaction_type || filters.owner_unit || filters.account_number}
        <button
          class="text-xs text-gray-400 hover:text-gray-700 underline"
          on:click={() => { filters = { account_number: '', transaction_type: '', owner_unit: '', year: new Date().getFullYear(), month: '', search: '' }; load(); }}
        >Filter zurücksetzen</button>
      {/if}
    </div>
    <!-- Freitext-Suche -->
    <div class="mt-3">
      <label class="text-xs text-gray-600 block mb-1">Freitext-Suche</label>
      <div class="flex gap-2">
        <input
          type="text"
          bind:value={filters.search}
          on:keydown={(e) => e.key === 'Enter' && load()}
          placeholder="Name, Verwendungszweck …"
          class="border rounded-lg px-3 py-1.5 text-sm w-72"
        />
        {#if filters.search}
          <button
            class="text-xs text-gray-400 hover:text-gray-700 px-2"
            on:click={() => { filters.search = ''; load(); }}
          >✕</button>
        {/if}
      </div>
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
              <th class="px-2 py-2 w-8"></th>
            </tr>
          </thead>
          <tbody>
            {#each data.items as tx}
              <tr class="border-t hover:bg-gray-50 {tx.is_fehlbuchung ? 'bg-red-50/40 opacity-60' : ''}">
                <td class="px-3 py-2 text-gray-500 text-xs whitespace-nowrap">{formatDate(tx.booking_date)}</td>
                <td class="px-3 py-2 max-w-[180px] truncate {tx.is_fehlbuchung ? 'line-through' : ''}">{tx.counterparty_name || '–'}</td>
                <td class="px-3 py-2 max-w-[300px] text-gray-600 text-xs">
                  <span class="truncate block {tx.is_fehlbuchung ? 'line-through' : ''}">{tx.purpose || tx.booking_text || '–'}</span>
                  {#if tx.fehlbuchung_note}
                    <span class="text-red-500 block mt-0.5 not-italic">⚠ {tx.fehlbuchung_note}</span>
                  {/if}
                </td>
                <td class="px-3 py-2">
                  <span class="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-700">{tx.transaction_type || '–'}</span>
                  {#if tx.is_fehlbuchung}
                    <span class="ml-1 text-xs text-red-500" title="Fehlbuchung">🚫</span>
                  {/if}
                </td>
                <td class="px-3 py-2">
                  {#if tx.owner_unit}
                    <span class="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">{tx.owner_unit}</span>
                  {/if}
                </td>
                <td class="px-3 py-2 text-right font-semibold {tx.is_fehlbuchung ? 'line-through text-gray-400' : txColor(tx.amount)}">{formatEur(tx.amount)}</td>
                <td class="px-2 py-2 text-center w-8">
                  {#if $currentUser?.role === 'admin'}
                    <button
                      title={tx.is_fehlbuchung ? (tx.fehlbuchung_note ? `Fehlbuchung: ${tx.fehlbuchung_note} – Klick zum Entfernen` : 'Fehlbuchung – Klick zum Entfernen') : 'Als Fehlbuchung markieren'}
                      on:click={() => openFehlbuchung(tx)}
                      class="text-sm transition-opacity {tx.is_fehlbuchung ? 'opacity-100' : 'opacity-0 hover:opacity-70 group-hover:opacity-40'}"
                    >🚫</button>
                  {:else if tx.is_fehlbuchung}
                    <span title={tx.fehlbuchung_note || 'Fehlbuchung'} class="text-sm cursor-help">🚫</span>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}
</div>

<!-- Fehlbuchung Modal -->
{#if fehlbuchungModal}
  <div
    class="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
    on:click|self={() => (fehlbuchungModal = null)}
    role="dialog"
    aria-modal="true"
  >
    <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 p-6">
      <h2 class="text-base font-bold text-gray-800 mb-1">🚫 Fehlbuchung markieren</h2>
      <p class="text-sm text-gray-500 mb-4">
        <span class="font-medium">{fehlbuchungModal.tx.counterparty_name || '–'}</span>
        &middot; {formatEur(fehlbuchungModal.tx.amount)}
        &middot; {formatDate(fehlbuchungModal.tx.booking_date)}
      </p>
      <div class="space-y-3">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Hinweis (optional)</label>
          <input
            type="text"
            bind:value={fehlbuchungModal.note}
            placeholder="z.B. Storniert und erstattet am 15.03.2025"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
          />
        </div>
        <p class="text-xs text-gray-400">
          Diese Buchung wird in keiner Abrechnung und keiner Auswertung berücksichtigt.
          Sie bleibt in der Buchungsliste sichtbar, aber durchgestrichen markiert.
        </p>
      </div>
      <div class="flex justify-end gap-3 mt-5">
        <button
          on:click={() => (fehlbuchungModal = null)}
          class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 font-medium"
        >Abbrechen</button>
        <button
          on:click={saveFehlbuchung}
          disabled={fehlbuchungSaving}
          class="bg-red-500 hover:bg-red-600 disabled:opacity-50 text-white text-sm font-semibold px-5 py-2 rounded-lg transition-colors"
        >
          {fehlbuchungSaving ? 'Speichert…' : '🚫 Als Fehlbuchung markieren'}
        </button>
      </div>
    </div>
  </div>
{/if}
