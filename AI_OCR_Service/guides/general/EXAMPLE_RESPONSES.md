# Enhanced Chat System - Example Responses

## Example 1: Simple Medicine Query

### Request
```bash
POST /medicine-chat
Content-Type: application/json

{
  "question": "What is Paracetamol 500mg?",
  "image_base64": null,
  "image_format": "jpeg",
  "chat_history": [],
  "include_context": true
}
```

### Response
```json
{
  "status": "success",
  "answer": "## Answer\nParacetamol 500mg is a common pain reliever and fever reducer used to treat mild to moderate pain and fever.\n\n## Detailed Medicine Information\n\nMedicine: Paracetamol 500mg\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n📋 What it does:\nReduces fever and relieves mild to moderate pain. Used for headaches, muscle aches, cold symptoms, and period pain.\n\n⚠️ Common Side Effects:\n  - Nausea (rare)\n  - Vomiting (rare)\n  - Allergic reactions (very rare)\n\n⚡ Precautions:\n  - Do not exceed 4g per day\n  - Avoid if you have liver problems\n  - Do not take with alcohol\n  - Not recommended during pregnancy\n\n💊 How to take:\nTake with or after food with a glass of water. Can take every 4-6 hours, maximum 4 times a day. Do not exceed 4g (8 tablets) in 24 hours.\n\n🔗 Interactions:\n  No interactions found with your current medicines\n\n---\n⚠️ MEDICAL DISCLAIMER\nThis information is for educational purposes only. Always consult with a healthcare professional before starting or changing any medication.",
  "disclaimer": "This information is for educational purposes only. Always consult with a healthcare professional before starting or changing any medication.",
  "metadata": {
    "provider_used": "rag",
    "confidence": 0.85,
    "has_image": false,
    "processing_time_ms": 2450,
    "timestamp": "2024-02-06T10:30:00.000Z"
  },
  "retrieved_context": null,
  "suggestions": [
    "What are the side effects?",
    "When should I contact a doctor about side effects?",
    "How do I properly store this medication?"
  ],
  "error_details": null
}
```

### Formatted Output (User Sees)
```
## Answer
Paracetamol 500mg is a common pain reliever and fever reducer used to treat mild to 
moderate pain and fever.

## Detailed Medicine Information

Medicine: Paracetamol 500mg
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 What it does:
Reduces fever and relieves mild to moderate pain. Used for headaches, muscle aches, 
cold symptoms, and period pain.

⚠️ Common Side Effects:
  - Nausea (rare)
  - Vomiting (rare)
  - Allergic reactions (very rare)

⚡ Precautions:
  - Do not exceed 4g per day
  - Avoid if you have liver problems
  - Do not take with alcohol
  - Not recommended during pregnancy

💊 How to take:
Take with or after food with a glass of water. Can take every 4-6 hours, maximum 
4 times a day. Do not exceed 4g (8 tablets) in 24 hours.

🔗 Interactions:
  No interactions found with your current medicines

---
⚠️ MEDICAL DISCLAIMER
This information is for educational purposes only. Always consult with a healthcare 
professional before starting or changing any medication.
```

---

## Example 2: Prescription Image Upload

### Request
```bash
POST /medicine-chat/upload
Content-Type: multipart/form-data

question: "What medicines are in this prescription?"
image: <prescription.jpg file>
chat_history: "[]"
include_context: true
```

### Response
```json
{
  "status": "success",
  "answer": "## Answer\nI found 3 medicines in your prescription:\n1. Paracetamol for pain and fever relief\n2. Ibuprofen for inflammation and pain\n3. Amoxicillin for bacterial infection\n\nPlease follow your doctor's instructions for dosage and duration.\n\n## Detailed Medicine Information\n\nMedicine: Paracetamol 500mg\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n📋 What it does:\nReduces fever and relieves mild to moderate pain...\n\n[Additional medicines follow...]\n\n---\n⚠️ MEDICAL DISCLAIMER\nThis information is for educational purposes only...",
  "disclaimer": "This information is for educational purposes only...",
  "metadata": {
    "provider_used": "rag",
    "confidence": 0.92,
    "has_image": true,
    "processing_time_ms": 5840,
    "timestamp": "2024-02-06T10:35:00.000Z"
  },
  "retrieved_context": "[OCR extracted text from image]",
  "suggestions": [
    "Are there any interactions between these medicines?",
    "When should I take each medicine?",
    "What should I do if I miss a dose?"
  ],
  "error_details": null
}
```

---

## Example 3: Multiple Medicines from Prescription

### OCR Extracted Text
```
Rx. Dr. John Smith
Date: 06/02/2024

Paracetamol 500mg BD x 5 days
Ibuprofen 400mg OD x 7 days
Amoxicillin 500mg TID x 10 days

Patient: John Doe
```

### Formatted Response

```
## Answer
I found 3 medicines in your prescription. Here's what they do and how to take them:

1. **Paracetamol** - For pain and fever relief, taken twice daily
2. **Ibuprofen** - For inflammation and pain, taken once daily
3. **Amoxicillin** - Antibiotic for bacterial infections, taken three times daily

Please follow all instructions and complete the full course of antibiotics.

## Detailed Medicine Information

Medicine: Paracetamol 500mg
Frequency: BD (Twice Daily)
Duration: 5 days
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 What it does:
Reduces fever and relieves mild to moderate pain. Commonly used for headaches, 
body aches, fever, and menstrual pain.

⚠️ Common Side Effects:
  - Nausea (rare)
  - Allergic reactions (very rare)
  - Liver toxicity if overdosed

⚡ Precautions:
  - Do not exceed 4g per day
  - Avoid with alcohol
  - May affect liver function
  - Not safe during first trimester of pregnancy

💊 How to take:
Take one tablet (500mg) every 4-6 hours as needed. Do not exceed 4 tablets in 24 hours. 
Take with food or milk if stomach upset occurs.

🔗 Interactions:
  - Warfarin: May increase bleeding risk
  - Alcohol: Increases liver damage risk

════════════════════════════════════════════════════════════════

Medicine: Ibuprofen 400mg
Frequency: OD (Once Daily)
Duration: 7 days
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 What it does:
Reduces pain, fever, and inflammation. Used for arthritis, period pain, headaches, 
and minor injuries.

⚠️ Common Side Effects:
  - Stomach upset (common)
  - Heartburn
  - Dizziness
  - Rash

⚡ Precautions:
  - Can cause stomach ulcers if used long-term
  - Avoid if you have heart disease
  - Not recommended during pregnancy
  - Use lowest effective dose
  - Take with food

💊 How to take:
Take one tablet (400mg) once daily, preferably with food. Take at the same time each 
day for best results. Complete the full 7-day course even if symptoms improve.

🔗 Interactions:
  - Aspirin: Avoid combination
  - Blood thinners: May increase bleeding risk
  - Blood pressure medications: May reduce effectiveness
  - Paracetamol: Can be taken together but maintain dose limits

════════════════════════════════════════════════════════════════

Medicine: Amoxicillin 500mg
Frequency: TID (Three Times Daily)
Duration: 10 days
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 What it does:
Antibiotic that kills bacteria causing infections. Used for ear infections, throat 
infections, urinary tract infections, and skin infections.

⚠️ Common Side Effects:
  - Diarrhea (common)
  - Nausea
  - Vomiting
  - Rash
  - Allergic reactions (if penicillin allergy)

⚡ Precautions:
  - Complete the full 10-day course even if you feel better
  - Do not share with others
  - May reduce effectiveness of birth control pills
  - Stop and report any severe allergic reactions
  - Take exactly as prescribed

💊 How to take:
Take one tablet (500mg) three times daily with 6-8 hours between doses. Take with 
or without food. Continue taking until the course is complete to prevent antibiotic 
resistance.

🔗 Interactions:
  - Birth control pills: Effectiveness may be reduced (use alternative contraception)
  - Methotrexate: May reduce effectiveness
  - Warfarin: May increase blood thinning effect
  - Paracetamol: Can be taken together
  - Ibuprofen: Can be taken together with caution

---
⚠️ MEDICAL DISCLAIMER
This information is for educational purposes only. Always consult with a healthcare 
professional before starting or changing any medication. Follow your doctor's 
instructions exactly. If you experience severe side effects, stop taking the medicine 
and contact your doctor immediately.
```

---

## Example 4: Query with Chat History

### Request
```bash
POST /medicine-chat
Content-Type: application/json

{
  "question": "Are there any interactions between these medicines?",
  "image_base64": null,
  "chat_history": [
    {
      "role": "user",
      "content": "What medicines are in my prescription?"
    },
    {
      "role": "assistant",
      "content": "I found Paracetamol, Ibuprofen, and Amoxicillin..."
    }
  ],
  "include_context": true
}
```

### Response
```json
{
  "status": "success",
  "answer": "## Answer\nBased on your previous medicines, here are the important interactions:\n\n⚠️ **Important Interactions:**\n\n1. **Paracetamol + Ibuprofen**: While they can be taken together, avoid combining them regularly. If taking both, maintain proper spacing and dose limits.\n\n2. **Amoxicillin + Birth Control**: If you take birth control pills, the antibiotic may reduce their effectiveness. Use additional contraception during the course.\n\n3. **Ibuprofen + Aspirin**: Do not take with aspirin as they can increase stomach ulcer risk.\n\n4. **Alcohol Interaction**: Avoid alcohol with Paracetamol and Ibuprofen as it increases the risk of liver and stomach damage.\n\n✅ **Safe Combinations:**\n- Paracetamol + Ibuprofen can be used together if needed (but carefully)\n- Amoxicillin has no major interactions with Paracetamol or Ibuprofen\n\nAlways inform your doctor about all medicines you're taking, including over-the-counter drugs.",
  "metadata": {
    "provider_used": "rag",
    "confidence": 0.88,
    "has_image": false,
    "processing_time_ms": 3210,
    "timestamp": "2024-02-06T10:40:00.000Z"
  },
  "suggestions": [
    "What should I do if I miss a dose?",
    "Are these medicines safe during pregnancy?",
    "What foods should I avoid with these medicines?"
  ]
}
```

---

## Example 5: Error Handling

### Request (Missing Required Field)
```bash
POST /medicine-chat
Content-Type: application/json

{
  "image_base64": null,
  "chat_history": []
}
```

### Response (422 Validation Error)
```json
{
  "status": "error",
  "error_details": "Validation error",
  "detail": {
    "error": "Validation error",
    "message": "Field required: 'question'"
  }
}
```

### Request (OCR Service Unavailable)
```bash
POST /medicine-chat/upload
Content-Type: multipart/form-data

question: "What medicines?"
image: <corrupted_file.jpg>
```

### Response (Service Error with Fallback)
```json
{
  "status": "success",
  "answer": "I couldn't extract the text from the image clearly. Could you please:\n1. Try uploading a clearer image\n2. Or describe the medicines in your prescription\n3. Or tell me the medicine names directly\n\nOnce I have the medicine information, I can provide detailed information about side effects, interactions, and usage.",
  "metadata": {
    "provider_used": "rag",
    "confidence": 0.6,
    "has_image": true,
    "processing_time_ms": 1200,
    "timestamp": "2024-02-06T10:45:00.000Z"
  },
  "suggestions": [
    "Can you tell me the medicine names?",
    "Can you try uploading a clearer image?",
    "Would you like to describe the medicines instead?"
  ]
}
```

---

## Log Output Examples

### Successful Request with Image
```
INFO  🔄 Processing chat request: What medicines are prescribed?...
DEBUG 📸 Extracting OCR data from image...
INFO  ✅ OCR extraction successful: 1250 characters
DEBUG OCR_EXTRACTION | Medicine: Paracetamol | Fields: dose, frequency
DEBUG OCR_EXTRACTION | Medicine: Ibuprofen | Fields: dose, frequency
DEBUG OCR_EXTRACTION | Medicine: Amoxicillin | Fields: dose, frequency
INFO  📋 Found 3 medicines in prescription
DEBUG 🧠 Enriching medicine: Paracetamol
DEBUG LLM Response: {"what_it_does": "...", "side_effects": [...], ...}
INFO  LLM_ENRICHMENT | Medicine: Paracetamol | Fields enriched: what_it_does, side_effects, precautions, how_to_take, interactions
DEBUG 🧠 Enriching medicine: Ibuprofen
INFO  LLM_ENRICHMENT | Medicine: Ibuprofen | Fields enriched: what_it_does, side_effects, precautions, how_to_take, interactions
DEBUG 🧠 Enriching medicine: Amoxicillin
INFO  LLM_ENRICHMENT | Medicine: Amoxicillin | Fields enriched: what_it_does, side_effects, precautions, how_to_take, interactions
INFO  ✅ Enriched 3 medicines
INFO  💬 Getting LLM response...
DEBUG 💬 Getting enhanced response...
INFO  🎨 Formatting response...
INFO  ✅ Response ready: 5840ms
INFO  CHAT_RESPONSE | Time: 5840ms | Medicines: 3 | Provider: enhanced_rag
```

### Error During Enrichment
```
INFO  🔄 Processing chat request: What is Aspirin?...
DEBUG 🧠 Enriching medicine: Aspirin
WARNING ⚠️ LLM enrichment failed: Connection timeout
DEBUG ERROR | Stage: LLM_ENRICHMENT | Error type: TimeoutError | Message: Connection timeout after 30s
WARNING ⚠️ LLM enrichment failed: Connection timeout
INFO  📋 Found 1 medicine in OCR
INFO  ✅ Response ready: 1200ms (using OCR data without enrichment)
```

---

## Performance Metrics

### Response Times
```
Simple Query:
  OCR: N/A
  LLM Response: 1200ms
  Formatting: 150ms
  Total: 1350ms

With Image & 3 Medicines:
  OCR Extraction: 2100ms
  Medicine Parsing: 300ms
  LLM Enrichment (3 medicines): 3200ms
  Formatting: 240ms
  Total: 5840ms

Average per medicine enrichment: ~1067ms
```

---

These examples demonstrate the complete functionality of the enhanced medicine chat system with real-world use cases and error scenarios.
