---
trigger: always_on
---

# KrishiMitra: project facts and freezes

## MANDI FREEZE
Do not modify: services/market_service.py, services/prediction_service.py, services/price_fetcher.py, scripts/*, models/price.py, routes/market.py, data/mandi_coordinates.json. They are owned and finished by my teammate. You may touch only thin glue in agent/tools.py that wraps them. If mandi code breaks the WhatsApp flow, describe the problem and the smallest suggested change, then wait for my decision.

## Project map (backend/ is the root)
main.py (canonical app), scheduler.py (canonical scheduler), config.py, farmer_store.py, routes/ (REST endpoints; WhatsApp does not use them), services/ (whatsapp_service, i18n, onboarding, geocode, market, prediction, price_fetcher, disease, severity, progression, yolo, twilio_media_download), agent/ (agent.py, tools.py, guardrails.py, diagnose.py, voice.py, model/), outbreak/, data/ (disease_db.json, progression_db.json, mandi_coordinates.json), legacy/ (dead code, never import), migrations/ (SQL applied in order).
Business logic belongs in services/. routes/*.py and WhatsApp both call services; WhatsApp never calls its own HTTP endpoints.

## Database facts
Supabase tables: farmers (phone PK, name, language, lat, lng, location text, state, district, crops text[], soil_type, water_source, onboarding_step, proactive_opt_in), price_alerts, mandi_prices, detections (legacy), conversation_state, chat_history, processed_messages, disease_cases, case_updates, outbreak_alerts_sent. Only ALTER ... ADD COLUMN IF NOT EXISTS; never drop or recreate tables. Phone numbers are normalized E.164 without "whatsapp:".

## Disease model reality
- New best.pt (in use): YOLOv8 detect, imgsz 640, 29 classes = 18 diseases + 11 healthy-leaf classes (apple, bell pepper, blueberry, cherry, corn, grape, peach, potato, raspberry, soybean, squash, strawberry, tomato). Blueberry, cherry, peach, raspberry, soybean and strawberry have a healthy class only, no disease classes.
- The old classifier.onnx covers only 15 PlantVillage classes (pepper, potato, tomato). Class names come from model metadata / class_names.json, never a hardcoded list.
- Boxes may cover whole leaves, not lesions. Severity is never presented as measured unless validated; the farmer's report is the primary severity input.
- "Healthy" wording is "I don't see signs of the diseases I can recognize", never certainty. Unsupported crops get an honest message plus general advice clearly labelled as general.
- NOT covered: chilli, ragi, paddy, sugarcane, arecanut, onion, groundnut, cotton.

## Other
- Groq deprecates models often; check the startup model warning.
- WhatsApp allows free-form proactive messages only within 24h of the farmer's last message; outside that window approved templates are required.