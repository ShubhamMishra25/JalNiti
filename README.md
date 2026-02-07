# Water Wallet – WhatsApp Flask API

## Overview

This repository contains the **WhatsApp integration layer** for the **Water Wallet** system. The purpose of this service is to act as a **conversational data collection interface** using WhatsApp and forward structured inputs to the existing Water Wallet backend APIs.

The WhatsApp interface enables farmers and evaluators to interact with Water Wallet **without installing any application**, aligning with the MVO (Minimum Viable Offering) objective of accessibility and rapid validation.

---

## Quickstart: Skeleton & Credential Test Bot

The current codebase is intentionally lightweight so that you can verify your WhatsApp Cloud API credentials before building the full Water Wallet logic.

1.  Install dependencies and load your `.env` (see [Environment Configuration](#environment-configuration)).
2.  Start the Flask server: `python app.py`. This exposes `/webhook` for Meta verification and prints any mock replies locally if credentials are missing.
3.  Send a one-off test message using the helper script:

  ```bash
  python scripts/send_test_message.py --message "Testing my credentials"
  ```

  * The script uses `TEST_NUMBER` from `.env` if `--to` is omitted.
  * If `ACCESS_TOKEN`/`PHONE_NUMBER_ID` are present, the message is sent via Graph API; otherwise the payload is printed to the console so you can validate the flow offline.
4.  Once Meta confirms webhook delivery, messages such as "hi", "hello", or "menu" will trigger the placeholder conversation defined in `conversation.py`.

Use this skeleton purely to validate connectivity. The actual Water Wallet flows (Precision Sowing, Crop Solvency, etc.) can be layered on top once backend contracts and webhook approvals are finalized.

---

## Role of This Service

This Flask service is **not the core intelligence engine**.

It is responsible for:

* Receiving WhatsApp messages via a webhook
* Managing conversational state (step-by-step data capture)
* Validating user inputs
* Calling existing Water Wallet backend APIs
* Sending formatted responses back to WhatsApp

All water intelligence logic remains in the main backend.

---

## Supported Water Wallet Features (via WhatsApp)

Based on the problem statement and feature scope (Precision Sowing Advisor, Crop Solvency Check), the WhatsApp interface supports:

1. **Precision Sowing Advisory (15-Day Window)**

   * Collects crop name
   * Collects latitude and longitude (or location input resolved server-side)
   * Calls backend API providing a 15-day forecast–based sowing recommendation

2. **Guided Input Collection**

   * Location (PIN / village / lat-long)
   * Crop selection
   * Land size (acres)
   * Water source

This aligns with the "chat-as-a-form" design principle.

---

## High-Level Architecture

WhatsApp User → WhatsApp Cloud API → Flask Webhook → Water Wallet Backend APIs → WhatsApp Response

The Flask webhook is mandatory as WhatsApp Cloud API operates in an event-driven push model.

---

## Technology Stack

* Python 3.10+
* Flask
* Requests (HTTP client)
* WhatsApp Cloud API (Meta)
* Ngrok (for local development)

---

## Folder Structure (Suggested)

```
whatsapp-service/
│
├── app.py                # Flask app entry
├── webhook.py            # WhatsApp webhook routes
├── conversation.py       # Minimal placeholder logic
├── whatsapp_client.py    # Send message utility (real API or mock)
├── config.py             # Tokens & configuration loader
├── scripts/send_test_message.py  # Credential verification helper
├── requirements.txt
└── README.md
```

---

## Environment Configuration

Create a `.env` or config file with the following values:

```
ACCESS_TOKEN=<WhatsApp Cloud API access token>
PHONE_NUMBER_ID=<WhatsApp phone number ID>
VERIFY_TOKEN=<Webhook verification token>
BACKEND_BASE_URL=<Water Wallet backend base URL>
```

⚠️ Access tokens may expire and should be refreshed as required.

---

## Webhook Endpoints

### 1. Webhook Verification (Required)

```
GET /webhook
```

Used by Meta during webhook registration to verify ownership.

### 2. Incoming Message Handler

```
POST /webhook
```

Receives WhatsApp messages in JSON format and routes them through the conversation engine.

---

## Conversation Flow (Precision Sowing Advisor)

1. User initiates chat
2. System requests crop name
3. System requests latitude and longitude
4. Inputs are validated
5. Backend API is called
6. 15-day sowing window recommendation is returned

---

## Backend API Contract (Example)

### Precision Sowing Forecast API

**Endpoint**

```
POST /api/sowing/forecast
```

**Request Payload**

```json
{
  "crop": "wheat",
  "latitude": 19.0760,
  "longitude": 72.8777
}
```

**Response Payload**

```json
{
  "recommended_start_date": "2026-06-18",
  "recommended_end_date": "2026-06-24",
  "risk_level": "LOW",
  "reason": "Optimal rainfall and soil moisture predicted"
}
```

---

## Message Formatting Strategy

WhatsApp responses should be:

* Short
* Structured
* Non-technical

Example:

```
🌱 Optimal Sowing Window

Crop: Wheat
Dates: 18 Jun – 24 Jun
Risk Level: Low

Reason: Favorable rainfall forecast
```

---

## State Management

Conversation state is maintained per WhatsApp user using:

* WhatsApp phone number as unique identifier
* In-memory dictionary (MVO)

For production, this can be replaced with Redis or a database.

---

## Development Setup

1. Install dependencies

```
pip install -r requirements.txt
```

2. Run Flask server

```
python app.py
```

3. Expose webhook using ngrok

```
ngrok http 5000
```

4. Register webhook URL in WhatsApp Cloud API dashboard

---

## Testing Constraints

* Only the **test WhatsApp number** is allowed in unverified mode
* Messages from other numbers are ignored
* Media messages are not handled

---

## Security Notes

* Do not commit access tokens
* Validate numeric inputs (latitude, longitude, land size)
* Rate-limit repeated requests per user

---

## MVO Justification

This WhatsApp integration is designed exclusively for:

* Feature validation
* Demonstration
* Evaluator testing

It intentionally avoids production complexity such as:

* Template messaging
* User authentication
* Multi-language NLP

---

## Future Enhancements

* Hindi / vernacular language support
* Interactive reply buttons
* Redis-backed session store
* Integration with additional Water Wallet features
* Transition to production WhatsApp Business API

---