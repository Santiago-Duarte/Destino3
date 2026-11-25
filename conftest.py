import os

# Se fija antes de que cualquier import de src.config lea ENVIRONMENT.
os.environ["ENVIRONMENT"] = "testing"
