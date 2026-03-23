<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { formatEur } from '$lib/format.js';

  let accounts = [];
  let history = [];
  let loading = true;
  let error = null;

  onMount(async () => {
    try {
      [accounts, history] = await Promise.all([
        api.getAccounts(),
        api.getAccountBalanceHistory(),
      ]);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  const typeLabel = {
    betriebskonto: 'Betriebskonto',
    rücklagenkonto: 'Rücklagenkonto',
  };

  // Merge history into accounts lookup
  $: historyByAccount = Object.fromEntries(
    history.map(h => [h.account_number, h])
  );

  // Collect all years across both accounts for the overview table
  $: allYears = [...new Set(history.flatMap(h => h.snapshots.map(s => s.year)))].sort();
</script>

<div class="space-y-6">
  <h2 class="text-2xl font-bold">Konten</h2>

  {#if loading}
    <div class="text-gray-500 text-center py-12 animate-pulse">Lade…</div>
  {:else if error}
    <div class="bg-red-50 text-red-700 rounded-xl p-4">Fehler: {error}</div>
  {:else}

    <!-- Account cards -->
    <div class="grid md:grid-cols-2 gap-6">
      {#each accounts as acc}
        <div class="card">
          <div class="flex justify-between items-start mb-4">
            <div>
              <span class="text-xs text-gray-500 uppercase tracking-wide">{typeLabel[acc.account_type] || acc.account_type}</span>
              <h3 class="text-xl font-bold mt-0.5">{acc.name}</h3>
            </div>
            <span class="text-3xl font-bold {acc.current_balance >= 0 ? 'text-green-600' : 'text-red-600'}">
              {formatEur(acc.current_balance)}
            </span>
          </div>
          <dl class="space-y-2 text-sm text-gray-600">
            <div class="flex justify-between border-t pt-2">
              <dt>Kontonummer</dt>
              <dd class="font-mono">{acc.account_number}</dd>
            </div>
            <div class="flex justify-between">
              <dt>IBAN</dt>
              <dd class="font-mono text-xs">{acc.iban}</dd>
            </div>
            <div class="flex justify-between">
              <dt>Bank</dt>
              <dd>{acc.bank_name || '–'}</dd>
            </div>
            <div class="flex justify-between">
              <dt>Währung</dt>
              <dd>{acc.currency}</dd>
            </div>
          </dl>
          <a
            href="/transactions?account_number={acc.account_number}"
            class="mt-4 block text-center btn-secondary text-sm"
          >
            Buchungen anzeigen →
          </a>
        </div>
      {/each}
    </div>

    <!-- Jahreskontostand-Verlauf -->
    {#if allYears.length > 0}
      <div class="card">
        <h3 class="font-semibold text-gray-700 mb-1">📅 Kontostände zum Jahresanfang & -ende</h3>
        <p class="text-xs text-gray-400 mb-4">
          01.01. = Kontostand vor der ersten Buchung des Jahres · 31.12. = nach der letzten Buchung
        </p>

        {#each history as acc_hist}
          {#if acc_hist.snapshots.length > 0}
            <div class="mb-6 last:mb-0">
              <h4 class="text-sm font-semibold text-gray-600 mb-2">
                {acc_hist.name}
                <span class="font-normal text-gray-400 ml-2">({acc_hist.account_number})</span>
              </h4>
              <div class="overflow-x-auto">
                <table class="w-full text-sm">
                  <thead>
                    <tr class="text-xs text-gray-400 border-b">
                      <th class="text-left py-2 pr-6 font-medium">Jahr</th>
                      <th class="text-right py-2 pr-6 font-medium">01.01. (Anfang)</th>
                      <th class="text-right py-2 pr-6 font-medium">31.12. (Ende)</th>
                      <th class="text-right py-2 font-medium">Veränderung</th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each acc_hist.snapshots as snap}
                      <tr class="border-b last:border-0 hover:bg-gray-50">
                        <td class="py-2.5 pr-6 font-semibold text-gray-700">{snap.year}</td>
                        <td class="py-2.5 pr-6 text-right font-mono text-gray-700">
                          {formatEur(snap.balance_jan1)}
                        </td>
                        <td class="py-2.5 pr-6 text-right font-mono font-semibold
                          {snap.balance_dec31 >= snap.balance_jan1 ? 'text-green-600' : 'text-red-600'}">
                          {formatEur(snap.balance_dec31)}
                        </td>
                        <td class="py-2.5 text-right font-semibold
                          {snap.change >= 0 ? 'text-green-600' : 'text-red-600'}">
                          {snap.change >= 0 ? '+' : ''}{formatEur(snap.change)}
                        </td>
                      </tr>
                    {/each}
                    <!-- Aktueller Kontostand als letzte Zeile -->
                    <tr class="bg-blue-50 border-t-2 border-blue-200">
                      <td class="py-2.5 pr-6 font-bold text-blue-700">Aktuell</td>
                      <td class="py-2.5 pr-6 text-right text-blue-400 text-xs" colspan="2">Stand heute</td>
                      <td class="py-2.5 text-right font-bold text-blue-700">
                        {formatEur(acc_hist.current_balance)}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          {/if}
        {/each}
      </div>

      <!-- Combined overview: both accounts side-by-side per year -->
      {#if history.length >= 2}
        <div class="card">
          <h3 class="font-semibold text-gray-700 mb-4">📊 Gesamtübersicht beider Konten</h3>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="text-xs text-gray-400 border-b">
                  <th class="text-left py-2 pr-4 font-medium">Jahr</th>
                  <th class="text-left py-2 pr-4 font-medium">Datum</th>
                  {#each history as h}
                    <th class="text-right py-2 pr-4 font-medium">{h.name}</th>
                  {/each}
                  <th class="text-right py-2 font-medium">Gesamt</th>
                </tr>
              </thead>
              <tbody>
                {#each allYears as year}
                  {@const rows = [
                    { label: '01.01.' + year, key: 'balance_jan1'  },
                    { label: '31.12.' + year, key: 'balance_dec31' },
                  ]}
                  {#each rows as row, ri}
                    <tr class="{ri === 0 ? 'border-t' : ''} hover:bg-gray-50 {ri === 1 ? 'border-b-2 border-gray-200 font-semibold' : ''}">
                      <td class="py-2 pr-4 text-gray-500 text-xs">{ri === 0 ? year : ''}</td>
                      <td class="py-2 pr-4 font-mono text-xs text-gray-600">{row.label}</td>
                      {#each history as h}
                        {@const snap = h.snapshots.find(s => s.year === year)}
                        <td class="py-2 pr-4 text-right font-mono
                          {snap ? (snap[row.key] >= 0 ? 'text-gray-700' : 'text-red-600') : 'text-gray-300'}">
                          {snap ? formatEur(snap[row.key]) : '–'}
                        </td>
                      {/each}
                      <td class="py-2 text-right font-mono font-semibold text-blue-700">
                        {formatEur(history.reduce((s, h) => {
                            const snap = h.snapshots.find(s2 => s2.year === year);
                            return s + (snap ? snap[row.key] : 0);
                          }, 0))}
                      </td>
                    </tr>
                  {/each}
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      {/if}
    {/if}
  {/if}
</div>
