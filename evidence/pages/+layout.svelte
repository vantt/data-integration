<script>
  import '@evidence-dev/tailwind/fonts.css';
  import '../app.css';
  import { EvidenceDefaultLayout } from '@evidence-dev/core-components';
  export let data;
</script>

<EvidenceDefaultLayout {data}>
  <slot slot="content" />
</EvidenceDefaultLayout>

<style>
  /* ═══ Indigo primary + slate content palette ═══ */
  :global([data-theme=light]) {
    --primary: #6366f1;
    --primary-content: #eef2ff;
    --base-100: #f8fafc;
    --base-200: #f1f5f9;
    --base-300: #e2e8f0;
    --base-content: #1e293b;
    --base-content-muted: #64748b;
    --base-heading: #0f172a;
    --positive: #16a34a;
    --negative: #dc2626;
    --info: #0284c7;
    --warning: #d97706;
  }

  /* ═══ Dark top bar ═══ */
  :global(header.fixed) {
    background-color: #0f172a !important;
    border-bottom-color: #1e293b !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
  }
  /* Force wordmark to white on dark bg */
  :global(header.fixed a img) {
    filter: brightness(0) invert(1);
  }
  :global(header.fixed button) {
    color: #94a3b8 !important;
  }
  :global(header.fixed button:hover) {
    background-color: #1e293b !important;
    color: #e2e8f0 !important;
  }
  :global(header.fixed .text-base-content) {
    color: #cbd5e1 !important;
  }
  /* Search icon + settings icon color */
  :global(header.fixed svg) {
    color: #94a3b8;
  }

  /* ═══ Dark left sidebar ═══ */
  :global(aside) {
    background-color: #0f172a;
  }
  /* The inner fixed div needs explicit bg too */
  :global(aside > div) {
    background-color: #0f172a !important;
  }
  /* All links in sidebar */
  :global(aside a) {
    color: #94a3b8 !important;
    background: transparent !important;
    box-shadow: none !important;
  }
  :global(aside a:hover) {
    color: #e2e8f0 !important;
  }
  /* Active page highlight → indigo-300 */
  :global(aside a.text-primary) {
    color: #a5b4fc !important;
    font-weight: 600 !important;
  }
  /* Remove white sticky background from "Home" section header */
  :global(aside .bg-base-100) {
    background-color: transparent !important;
  }
  :global(aside .shadow, aside [class*="shadow-base"]) {
    --tw-shadow: none;
    box-shadow: none !important;
  }

  /* ═══ Content area polish ═══ */
  /* Slightly deeper border for cards defined in pages */
  :global(main .border) {
    border-color: #e2e8f0;
  }
  /* Reduce aggressive top padding under dark header */
  :global(main > article) {
    padding-top: 1.5rem;
  }
</style>
