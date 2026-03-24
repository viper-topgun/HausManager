<script>
  import { api } from '$lib/api.js';
  import { onMount } from 'svelte';

  const YEARS = [2024, 2025, 2026, 2027];
  let selectedYear = new Date().getFullYear();

  let accounts = [];
  let selectedAccount = '';

  onMount(async () => {
    try {
      accounts = await api.getAccounts();
    } catch (e) {
      // ignore – account filter optional
    }
  });

  function witterDocxUrl(year) {
    return `/api/witter/${year}/export/docx`;
  }
  function witterPdfUrl(year) {
    return `/api/witter/${year}/export/pdf`;
  }
  function transactionsXlsxUrl(year, account) {
    let url = `/api/transactions/export/xlsx?year=${year}`;
    if (account) url += `&account_number=${encodeURIComponent(account)}`;
    return url;
  }
  function transactionsXlsxAllUrl() {
    if (selectedAccount) return `/api/transactions/export/xlsx?account_number=${encodeURIComponent(selectedAccount)}`;
    return `/api/transactions/export/xlsx`;
  }
</script>

<div class="p-6 max-w-3xl mx-auto">
  <h1 class="text-2xl font-bold text-gray-900 mb-1">Export</h1>
  <p class="text-sm text-gray-500 mb-6">Daten als Datei herunterladen</p>

  <!-- ── Witter Abrechnung ─────────────────────────────────────────────────── -->
  <div class="bg-white rounded-xl border border-gray-200 shadow-sm mb-6">
    <div class="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
      <span class="text-lg">🔥</span>
      <h2 class="text-base font-semibold text-gray-800">Witter Heizkostenabrechnung</h2>
    </div>
    <div class="px-5 py-4">
      <p class="text-sm text-gray-500 mb-4">Vollständige Abrechnung (alle Formular-Sektionen) als Word- oder PDF-Dokument.</p>

      <!-- Year selector -->
      <div class="flex items-center gap-2 mb-4">
        <span class="text-sm text-gray-600 font-medium w-16">Jahr</span>
        <div class="flex gap-1 bg-gray-100 rounded-lg p-1">
          {#each YEARS as y}
            <button
              on:click={() => selectedYear = y}
              class="px-3 py-1 text-sm font-medium rounded-md transition-colors
                {selectedYear === y ? 'bg-white shadow text-primary-700' : 'text-gray-500 hover:text-gray-700'}"
            >{y}</button>
          {/each}
        </div>
      </div>

      <div class="flex flex-wrap gap-3">
        <a
          href={witterDocxUrl(selectedYear)}
          download="Witter_Abrechnung_{selectedYear}.docx"
          class="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-sm font-medium text-gray-700 transition-colors shadow-sm"
        >
          <span class="text-base">📄</span>
          Word (.docx) – {selectedYear}
        </a>
        <a
          href={witterPdfUrl(selectedYear)}
          download="Witter_Abrechnung_{selectedYear}.pdf"
          class="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-sm font-medium text-gray-700 transition-colors shadow-sm"
        >
          <span class="text-base">📕</span>
          PDF – {selectedYear}
        </a>
      </div>
    </div>
  </div>

  <!-- ── Buchungen / Transaktionen ─────────────────────────────────────────── -->
  <div class="bg-white rounded-xl border border-gray-200 shadow-sm mb-6">
    <div class="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
      <span class="text-lg">📋</span>
      <h2 class="text-base font-semibold text-gray-800">Buchungen</h2>
    </div>
    <div class="px-5 py-4">
      <p class="text-sm text-gray-500 mb-4">Alle Buchungen mit Kategorisierung als Excel-Tabelle.</p>

      <!-- Filters -->
      <div class="flex flex-wrap items-center gap-4 mb-4">
        <div class="flex items-center gap-2">
          <span class="text-sm text-gray-600 font-medium w-16">Jahr</span>
          <div class="flex gap-1 bg-gray-100 rounded-lg p-1">
            {#each YEARS as y}
              <button
                on:click={() => selectedYear = y}
                class="px-3 py-1 text-sm font-medium rounded-md transition-colors
                  {selectedYear === y ? 'bg-white shadow text-primary-700' : 'text-gray-500 hover:text-gray-700'}"
              >{y}</button>
            {/each}
          </div>
        </div>
        {#if accounts.length > 0}
          <div class="flex items-center gap-2">
            <span class="text-sm text-gray-600 font-medium">Konto</span>
            <select bind:value={selectedAccount} class="border rounded-lg px-2 py-1.5 text-sm text-gray-700">
              <option value="">Alle Konten</option>
              {#each accounts as acc}
                <option value={acc.account_number}>{acc.account_number} – {acc.owner || acc.description || ''}</option>
              {/each}
            </select>
          </div>
        {/if}
      </div>

      <div class="flex flex-wrap gap-3">
        <a
          href={transactionsXlsxUrl(selectedYear, selectedAccount)}
          download="Buchungen_{selectedYear}.xlsx"
          class="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-sm font-medium text-gray-700 transition-colors shadow-sm"
        >
          <span class="text-base">📊</span>
          Excel – {selectedYear}{selectedAccount ? ' / ' + selectedAccount : ''}
        </a>
        <a
          href={transactionsXlsxAllUrl()}
          download="Buchungen_Alle.xlsx"
          class="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-sm font-medium text-gray-700 transition-colors shadow-sm"
        >
          <span class="text-base">📊</span>
          Excel – Alle Jahre{selectedAccount ? ' / ' + selectedAccount : ''}
        </a>
      </div>
    </div>
  </div>
</div>
