Build OpsDesk, a small incident board for an operations team. Start with the visible
app only. I should be able to click and use it before adding AI.

Create three synthetic tickets: payments is slow (high), checkout needs a health
check (medium), catalog availability check (low). Each has id, title, description,
service and priority. Show an inbox, priority filter, search, selected-ticket detail
and a New ticket form. Ticket edits stay in memory for this first exercise.

Add an Ask AI panel with Analyze safely, a result area and an initial state reading
"AI is not connected yet". Do not generate a fake AI response, pretend to authenticate
a user, or imply that a database exists. Mark all tickets as synthetic training data.

Use Oracle Redwood for a clear desktop/mobile layout: Oracle red accents, warm stone
surfaces, Georgia headings and local Figtree/system UI text. Use only approved brand
assets. Keep compact incident rows and one clear action. Make loading, empty,
validation and failure states usable. Render ticket text as text, never raw HTML.
No paid integrations, real customer data, production connectors, automatic publishing,
real model calls or secrets in this first build. Show which visible features work
and which capabilities still need a backend. Then stop for a review of the preview.
