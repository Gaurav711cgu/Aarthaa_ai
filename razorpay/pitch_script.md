# ArthaShield - AI Risk Manager for Razorpay

**Goal:** 5-minute pitch video script for the Razorpay AI Buildathon (AI Risk Manager Track)

## Structure
1. **The Hook (0:00 - 0:45):** The cost of chargebacks and fraud for merchants.
2. **The Solution (0:45 - 1:30):** Introducing ArthaShield - real-time risk assessment via Razorpay Webhooks.
3. **The AI Engine (1:30 - 3:00):** How the Ensemble Model (XGBoost + Random Forest) + SHAP + RAG works.
4. **The Demo (3:00 - 4:15):** Triggering a transaction, viewing the risk score, and auto-generating chargeback evidence.
5. **The Value Prop (4:15 - 5:00):** Why this wins the Buildathon (reducing merchant liability, automation, API-first).

## Script
*(Visual: Developer at desk, screen sharing the ArthaShield dashboard)*

**Speaker:** "Hi everyone, I'm Gaurav. Every year, merchants lose millions to fraudulent chargebacks and returns. Traditional risk models are black boxes, leaving merchants defenseless when disputes arise. That's why I built ArthaShield—a specialized merchant-protection module powered by my enterprise risk engine, Aarthaa AI—for the Razorpay AI Risk Manager track."

*(Visual: Architecture diagram showing Razorpay Webhook -> ArthaShield API -> Fraud Model + RAG)*

**Speaker:** "ArthaShield is a real-time risk evaluation engine that plugs directly into Razorpay webhooks. When a `payment.captured` event occurs, we extract the features and run them through an ensemble model of XGBoost and Random Forests. But detecting fraud isn't enough—you need to prove it."

*(Visual: Code snippet of SHAP explanation generation)*

**Speaker:** "That's where Explainable AI comes in. We use SHAP values to explain exactly *why* a transaction was scored a certain way. If a dispute happens, our system automatically queries a RAG pipeline loaded with RBI guidelines and merchant terms to generate a comprehensive, legally-sound chargeback defense payload, ready to be submitted to the Razorpay Dispute API."

*(Visual: Live demo triggering a webhook)*

**Speaker:** "Let's see it in action. I'm firing a test webhook from Razorpay. You can see ArthaShield instantly scores the transaction. Because it flags high velocity, the model blocks it, generates the SHAP explanation, and structures the evidence payload."

*(Visual: Speaker full screen)*

**Speaker:** "ArthaShield protects merchants by preventing fraud at checkout and automating the defense process when chargebacks occur. It's scalable, transparent, and built for the modern payments stack. Thank you for checking out my submission!"
