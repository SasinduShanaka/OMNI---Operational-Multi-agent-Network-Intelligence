# User Stories & Agent Stories

These stories follow the Agile format: **"As a [Role], I want to [Action], so that [Benefit]."** 
They are broken down by the Human User and the 4 Agents in your Balanced Scope system. You can use these directly in your project report or GitHub issues to track your development progress.

---

## 1. The Human Manager (End-User)

*   **US-1.1:** As a Human Manager, I want to type a natural language request (e.g., *"We need 500 meters of organic cotton"*), so that I don't have to manually search through supplier databases.
*   **US-1.2:** As a Human Manager, I want the system to pause and ask for my explicit approval before finalizing any Purchase Order, so that I maintain financial control over the budget.
*   **US-1.3:** As a Human Manager, I want to receive a simple, plain-English summary of the final booked freight, so that I know exactly when the goods will arrive without logging into a TMS system.

---

## 2. Agent 1: Sourcing & RAG Compliance Agent

*   **AS-1.1 (Sourcing):** As the Sourcing Agent, I want to query the `mock-erp.db` (via MCP) based on the user's requested material, so that I can find a list of potential suppliers who sell that item.
*   **AS-1.2 (Quoting):** As the Sourcing Agent, I want to retrieve the unit price and lead time for the matched suppliers, so that I can identify the most cost-effective option.
*   **AS-1.3 (RAG Compliance):** As the Compliance Agent, I want to search a local vector database of PDF Supplier Contracts, so that I can verify the chosen supplier strictly adheres to "Organic" and "Child-Labor Free" policies before recommending them.
*   **AS-1.4 (Handoff):** As the Sourcing Agent, I want to pass the `supplier_id`, total cost, and compliance proof to the Purchasing Agent, so that the PO drafting process can begin.

---

## 3. Agent 2: Purchasing & PO Agent

*   **AS-2.1 (Drafting):** As the Purchasing Agent, I want to receive a validated supplier and quantity, and call the `draft_po` tool (via MCP), so that a new record is created in the `Purchase_Orders` table with a status of 'Pending'.
*   **AS-2.2 (Human-in-the-Loop):** As the Purchasing Agent, I want to halt my execution and message the Human Manager with the PO details, so that I do not authorize spending without human consent.
*   **AS-2.3 (Finalizing):** As the Purchasing Agent, I want to update the PO status to 'Approved' in the database once the human confirms, and notify the Freight Booking Agent to arrange transport.

---

## 4. Agent 3: Freight Booking Agent

*   **AS-3.1 (Carrier Lookup):** As the Freight Booking Agent, I want to read the approved PO details and query the `mock-tms.db` (via MCP) for available carriers (e.g., Sea vs. Air freight), so that I can see my shipping options.
*   **AS-3.2 (Decision Logic):** As the Freight Booking Agent, I want to select the transport mode based on urgency (e.g., if lead time is short, pick Air; if normal, pick Sea), so that I balance shipping costs against production deadlines.
*   **AS-3.3 (Booking):** As the Freight Booking Agent, I want to call the `book_shipment` tool to generate a shipment record in the TMS database, so that the physical logistics process is officially initiated.

---

## 5. Agent 4: Shipment Tracking Agent

*   **AS-4.1 (Monitoring):** As the Tracking Agent, I want to periodically call the `get_shipment_status` tool for active shipments, so that I know where the goods currently are.
*   **AS-4.2 (Exception Handling - Optional Bonus):** As the Tracking Agent, I want to check a weather API for the shipment's origin port, so that if there is a severe storm, I can update the TMS status to "Delayed" and alert the Human Manager.

---

> [!TIP]  
> **How to use these:** When building your code, take one story at a time. For example, do not start writing code for the Purchasing Agent until you can prove that `AS-1.1` and `AS-1.2` execute flawlessly in your terminal.
