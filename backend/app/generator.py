import os
import logging
from dotenv import load_dotenv
from groq import Groq
from .utils import ABSTAIN_MESSAGE

load_dotenv()

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

MODEL_NAME = os.getenv("GENERATOR_MODEL", "openai/gpt-oss-120b")

def _build_context(retrieved_docs):
    parts = []
    for i, d in enumerate(retrieved_docs):
        section = d.get("parent_section", "Unknown Section")
        text = d.get("text", "").strip()
        parts.append(f"[DOCUMENT {i+1}]\nSection: {section}\n\n{text}")
    return "\n\n".join(parts)

def generate_answer(question: str, retrieved_docs: list) -> str:
    if not retrieved_docs:
        return ABSTAIN_MESSAGE

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("CRITICAL ERROR: No GROQ_API_KEY found! Python is blind to your environment.")

    client = Groq(api_key=api_key)
    context_str = _build_context(retrieved_docs)

    # 🚨 UPGRADED CHUNK DUMP FOR AUDIT: Case A vs Case B Verification
    print("\n" + "🛑"*30)
    print("🛑 RAW PAYLOAD SENT TO GROQ 🛑")
    for i, doc in enumerate(retrieved_docs):
        text_content = doc.get('text', 'NO TEXT')
        word_count = len(text_content.split())
        char_count = len(text_content)
        
        print(f"\n--- CHUNK {i+1} ---")
        print(f"SECTION: {doc.get('parent_section', 'Unknown Section')}")
        print(f"STATS: {word_count} words | {char_count} characters")
        print(f"TEXT START >>>\n{text_content}\n<<< TEXT END")
    print("🛑"*30 + "\n")

    system_instruction = f"""
    You are TruthLens, an expert AI legal auditor. 
    Your job is to answer the user's question using ONLY the provided legal documents.
    
    CRITICAL INSTRUCTIONS:
    1. SYNTHESIS: Do not copy-paste verbatim. If information comes from multiple documents, synthesize them into a single, cohesive answer.
    2. TONE & DELIVERY: Be professional, grounded, and concise. Always start your response with a brief, natural introductory sentence (e.g., "According to the NIST framework, the seven characteristics are:").
    3. ASSUMPTION CORRECTION: If the user's question contains a false assumption, gently correct them based in reality before answering.
    4. MISSING DATA: If the answer cannot be found in the provided context, respond exactly with: "{ABSTAIN_MESSAGE}"
    5. FORMATTING: Use bullet points when listing items, steps, or evidence. Use bold text to highlight key terms.
    6. NO META-COMMENTARY: NEVER narrate your internal rules, thought processes, or use robotic labels (e.g., do not type "Conclusion:", "Correction:", or "Executing Rule 3").
    """

    try:
        logger.info(f"Calling Groq {MODEL_NAME}...")
        
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_instruction.strip()},
                {"role": "user", "content": f"Context from Database:\n{context_str}\n\nUser Question: {question}"}
            ],
            temperature=0.0,
            max_tokens=600
        )
        
        return completion.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"🔥 THE API CALL CRASHED: {e}")
        raise RuntimeError(f"Generator failed: {e}")