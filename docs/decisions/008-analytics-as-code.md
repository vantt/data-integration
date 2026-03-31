# ADR-008: Analytics-as-Code với Markdown blueprints

> **Trạng thái:** Accepted
> **Ngày:** 2026-03-31
> **Tham chiếu:** [`AGENTS.md` §Analytics-as-Code](../../AGENTS.md), [`analytics-handbook/README.md`](../analytics-handbook/README.md)

## Bối cảnh

Metabase dashboards thường được tạo thủ công qua UI. Điều này gây ra:
- Không version control
- Không review trước khi deploy
- Không reproducible (mất dashboard = mất config)
- Documentation tách rời khỏi implementation

## Quyết định

**Metabase config định nghĩa trong Markdown**, triển khai tự động:

```
Domain (metrics) → Playbook (story) → Blueprint (implementation) → Deploy script → Metabase
```

| Layer | File | Audience | Nội dung |
|:---|:---|:---|:---|
| Domain | `domains/*.md` | Business | Metrics definitions, SQL formulas |
| Playbook | `playbooks/*.md` | Human | User stories, layout, visualization |
| Blueprint | `blueprints/*.md` | Machine | SQL queries, JSON config, deployable |

Blueprint = documentation + deployment config trong cùng 1 file Markdown.

## Lý do

1. **Single source of truth** — documentation IS the config
2. **Version control** — git diff thấy rõ thay đổi
3. **Code review** — review blueprint trước khi deploy lên production Metabase
4. **Reproducible** — `deploy_from_markdown.js` tái tạo dashboard bất kỳ lúc nào
5. **Accessible** — Playbook readable bởi non-technical stakeholders

## Hệ quả

- Cần maintain 3 layers (domain → playbook → blueprint) cho mỗi dashboard
- Deploy script cần parse Markdown → phức tạp hơn JSON/YAML config
- Thay đổi nhỏ trên UI (drag card, resize) cần sync ngược vào blueprint

## Khi nào xem xét lại

- Nếu team lớn hơn cần self-serve dashboard creation → cân nhắc thêm UI-first workflow
- Nếu Metabase hỗ trợ native Git sync → có thể đơn giản hóa deploy script
