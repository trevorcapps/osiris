import logging
from typing import List
from app.models.schemas import Entity

logger = logging.getLogger(__name__)

try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = None
    logger.warning("spaCy model not loaded — entity extraction disabled")


def extract_entities(text: str, source_event_id: str = None) -> List[Entity]:
    if not nlp or not text:
        return []
    try:
        doc = nlp(text[:10000])  # Limit input size
        entities = []
        seen = set()
        for ent in doc.ents:
            if ent.label_ in ("PERSON", "ORG", "GPE", "LOC", "NORP", "FAC", "EVENT"):
                key = (ent.text.strip(), ent.label_)
                if key not in seen and len(ent.text.strip()) > 1:
                    seen.add(key)
                    entities.append(Entity(
                        name=ent.text.strip(),
                        type=ent.label_,
                        source_event_id=source_event_id
                    ))
        return entities
    except Exception as e:
        logger.error(f"Entity extraction failed: {e}")
        return []
