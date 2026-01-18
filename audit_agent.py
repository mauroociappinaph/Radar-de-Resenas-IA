import os
import time
import re
import litellm
import langsmith
from langsmith import traceable
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# API Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# LangSmith Configuration
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = "Radar_IA_Audits"

def get_ai_client():
    print("🤖 Configuring Multi-Provider AI (LiteLLM)...")
    model = os.getenv("PRIMARY_MODEL", "mistral/mistral-small-latest")
    return model

MODEL_NAME = get_ai_client()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def load_email_template():
    """Carga el template HTML para emails."""
    template_path = os.path.join(os.path.dirname(__file__), 'email_template.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()

def render_html_email(greeting, main_content, cta_button=""):
    """Renderiza el contenido del email en HTML usando el template."""
    template = load_email_template()

    # Reemplazar placeholders
    html = template.replace('{{GREETING}}', greeting)
    html = html.replace('{{MAIN_CONTENT}}', main_content)
    html = html.replace('{{CTA_BUTTON}}', cta_button)

    return html

def classify_email(email: str) -> str:
    if not email: return "unknown"
    generic_prefixes = [
        'info', 'contact', 'contacto', 'hello', 'hola', 'admin', 'sales', 'support', 'office',
        'recepcion', 'citas', 'reservas', 'team', 'ventas', 'atencion', 'soporte', 'groupbookings',
        'gerencia', 'comercial', 'ayuda', 'marketing', 'press', 'hr', 'jobs', 'careers',
        'klantenservice', 'affiliate', 'customer', 'serviciocliente', 'atencionalcliente', 'servicedesk',
        'management', 'hq', 'feedback', 'donations', 'privacy', 'legal'
    ]
    prefix = email.split('@')[0].lower()
    prefix_clean = re.sub(r'\d+', '', prefix)
    # Use exact match to avoid skipping things like 'affiliatesupport' just because it contains 'support'
    if any(gp == prefix_clean for gp in generic_prefixes): return "generic"
    return "personal"

def get_rating_status(stars):
    try:
        if stars is None or str(stars).lower() == 'none': return "Visibility (Unknown digital presence)"
        s = float(stars)
        if s == 0: return "Visibility (No reviews yet)"
        if s < 4.0: return "Crisis Management (Low rating)"
        return "Optimization (High rating)"
    except: return "Visibility"

@traceable
def run_sequential_audit(name, key_issue, review_context, sentiment_score=0.0):
    """
    Simula sequential thinking usando múltiples llamadas a IA para análisis más profundo.
    Adapta la estrategia según el sentimiento de las reseñas.
    """

    # THOUGHT 1: Análisis inicial adaptado al sentimiento
    if sentiment_score > 0.1:
        # Reseñas positivas: enfoque en oportunidades de crecimiento
        prompt_1 = f"""
        Eres un consultor experimentado en marketing digital. Lee estas reseñas POSITIVAS sobre '{name}': {review_context[:500]}

        TAREA: Identifica las FORTALEZAS PRINCIPALES que más se destacan. ¿Qué valoran más los clientes?
        ¿Cómo podemos AMPLIFICAR estos aspectos positivos para atraer más clientes?

        Sé específico y enfócate en oportunidades de crecimiento. Este es el PASO 1 de 4.
        """
    elif sentiment_score < -0.1:
        # Reseñas negativas: enfoque en problemas reales
        prompt_1 = f"""
        Eres un consultor experimentado en marketing digital. Lee estas reseñas con PROBLEMAS sobre '{name}': {review_context[:500]}

        TAREA: Identifica el PROBLEMA PRINCIPAL que más se repite. ¿Qué duele más a los clientes?
        ¿Cómo podemos ayudarles a SOLUCIONAR estos problemas específicos?

        Sé directo y específico. Este es el PASO 1 de 4.
        """
    else:
        # Reseñas neutrales: enfoque en visibilidad
        prompt_1 = f"""
        Eres un consultor experimentado en marketing digital. Lee estas reseñas NEUTRALES sobre '{name}': {review_context[:500]}

        TAREA: ¿Por qué las reseñas son neutras? ¿Falta visibilidad o engagement?
        ¿Cómo podemos aumentar la presencia online y generar más interacciones?

        Identifica oportunidades de mejora. Este es el PASO 1 de 4.
        """

    response_1 = litellm.completion(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt_1}],
        temperature=0.3,
        max_tokens=200
    )
    thought_1 = response_1.choices[0].message.content.strip()

    # THOUGHT 2: Identificación de oportunidades y soluciones
    prompt_2 = f"""
    El problema principal de {name} es: "{thought_1}"

    TAREA: ¿Cómo puedo ayudarles específicamente? Piensa en soluciones prácticas de IA que realmente solucionen este problema.
    Sé concreto: qué herramienta o automatización específica resolvería esto.

    Este es el PASO 2 de 4.
    """

    response_2 = litellm.completion(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt_2}],
        temperature=0.4,
        max_tokens=250
    )
    thought_2 = response_2.choices[0].message.content.strip()

    # THOUGHT 3: Desarrollo de estrategia persuasiva
    prompt_3 = f"""
    Sobre {name}:
    Problema: {thought_1}
    Mi solución: {thought_2}

    TAREA: ¿Cómo hago que este email suene natural y persuasivo? Piensa en cómo un consultor hablaría con un colega.
    ¿Qué tono usar? ¿Qué historia contar? ¿Cómo crear urgencia sin sonar agresivo?

    Este es el PASO 3 de 4.
    """

    response_3 = litellm.completion(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt_3}],
        temperature=0.5,
        max_tokens=300
    )
    thought_3 = response_3.choices[0].message.content.strip()

    # THOUGHT 4: Redacción final del email
    prompt_4 = f"""
    Información completa sobre {name}:
    PASO 1: {thought_1}
    PASO 2: {thought_2}
    PASO 3: {thought_3}

    TAREA FINAL: Escribe un email que suene como si lo escribiera un consultor amigo, no un robot.
    - Subject: Algo que llame la atención pero natural
    - Empieza con un saludo normal: "Hola equipo de {name},"
    - Habla como persona: menciona específicamente el problema que leíste en reseñas
    - Explica tu solución de manera conversacional
    - Termina con una llamada natural a conversar
    - Firma EXACTA: Mauro Ciappina | Desarrollador IA

    IMPORTANTE: Evita listas numeradas, bullet points, o lenguaje corporativo. Hazlo sonar humano.

    FORMATO DEL OUTPUT:
    Subject: [subject aquí]

    [email completo aquí, conversacional y natural]

    Mauro Ciappina | Desarrollador IA
    """

    response_4 = litellm.completion(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt_4}],
        temperature=0.7,
        max_tokens=500
    )
    thought_4 = response_4.choices[0].message.content.strip()

    # Compilar respuesta final en formato XML esperado
    combined_thinking = f"""
Análisis Secuencial para {name}:

PASO 1 - Problema Crítico: {thought_1}

PASO 2 - Oportunidades: {thought_2}

PASO 3 - Estrategia: {thought_3}

PASO 4 - Redacción: {thought_4}
""".strip()

    # Extraer componentes del email generado
    subject_match = re.search(r'Subject:\s*(.+?)(?:\n|$)', thought_4, re.IGNORECASE)
    subject = subject_match.group(1).strip() if subject_match else f"Solución IA para {name}"

    # Extraer greeting y main content
    email_text = re.sub(r'Subject:.*?\n', '', thought_4, flags=re.IGNORECASE)
    email_text = re.sub(r'Mauro Ciappina \| Desarrollador IA.*', '', email_text, flags=re.IGNORECASE).strip()
    # Limpiar líneas vacías al inicio
    email_text = email_text.lstrip('\n').strip()

    # Separar greeting del contenido principal
    lines = email_text.split('\n', 1)
    greeting = lines[0] if lines else f"Hola equipo de {name},"
    main_content = lines[1] if len(lines) > 1 else email_text

    # Estructurar párrafos: convertir saltos de línea dobles en párrafos
    if main_content:
        # Dividir por párrafos (doble salto de línea)
        paragraphs = main_content.split('\n\n')
        # Convertir cada párrafo en <p> tag
        main_content = '\n'.join([f'<p>{p.strip()}</p>' for p in paragraphs if p.strip()])

    # Generar HTML
    html_email = render_html_email(greeting, main_content)

    # Formato final XML con HTML
    final_response = f"""<thinking>{combined_thinking}</thinking>
<subject>{subject}</subject>
<email>{html_email}</email>"""

    return final_response

@traceable
def run_ai_audit(name, key_issue, review_context, sentiment_score=0.0):
    """
    Wrapper para mantener compatibilidad - usa sequential thinking por defecto
    """
    return run_sequential_audit(name, key_issue, review_context, sentiment_score)

def analyze_leads(limit: int = 50):
    print(f"🧠 Starting analysis process - Limit: {limit}...")
    # Select enriched leads that haven't been analyzed yet
    response = supabase.table("leads").select("*").eq("status", "enriched").limit(limit).execute()
    leads = response.data
    if not leads:
        print("📭 No leads found in 'enriched' status.")
        return

    for lead in leads:
        lead_id, name, rating = lead.get("id"), lead.get("business_name"), lead.get("rating")
        review_context = lead.get("review_context", "No direct reviews found.")
        contact_email = lead.get("contact_email")
        sentiment_score = lead.get("sentiment_score", 0.0)

        # Internal re-check of email quality
        email_type = classify_email(contact_email)

        if not contact_email or not lead.get("email_valid"):
            print(f"⏩ Skipping {name}: Missing or invalid email.")
            supabase.table("leads").update({"status": "failed", "analysis_thinking": "Skipped: Missing/Invalid email"}).eq("id", lead_id).execute()
            continue

        if email_type == "generic" or lead.get("email_type") != "personal":
            # If the user specifically excluded them, we mark them as skipped so they don't stay "Analizando"
            print(f"⏩ Skipping {name}: Generic email ({contact_email})")
            supabase.table("leads").update({"status": "skipped", "analysis_thinking": "Skipped: Generic email filter"}).eq("id", lead_id).execute()
            continue

        print(f"🤖 Auditing: {name} (Sentiment: {sentiment_score:.2f})...")
        key_issue = get_rating_status(rating)

        try:
            raw_response = run_sequential_audit(name, key_issue, review_context, sentiment_score)
            print(f"DEBUG RAW RESPONSE:\n{raw_response}\n---")

            # Extraction - Improved regex to be more forgiving
            thinking_match = re.search(r'<(?:thought|thinking)>(.*?)</(?:thought|thinking)>', raw_response, re.DOTALL | re.IGNORECASE)
            thinking = thinking_match.group(1).strip() if thinking_match else "Analysis produced without tags."

            subject_match = re.search(r'<subject>(.*?)</subject>', raw_response, re.DOTALL | re.IGNORECASE)
            if subject_match:
                subject = subject_match.group(1).strip()
            else:
                # Fallback for common AI subject formats
                subject_fallback = re.search(r'(?:Asunto|Subject|Subject\sLine):\s*(.*)', raw_response, re.IGNORECASE)
                subject = subject_fallback.group(1).strip() if subject_fallback else f"Propuesta para {name}"

            # Clean subject from potential quotes or labels
            subject = re.sub(r'^(?:Asunto|Subject|Subject\sLine):\s*', '', subject, flags=re.IGNORECASE).strip()
            subject = subject.strip('"').strip("'").strip('*')

            email_match = re.search(r'<email>(.*?)</email>', raw_response, re.DOTALL | re.IGNORECASE)
            email_draft = email_match.group(1).strip() if email_match else raw_response

            # Remove any residual tags if fallback was used
            email_draft = re.sub(r'<(?:thought|thinking|subject|email)>.*?</(?:thought|thinking|subject|email)>', '', email_draft, flags=re.DOTALL | re.IGNORECASE).strip()

            supabase.table("leads").update({
                "status": "analyzed",
                "email_subject": subject,
                "email_draft": email_draft,
                "analysis_thinking": thinking
            }).eq("id", lead_id).execute()
            print(f"✅ Draft created for {name}")
            time.sleep(1)
        except Exception as e:
            print(f"❌ Error analyzing {name}: {e}")
            supabase.table("leads").update({"analysis_thinking": f"Error: {str(e)}"}).eq("id", lead_id).execute()

if __name__ == "__main__":
    analyze_leads()
