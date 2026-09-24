# OMNI Evaluation Walkthrough

## Before the demonstration

1. Start the backend and frontend using the commands in README.md.
2. Create an evaluator account or sign in with an existing account. Do not share a real user's password.
3. In Ask Omni, expand **Service status** and select **Check services**.
4. Confirm that MongoDB contains products, inventory, BOM, production lines, and demand history. Supplier and shipment records currently come from the local ERP/TMS SQLite databases; the panel identifies these sources.
5. Resolve missing records before the demonstration. Do not rerun seed scripts against a populated database without checking their deletion/reset behavior.
6. Use a product that exists in your database. The examples below use Classic Black Polo / GAR-001. Quantities and results depend on current records.

The language-model and email checks validate configuration only. They do not contact the provider or send test emails. A configured service can still fail because of connectivity, quotas, authentication, or an unverified sender.

## Demonstration Sequence

| Prompt or action | Evidence to show |
| --- | --- |
| `What materials are needed for 1,250 Classic Black Polo units?` | Bill of materials, quantity per unit, total requirement, available stock, and shortages. |
| `Can we fulfill 1,250 Classic Black Polo units in 30 days? Explain the reasons and next steps.` | Feasibility verdict, explicit deadline, working days, capacity, and material checks. |
| `Can we fulfill 10,000 Classic Black Polo units in 30 days? Explain the reasons and next steps.` | Constraints, capacity shortfall, material shortages, and any alternative-line proposals. |
| `Which materials are below their reorder levels?` | Current stock, reorder level, and replenishment requirement. |
| `Find suppliers for those low stock materials` | Supplier suggestions. Finding suppliers alone does not approve an order. |
| `Order these low stock materials` | Draft PO for each material, quantity and value, manual approval controls. |
| Select **Reject** on a demonstration draft | Saved rejection, disabled approval controls, same rejected status in Supplier intel. |
| Select **Authorize PO** on a reviewed draft | Actual approval, shipment record if created, and separate email delivery result. This action can send a real email. |
| `Download a report of the previous answer` | PDF from the chat result. |

Do not repeatedly submit ordering or feasibility prompts during a demonstration without reviewing existing drafts: a new request can create another set of draft orders. Approval itself is protected against repeated processing of the same run.

## Explain the Actions Accurately

- Planning checks read current factory records. The evidence includes a check timestamp; it is a snapshot, not a stock reservation.
- Missing BOM data cannot produce a positive feasibility verdict.
- A draft PO is a saved database record awaiting manual approval. Automatically estimated values are labelled for review.
- Approval and rejection are saved with the procurement run and survive backend restarts for newly created runs.
- Email failure does not undo an approved order. Review the email result and fix configuration before using the existing resend command in Supplier intel.
- The freight integration creates records in the local TMS. A shipment record is not proof that an external carrier accepted a real booking.
- Line reallocations remain recommendations. No production schedule is changed by a feasibility check or PO approval.
- A material's supplier lead time alone cannot prove that the finished order will meet its deadline. Allow time for receipt, production, and delivery.
- Ask Omni's loading agent comes from backend progress updates. The local progress registry expects a single API worker. Chat context is still in memory; restart the conversation after a backend restart.

## Email Configuration

Configure these in the ignored `backend/.env` file using your own credentials:

```dotenv
BREVO_SMTP_HOST=smtp-relay.brevo.com
BREVO_SMTP_PORT=587
BREVO_SMTP_USER=
BREVO_SMTP_PASS=
BREVO_SENDER_EMAIL=
BREVO_SENDER_NAME=OMNI Procurement
```

No credentials are included in this guide. Confirm the supplier's stored email address before authorizing a real PO.

## Regression Checks

```powershell
.\.venv\Scripts\python.exe -m unittest backend.test_factory_operations_mcp backend.test_auth backend.test_evaluation backend.test_reports -v
```

From `frontend`:

```powershell
npm run build
npm run lint
node --test src/components/chatReports.test.js
```

The evaluation regression tests use isolated records and mocked external services. They do not seed the live database, book freight, or send supplier emails.
