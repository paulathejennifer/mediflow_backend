from pydantic_settings import BaseSettings

class MLConfig(BaseSettings):
    # Confidence threshold to flag a record as a potential duplicate (0.0 to 1.0)
    DUPLICATE_THRESHOLD: float = 0.82
    
    # Algorithmic weights (Must sum to 1.0)
    # TF-IDF captures structural character configurations across the tokenized text
    TFIDF_WEIGHT: float = 0.60
    # Levenshtein/RapidFuzz catches transpositions and small typos
    RAPIDFUZZ_WEIGHT: float = 0.40

    class Config:
        env_prefix = "ML_"

ml_config = MLConfig()