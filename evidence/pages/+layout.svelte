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
  /* Override primary to indigo in dark theme */
  :global([data-theme=dark]) {
    --primary: #818cf8;
    --primary-content: #1e1b4b;
    --twc-primary: 234.5 89.5% 73.9%;
  }
</style>
