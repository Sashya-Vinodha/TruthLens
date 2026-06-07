import os
import logging
from dotenv import load_dotenv
from groq import Groq
from .utils import ABSTAIN_MESSAGE

load_dotenv()

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

MODEL_NAME = os.getenv("GENERATOR_MODEL", "llama-3.3-70b-versatile")

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
    1. SYNTHESIZE: Do not copy-paste verbatim. If information comes from multiple documents, synthesize them into a single, cohesive answer.
    2. BE PRECISE: Be professional, grounded, and concise. Never use canned AI filler.
    3. THE TRAP-CATCHER RULE: If the user's question contains a false assumption, gently correct them based in reality.
    4. ABSTENTION RULE: If the answer cannot be found in the provided context, respond exactly with: "{ABSTAIN_MESSAGE}"
    5. FORMATTING RULE: You must format your final answer for maximum readability. Use bullet points when listing items, steps, or evidence. Use bold text to highlight key terms or framework concepts. Do not output a single wall of text.
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